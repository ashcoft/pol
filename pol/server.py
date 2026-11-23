from __future__ import print_function
from datetime import datetime
from hashlib import sha256
import json
import pickle
import zlib
import stat
import time, sys, traceback
import re
import os

import brotli
import six
from lxml import etree

from twisted.web import server, resource
from twisted.internet import reactor, endpoints, defer
from twisted.web.client import Agent, BrowserLikeRedirectAgent, PartialDownloadError, HTTPConnectionPool
from twisted.web.server import NOT_DONE_YET
from twisted.web.http_headers import Headers
from twisted.web.http import INTERNAL_SERVER_ERROR
from twisted.web.html import escape
twisted_headers = Headers
from twisted.logger import Logger

from scrapy.http.response.text import TextResponse
from scrapy.http import Headers
from scrapy.responsetypes import responsetypes
from scrapy.core.downloader.contextfactory import ScrapyClientContextFactory
from scrapy.selector import Selector

from pol.log import LogHandler
from .feed import Feed
from .client import ppReadBody, IGNORE_SIZE
from .reader.web import ReaderEndpoints

from twisted.logger import Logger


log = Logger()


def _text(value):
    return value.decode('utf-8', 'replace') if isinstance(value, bytes) else value


def _http_url(value):
    """Return an absolute http(s) URL as text, or None for anything else."""
    value = _text(value)
    value = (value or '').strip()
    if not value:
        return None
    try:
        parts = six.moves.urllib.parse.urlsplit(value)
    except ValueError:
        return None
    if parts.scheme.lower() not in ('http', 'https') or not parts.netloc:
        return None
    return value

