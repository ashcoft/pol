import w3lib.url
import w3lib.html

import six
from lxml import etree
from lxml import html as lxml_html
import hashlib
import re, sys
from hashlib import md5

from feedgenerator import Rss201rev2Feed, Enclosure
import datetime

import MySQLdb
from contextlib import closing
from settings import DATABASES, DOWNLOADER_USER_AGENT
from twisted.logger import Logger

from .db import get_conn


log = Logger()


def _fingerprint(*parts):
    """128-bit content fingerprint used to detect duplicate posts.

    Fits the legacy CHAR(32) posts.md5sum column; not security sensitive."""
    digest = hashlib.blake2b(digest_size=16)
    for part in parts:
        digest.update(part.encode('utf-8'))
    return digest.hexdigest()


def _as_text(value):
    return value.decode('utf-8') if isinstance(value, bytes) else value


def _normalize_images(fragment, base_url):
    """Give lazy-loaded and relative <img> tags a usable absolute src."""
    if '<img' not in fragment:
        return fragment
    try:
        root = lxml_html.fragment_fromstring(fragment, create_parent='div')
    except (etree.ParserError, ValueError):
        return fragment
    changed = False
    for img in root.iter('img'):
        src = img.get('src') or ''
        lazy_src = img.get('data-src') or img.get('data-original') or img.get('data-lazy-src')
        if lazy_src and (not src or src.startswith('data:')):
            src = lazy_src
            img.set('src', src)
            changed = True
        if src and base_url and not re.match(r'^(?:[a-z][a-z0-9+.-]*:|//)', src, re.I):
            img.set('src', six.moves.urllib.parse.urljoin(base_url, src))
            changed = True
        if 'loading' in img.attrib:
            del img.attrib['loading']
    if not changed:
        return fragment
    return (root.text or '') + ''.join(
        etree.tostring(child, encoding='unicode', method='html') for child in root)


class Feed(object):

    url_hash_regexp = re.compile('(#.*)?$')

    POST_TIME_DISTANCE = 15 # minutes, RSS Feed Reader skip same titles created in 10 min interval

    FIELD_IDS = {'title': 1, 'description': 2, 'link': 3}

    def __init__(self, db_creds):
        self.db_creds = db_creds


    def save_post(self, conn, created, feed_id, post_fields):
        with conn.cursor() as cur:
            cur.execute("""insert into frontend_post (md5sum, created, feed_id)
                            values (unhex(%s), %s, %s)""", (post_fields['md5'], created, feed_id))
            post_id = cur.lastrowid
            log.info('Post saved id:{id!r}', id=post_id)
            return post_id

    def fill_time(self, feed_id, items):
        if not items:
            return 0

        new_post_cnt = 0
        for item in items:
            item['md5'] = _fingerprint(
                *[item[key] for key in ['title', 'description', 'link'] if key in item])

        #fetch dates from db
        fetched_dates = {}
        with closing(get_conn(self.db_creds)) as conn:
            with conn.cursor() as cur:
                quoted_hashes = ','.join(["unhex('%s')" % (i['md5']) for i in items])

                cur.execute("""select lower(hex(p.md5sum)), p.created, p.id
                               from frontend_post p
                               where p.md5sum in (%s)
                               and p.feed_id=%s""" % (quoted_hashes, feed_id,))
                rows = cur.fetchall()
                log.debug('Selected {count!r} posts', count=len(rows))
                for row in rows:
                    md5hash = row[0]
                    created = row[1]
                    post_id = row[2]
                    fetched_dates[md5hash] = created

            cur_time = datetime.datetime.utcnow()
            saved_times = {}
            for item in items:
                if item['md5'] in fetched_dates:
                    item['time'] = fetched_dates[item['md5']]
                else:
                    if item['md5'] in saved_times:
                        item['time'] = saved_times[item['md5']]
                    else:
                        self.save_post(conn, cur_time, feed_id, item)
                        saved_times[item['md5']] = cur_time
                        item['time'] = cur_time
                        new_post_cnt += 1
                    cur_time -= datetime.timedelta(minutes=self.POST_TIME_DISTANCE)
        return new_post_cnt

    def _build_link(self, html, doc_url, url):
        base_url = w3lib.html.get_base_url(html, doc_url)
        return six.moves.urllib.parse.urljoin(base_url, url)

    def buildFeed(self, selector, page_unicode, feed_config):
        selector.remove_namespaces()

        selector = selector
        tree = selector.root.getroottree()
        # get data from html
        items = []
        for node in selector.xpath(feed_config['xpath']):
            item = {}
            required_count = 0
            required_found = 0
            for field_name in ['title', 'description', 'link']:
                if field_name in feed_config['fields']:
                    if feed_config['required'][field_name]:
                        required_count += 1

                    extracted = node.xpath(feed_config['fields'][field_name]).extract()
                    if extracted:
                        item[field_name] = u''.join(extracted)
                        if feed_config['required'][field_name]:
                            required_found += 1
                        if field_name == 'link':
                            item['link'] = self._build_link(page_unicode, feed_config['uri'], item[field_name])

            if required_count == required_found:
                items.append(item)

        title = selector.xpath('//title/text()').extract_first()

        #build feed
        feed = Rss201rev2Feed(
            title = title if title else 'PolitePol: ' + feed_config['uri'],
            link=feed_config['uri'],
            description="Generated by PolitePol.\n"+\
                "Source page: " + feed_config['uri'],
            language="en",
        )
        new_post_cnt = self.fill_time(feed_config['id'], items)

        base_url = w3lib.html.get_base_url(page_unicode, feed_config['uri'])

        for item in items:
            title = item['title'] if 'title' in item else ''
            title = re.sub(r'<[^>]+>', '', title).strip()
            desc = item['description'] if 'description' in item else ''
            desc = _normalize_images(desc, base_url)
            time = item['time'] if 'time' in item else datetime.datetime.utcnow()
            if 'link' in item:
                link = item['link']
            else:
                # md5 is the published identity of link-less items; keep it stable.
                fragment = md5((title + desc).encode('utf-8'), usedforsecurity=False).hexdigest()  # nosec B324  # nosemgrep
                link = self.url_hash_regexp.sub('#' + fragment, feed_config['uri'])
            feed.add_item(
                title = title,
                link = link,
                unique_id = link,
                description = desc,
                #enclosure=Enclosure(fields[4], "32000", "image/jpeg") if  4 in fields else None, #"Image"
                pubdate = time
            )
        return [feed.writeString('utf-8'), len(items), new_post_cnt]

    def getFeedData(self, feed_id):
        # get url, xpathes
        feed = {}

        with closing(get_conn(self.db_creds, dict_result=True)) as conn:
            with conn.cursor() as cur:
                cur.execute("""select f.uri, f.xpath as feed_xpath, fi.name, ff.xpath, fi.required
                               from frontend_feed f
                               right join frontend_feedfield ff on ff.feed_id=f.id
                               left join frontend_field fi on fi.id=ff.field_id
                               where f.id=%s""", (feed_id,))
                rows = cur.fetchall()

                for row in rows:
                    if not feed:
                        feed['id'] = feed_id
                        feed['uri'] = row['uri']
                        feed['xpath'] = _as_text(row['feed_xpath'])
                        feed['fields'] = {}
                        feed['required'] = {}
                    feed['fields'][row['name']] = _as_text(row['xpath'])
                    feed['required'][row['name']] = row['required']

        if feed:
            return [feed['uri'], feed]
        else:
            return 'Feed generator error: config of feed is empty'