class Downloader(object):

    def __init__(self, feed, debug, snapshot_dir, stat_tool, memon, request,
                 url, feed_config, selector_defer, sanitize, max_size):
        self.feed = feed
        self.debug = debug
        self.snapshot_dir = snapshot_dir
        self.stat_tool = stat_tool
        self.memon = memon
        self.request = request
        self.url = url
        self.feed_config=feed_config
        self.selector_defer = selector_defer
        self.sanitize = sanitize
        self.max_size = max_size

    def html2json(self, el):
        return [
            el.tag,
            {k: v for (k,v) in el.items() if k in ['tag-id', 'class']},  # attributes
            [self.html2json(e) for e in el.getchildren() if isinstance(e, etree.ElementBase)]
        ]

    def _saveResponse(self, headers, url, tree):
        # save html for extended selectors
        if six.PY2:
            file_name = '%s_%s' % (time.time(), sha256(url).hexdigest())
        elif six.PY3:
            file_name = '%s_%s' % (time.time(), sha256(url.encode('utf-8')).hexdigest())
        file_path = self.snapshot_dir + '/' + file_name
        with open(file_path, 'w') as f:
            f.write(url + '\n')
            if six.PY2:
                for k, v in headers.iteritems():
                    for vv in v:
                        f.write('%s: %s\n' % (k, vv))
            elif six.PY3:
                for k, v in headers.items():
                    for vv in v:
                        f.write('%s: %s\n' % (_text(k), _text(vv)))

            if six.PY2:
                f.write('\n\n' + etree.tostring(tree, encoding='utf-8', method='html'))
            elif six.PY3:
                f.write('\n\n' + etree.tostring(tree, encoding='utf-8', method='html').decode('utf-8'))
        return file_name

    def sanitizeAndNumerate(self, selector, numerate=True, sanitize_anchors=True):

        tree = selector.root.getroottree()

        i = 1
        for bad in tree.xpath("//*"):
            # remove scripts and iframes
            if bad.tag in ['script', 'iframe']:
                bad.getparent().remove(bad)
            elif numerate:
                # set tag-id attribute
                bad.attrib['tag-id'] = str(i)
                i += 1

            # promote lazy-loaded images to a real src
            if bad.tag == 'img':
                lazy_src = (bad.attrib.get('data-src') or bad.attrib.get('data-original')
                            or bad.attrib.get('data-lazy-src'))
                src = bad.attrib.get('src', '')
                if lazy_src and (not src or src.startswith('data:')):
                    bad.attrib['src'] = lazy_src
                bad.attrib.pop('loading', None)

            # sanitize anchors
            if sanitize_anchors and bad.tag == 'a' and 'href' in bad.attrib:
                bad.attrib['origin-href'] = bad.attrib['href']
                del bad.attrib['href']

            # remove html events
            for attr in bad.attrib:
                if attr.startswith('on'):
                    del bad.attrib[attr]

            # make clickable for mobile
            bad.attrib['onclick'] = ""

            # sanitize forms
            if bad.tag == 'form':
                bad.attrib['onsubmit'] = "return false"


    def setBaseAndRemoveScriptsAndMore(self, selector, headers, url):
        selector.remove_namespaces()

        tree = selector.root.getroottree()

        if self.snapshot_dir:
            file_name = self._saveResponse(headers, url, tree)
        else:
            file_name = 'DISABLED'

        # set base url to html document
        head = tree.xpath("//head")
        if head:
            head = head[0]
            base = head.xpath("./base")
            if base:
                base = base[0]
            else:
                base = etree.Element("base")
                head.insert(0, base)
            if six.PY2:
                base.set('href', url.decode('utf-8'))
            elif six.PY3:
                base.set('href', url)

        self.sanitizeAndNumerate(selector)

        body = tree.xpath("//body")
        if body:
            # append html2json js object
            jsobj = self.html2json(tree.getroot())
            script = etree.Element('script', {'type': 'text/javascript'})
            script.text = '\n'.join((
                            'var html2json = ' + json.dumps(jsobj) + ';',
                            'var snapshot_time = "' + file_name + '";'
                        ))
            body[0].append(script)

        if six.PY2:
            return etree.tostring(tree, method='html')
        elif six.PY3:
            return etree.tostring(tree, method='html').decode('utf-8')

    def buildScrapyResponse(self, response, body, url):
        status = response.code
        raw_headers = {k: b','.join(v) for k, v in response.headers.getAllRawHeaders()}
        # Content-Encoding makes Scrapy fall back to a plain Response (the body is
        # still compressed here), so pick the class from Content-Type only.
        sniff_headers = {k: v for k, v in raw_headers.items() if k.lower() != b'content-encoding'}
        respcls = responsetypes.from_args(headers=sniff_headers, url=url)
        return respcls(url=url, status=status, headers=Headers(raw_headers), body=body)

    def error_html(self, msg):
        return "<html><body>%s</body></html>" % msg.replace("\n", "<br/>\n")

    def downloadError(self, error):
        # read for details: https://stackoverflow.com/questions/29423986/twisted-giving-twisted-web-client-partialdownloaderror-200-ok
        if error.type is PartialDownloadError and error.value.response is not None:
            d = defer.Deferred()
            reactor.callLater(0, d.callback, error.value.response) # error.value.response is response_str
            d.addCallback(self.downloadDone)
            d.addErrback(self.downloadError)
            return

        if self.selector_defer:
            self.selector_defer.errback(error)
        else:
            try:
                if self.stat_tool:
                    feed_id = self.feed_config and self.feed_config['id']
                    s_url = None
                    if not feed_id:
                        feed_id = 0
                        s_url = self.url
                    self.stat_tool.trace(
                            ip = self.request.getHeader('x-real-ip') or self.request.client.host,
                            feed_id = feed_id,
                            post_cnt=0,
                            new_post_cnt=0,
                            url=s_url,
                            ex_msg=error.getErrorMessage(),
                            ex_callstack=error.getTraceback()
                        )
                else:
                    sys.stderr.write('\n'.join(
                        [str(datetime.utcnow()), str(self.request.uri), str(self.url),
                         'Downloader error: ' + str(error.getErrorMessage()),
                         'Traceback: ' + str(error.getTraceback())]))
            except:
                traceback.print_exc(file=sys.stdout)

            self.request.setResponseCode(INTERNAL_SERVER_ERROR)
            if self.debug:
                self.request.write(('Downloader error: ' + str(error.getErrorMessage())).encode('utf-8'))
                self.request.write(('Traceback: ' + str(error.getTraceback())).encode('utf-8'))
            else:
                err_message = self.error_html('<h1>PolitePol says: "Something wrong"</h1> <p><b>Try to refresh page or open an issue: <a href="https://github.com/ashcoft/">github.com/ashcoft</a></b>\n(Help us to improve our service with your feedback)</p> <p><i>Scary mantra: %s</i></p>' % escape(error.getErrorMessage()))
                self.request.write(err_message.encode('utf-8'))

            self.request.finish()

    def downloadStarted(self, response):
        self.response = response

        d = ppReadBody(response, self.max_size)
        d.addCallback(self.downloadDone)
        d.addErrback(self.downloadError)
        return response

    def downloadDone(self, response_str):
        url = self.response.request.absoluteURI
        if isinstance(url, bytes):
            url = url.decode('utf-8', 'replace')

        print('Response <%s> ready (%s bytes)' % (url, len(response_str)))
        sresponse = self.buildScrapyResponse(self.response, response_str, url)

        if self.selector_defer:
            self.selector_defer.callback(sresponse)
        else:
            self.writeResponse(sresponse)
            self.run_memon()

    def writeResponse(self, sresponse): #, response_str='PolitePol: Local page processing is failed'
        sresponse = self._decompress(sresponse)

        # Pages behind bot protection (Cloudflare and friends) return a
        # challenge instead of content. Report it for feeds too, so challenge
        # markup is never published as posts.
        if self._is_bot_challenge(sresponse.body):
            self._write_error(
                502, 'This site blocks automated access',
                'The page answered with a bot-protection challenge (for example '
                'Cloudflare\'s "Just a moment..."), so its content cannot be read '
                'here. Try another page or subscribe to the site\'s own RSS feed.')
            return
        if sresponse.status >= 400:
            self._write_error(
                sresponse.status, 'The page returned HTTP %s' % sresponse.status,
                self._status_detail(sresponse.status))
            return

        response_headers = self.prepare_response_headers(sresponse.headers)

        if (isinstance(sresponse, TextResponse)):
            ip = self.request.getHeader('x-real-ip') or self.request.client.host
            response_str = self.prepare_response_str(sresponse.selector, sresponse.headers, sresponse.text, sresponse.url, ip)
            if self.feed_config:
                response_headers = {b"Content-Type": b'text/xml; charset=utf-8'}
        else: # images and such
            response_str = sresponse.body

        for k, v in response_headers.items():
            self.request.setHeader(k, v)

        if isinstance(response_str, str):
            response_str = response_str.encode('utf-8')
        self.request.write(response_str)
        self.request.finish()

    # A small compressed body can expand to hundreds of megabytes.
    MAX_DECOMPRESSED_SIZE = 32 * 1024 * 1024

    # Only challenge-specific signals: a normal article may quote a phrase
    # like "Just a moment..." or load Cloudflare's JavaScript Detections.
    BOT_CHALLENGE_TITLES = (
        b'just a moment...',
        b'attention required! | cloudflare',
        b'checking your browser before accessing',
        b'enable javascript and cookies to continue',
    )
    BOT_CHALLENGE_MARKERS = (
        b'id="cf-challenge-running"',
        b'id="challenge-form"',
        b'cf-browser-verification',
        b'_cf_chl_opt',
    )

    def _is_bot_challenge(self, body):
        title = re.search(rb'<title[^>]*>(.*?)</title>', body, re.S | re.I)
        if title:
            normalized = b' '.join(title.group(1).lower().split())
            if any(phrase in normalized for phrase in self.BOT_CHALLENGE_TITLES):
                return True
        lowered = body.lower()
        return any(marker in lowered for marker in self.BOT_CHALLENGE_MARKERS)

    @staticmethod
    def _status_detail(status):
        if status == 404:
            return 'The page was not found.'
        if status in (401, 403):
            return 'The site refused the request, so there is nothing to pick elements from.'
        if status >= 500:
            return 'The site returned a server error, so there is nothing to pick elements from.'
        return 'The site returned an error, so there is nothing to pick elements from.'

    def _write_error(self, status, title, detail):
        page = self.error_html(
            '<h1>PolitePol says: "%s"</h1>\n<p>%s</p>' % (escape(title), escape(detail)))
        self.request.setResponseCode(status)
        self.request.setHeader(b'Content-Type', b'text/html; charset=utf-8')
        self.request.write(page.encode('utf-8'))
        self.request.finish()

    def _decompress(self, response):
        header = response.headers.get(b'Content-Encoding', b'')
        if isinstance(header, str):
            header = header.encode('utf-8')
        codings = [c.strip().lower() for c in header.split(b',') if c.strip()]
        if not codings:
            return response
        body = response.body
        # Content-Encoding lists the codings in the order they were applied.
        for coding in reversed(codings):
            body = self._decode_body(body, coding)
        headers = Headers({k: v for k, v in response.headers.items()
                           if k.lower() != b'content-encoding'})
        kwargs = {'body': body, 'headers': headers}
        if isinstance(response, TextResponse):
            # Let the decoded markup declare its own charset.
            kwargs['encoding'] = None
        return response.replace(**kwargs)

    def _decode_body(self, body, coding):
        if coding in (b'gzip', b'x-gzip'):
            return self._bounded_decompress(zlib.decompressobj(16 + zlib.MAX_WBITS), body)
        if coding == b'deflate':
            try:
                return self._bounded_decompress(zlib.decompressobj(zlib.MAX_WBITS), body)
            except zlib.error:
                return self._bounded_decompress(zlib.decompressobj(-zlib.MAX_WBITS), body)
        if coding == b'br':
            return self._bounded_brotli(body)
        return body

    BROTLI_CHUNK_SIZE = 1024 * 1024

    def _bounded_brotli(self, body):
        decompressor = brotli.Decompressor()
        parts = []
        total = 0
        chunk = decompressor.process(body, output_buffer_limit=self.BROTLI_CHUNK_SIZE)
        while True:
            parts.append(chunk)
            total += len(chunk)
            if total > self.MAX_DECOMPRESSED_SIZE:
                raise ValueError('Decompressed response is too large')
            if decompressor.is_finished():
                return b''.join(parts)
            chunk = decompressor.process(b'', output_buffer_limit=self.BROTLI_CHUNK_SIZE)
            if not chunk:
                raise ValueError('Incomplete brotli stream')

    def _bounded_decompress(self, decompressor, body):
        out = decompressor.decompress(body, self.MAX_DECOMPRESSED_SIZE)
        if decompressor.unconsumed_tail:
            raise ValueError('Decompressed response is too large')
        out += decompressor.flush()
        if len(out) > self.MAX_DECOMPRESSED_SIZE:
            raise ValueError('Decompressed response is too large')
        return out

    def prepare_response_headers(self, headers):
        return {}

    def prepare_response_str(self, selector, headers, page_unicode, url, ip=None):
        if self.feed_config:
            if self.sanitize:
                self.sanitizeAndNumerate(selector, numerate=False, sanitize_anchors=False)
            [response_str, post_cnt, new_post_cnt] = self.feed.buildFeed(selector, page_unicode, self.feed_config)
            if self.stat_tool:
                self.stat_tool.trace(ip=ip, feed_id=self.feed_config['id'], post_cnt=post_cnt, new_post_cnt=new_post_cnt)
        else:
            response_str = self.setBaseAndRemoveScriptsAndMore(selector, headers, url)
            if self.stat_tool:
                self.stat_tool.trace(ip=ip, feed_id=0, post_cnt=0, new_post_cnt=0, url=url)
        return response_str


    def run_memon(self):
        if self.memon:
            d = defer.Deferred()
            reactor.callLater(0, d.callback, None)
            d.addCallback(self.memon.show_diff)
            d.addErrback(lambda err: print("Memory Monitor error: %s\nPGC traceback: %s" % (err.getErrorMessage(), err.getTraceback())))


class Site(resource.Resource):
    isLeaf = True

    feed_regexp = re.compile(rb'^/feed/(\d{1,10})')


    def __init__(self, db_creds, snapshot_dir, user_agent, debug=False, limiter=None, memon=None, stat_tool=None, prefetch_dir=None, feed=None, downloadercls=None, max_size=IGNORE_SIZE, reader=None):
        self.db_creds = db_creds
        self.snapshot_dir = snapshot_dir
        self.user_agent = user_agent
        self.limiter = limiter
        self.prefetch_dir = prefetch_dir
        self.reader = reader if reader is not None else ReaderEndpoints(user_agent)

        self.feed = feed or Feed(db_creds)
        self.debug = debug
        self.stat_tool = stat_tool
        self.memon= memon
        self.max_size = max_size
        self.downloadercls = downloadercls or Downloader

    def startRequest(self, request, url, feed_config = None, selector_defer=None, sanitize=False):
        if isinstance(url, bytes):
            url = url.decode('utf-8', 'replace')
        downloader = self.downloadercls(self.feed, self.debug, self.snapshot_dir, self.stat_tool, self.memon,
                                        request=request, url=url, feed_config=feed_config,
                                        selector_defer=selector_defer, sanitize=sanitize, max_size=self.max_size)

        sresponse = self.tryLocalPage(url)
        if sresponse:
            if selector_defer:
                reactor.callLater(0, selector_defer.callback, sresponse)
            else:
                downloader.writeResponse(request, sresponse, feed_config)
        else:
            agent = BrowserLikeRedirectAgent(
                Agent(reactor,
                    contextFactory=ScrapyClientContextFactory(), # skip certificate verification
                    connectTimeout=10),
                    #pool=pool),
                redirectLimit=5
            )

            d = agent.request(
                b'GET',
                url.encode('utf-8'),
                twisted_headers({
                    b'Accept': [b'text/html,application/xhtml+xml,application/xml;q=0.9,'
                                b'image/avif,image/webp,*/*;q=0.8'],
                    b'Accept-Language': [b'en-US,en;q=0.9'],
                    b'Accept-Encoding': [b'gzip, deflate, br'],
                    b'Upgrade-Insecure-Requests': [b'1'],
                    b'Sec-Fetch-Dest': [b'document'],
                    b'Sec-Fetch-Mode': [b'navigate'],
                    b'Sec-Fetch-Site': [b'none'],
                    b'Sec-Fetch-User': [b'?1'],
                    b'User-Agent': [self.user_agent.encode('utf-8')]
                }),
                None
            )
            print('Request <GET %s> started' % (url,))
            d.addCallback(downloader.downloadStarted)
            d.addErrback(downloader.downloadError)

    def tryLocalPage(self, url):
        if self.prefetch_dir:
            if isinstance(url, bytes):
                url = url.decode('utf-8', 'replace')
            m = sha256(url.encode('utf-8')).hexdigest()
            domain = six.moves.urllib.parse.urlparse(url).netloc
            base_dir = os.path.realpath(self.prefetch_dir)
            boundary = base_dir.rstrip(os.path.sep) + os.path.sep
            safe_domain = re.sub(r'[^A-Za-z0-9._-]', '_', domain)
            fpath = os.path.realpath(os.path.join(base_dir, m + '.' + safe_domain))

            if fpath.startswith(boundary):
                fd = -1
                try:
                    # O_NOFOLLOW prevents a symlink swap between the
                    # realpath() check and the open() from escaping base_dir.
                    fd = os.open(fpath, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
                    if stat.S_ISREG(os.fstat(fd).st_mode):
                        with os.fdopen(fd, 'rb') as f:
                            fd = -1  # ownership transferred to fdopen
                            return pickle.load(f)
                except (IOError, OSError):
                    pass
                finally:
                    if fd != -1:
                        os.close(fd)
        return None

    def render_GET(self, request):
        '''
        Render page for frontend or RSS feed
        '''
        if self.reader and self.reader.handles(request.path):
            return self.reader.get(request)
        if b'url' in request.args: # page for frontend
            raw_url = request.args[b'url'][0] if request.args.get(b'url') else b''
            url = _http_url(raw_url)
            if not url:
                request.setResponseCode(400)
                return b'Url is invalid'

            self.startRequest(request, url, sanitize=True)
            return NOT_DONE_YET
        elif self.feed_regexp.match(request.uri) is not None: # feed

            feed_id = self.feed_regexp.match(request.uri).groups()[0].decode('ascii')
            sanitize = request.uri.endswith(b'?sanitize=Y')

            time_left = self.limiter.check_request_time_limit(request.uri) if self.limiter else 0
            if time_left:
                request.setResponseCode(429)
                request.setHeader('Retry-After', str(time_left) + ' seconds')
                return b'Too Many Requests. Retry after %s seconds' % (str(time_left))
            else:
                res = self.feed.getFeedData(feed_id)

                if isinstance(res, six.string_types): # error message
                    return res.encode('utf-8')

                url, feed_config = res
                url = _http_url(url)
                if not url:
                    request.setResponseCode(400)
                    return b'Feed URL is invalid'
                self.startRequest(request, url, feed_config, sanitize=sanitize)
                return NOT_DONE_YET
        else: # neither page and feed
            return b'Url is invalid'

    def render_POST(self, request):
        if self.reader and self.reader.handles(request.path):
            return self.reader.post(request)
        request.setResponseCode(405)
        return b'Method not allowed'

    def render_OPTIONS(self, request):
        if self.reader and self.reader.handles(request.path):
            return self.reader.options(request)
        request.setResponseCode(405)
        return b'Method not allowed'

class Server(object):

    def __init__(self, port, db_creds, snapshot_dir, user_agent, debug=False, limiter=None, memon=None, stat_tool=None, prefetch_dir=None, feed=None, sitecls=None, downloadercls=None, max_size=IGNORE_SIZE, reader=None):
        self.port = port
        self.db_creds = db_creds
        self.snapshot_dir = snapshot_dir
        self.user_agent = user_agent
        self.debug = debug
        self.limiter = limiter
        self.memon = memon
        self.stat_tool=stat_tool
        self.prefetch_dir = prefetch_dir

        self.log_handler = LogHandler()

        if not sitecls:
            sitecls = Site

        self.site = sitecls(self.db_creds, self.snapshot_dir, self.user_agent, self.debug, self.limiter, self.memon, self.stat_tool, self.prefetch_dir, feed, downloadercls=downloadercls, max_size=max_size, reader=reader)

    def requestSelector(self, url=None, feed_config=None):
        d = defer.Deferred()
        self.site.startRequest(None, url, feed_config=feed_config, selector_defer=d)
        return d

    def run(self):
        endpoints.serverFromString(reactor, "tcp:%s" % self.port).listen(server.Site(self.site))
        reactor.run()
