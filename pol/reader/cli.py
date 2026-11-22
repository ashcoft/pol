"""Command line interface: ``morss`` / ``pol-feed`` / ``python -m pol.reader``."""

from __future__ import annotations

import argparse
import json
import sys

from .errors import ReaderError
from .jsonfeeds import load_rules
from .pipeline import Options, discover, process


def build_parser():
    parser = argparse.ArgumentParser(
        prog='morss',
        description='Read feeds, extract full text and export RSS/JSON/CSV/HTML.')
    parser.add_argument('url', nargs='?', help='feed or page URL')

    output = parser.add_argument_group('output')
    output.add_argument('--format', default='rss', choices=('rss', 'json', 'csv', 'html'),
                        help='output format (default: rss)')
    output.add_argument('--callback', help='JSONP callback name (implies --format jsonp)')
    output.add_argument('--indent', action='store_true', help='pretty-print XML/JSON')
    output.add_argument('-o', '--output', help='write to a file instead of stdout')

    action = parser.add_argument_group('action')
    action.add_argument('--discover', action='store_true',
                        help='list feeds found on the page as JSON')
    action.add_argument('--post', metavar='STRING',
                        help='POST this body to the feed URL instead of a GET')
    action.add_argument('--order', default='first', choices=('first', 'last', 'newest', 'oldest'),
                        help='which items to enrich when max-items is reached (default: first)')
    action.add_argument('--firstlink', action='store_true',
                        help='use the first <a> in the description as the item link')
    action.add_argument('--nolink', action='store_true',
                        help='drop links from item content but keep their text')
    action.add_argument('--noref', action='store_true', help='drop item links')
    action.add_argument('--proxy', action='store_true', help='do not fetch full text')
    action.add_argument('--fulltext', dest='fulltext', action='store_true', default=True,
                        help='fetch full text (default)')
    action.add_argument('--no-fulltext', dest='fulltext', action='store_false',
                        help='do not fetch full text')
    action.add_argument('--clip', action='store_true',
                        help='keep the original summary above the full text')
    action.add_argument('--resolve', action='store_true',
                        help='replace tracking links with direct links')
    action.add_argument('--search', help='only keep items containing this text')
    action.add_argument('--xpath', help='extract the article with this XPath instead of readability')
    action.add_argument('--max-items', type=int, default=20,
                        help='maximum items to enrich (default: 20)')

    cache = parser.add_argument_group('cache')
    cache.add_argument('--cache', action='store_true', help='enable the HTTP cache')
    cache.add_argument('--offline', action='store_true',
                       help='only use cached responses (implies --cache)')
    cache.add_argument('--force', action='store_true', help='bypass cached responses')
    cache.add_argument('--cache-backend', choices=('memory', 'redis', 'diskcache', 'none'),
                       help='cache backend (default: memory, or diskcache with --cache-dir)')
    cache.add_argument('--cache-dir', help='directory for the diskcache backend')
    cache.add_argument('--cache-ttl', type=int, default=3600, help='cache TTL in seconds')
    cache.add_argument('--redis-url', help='redis URL (default: $REDIS_URL)')

    custom = parser.add_argument_group('custom feeds')
    custom.add_argument('--mode', choices=('json', 'html', 'xml', 'auto'),
                        help='parser to use for custom feed rules')
    custom.add_argument('--rules', help='JSON or INI file with custom feed rules')
    custom.add_argument('--items', help='rule selecting the items (path or XPath)')
    custom.add_argument('--item-link', help='rule for the item link')
    custom.add_argument('--item-title', help='rule for the item title')
    custom.add_argument('--item-content', help='rule for the item content')
    custom.add_argument('--item-desc', help='rule for the item summary')
    custom.add_argument('--item-time', help='rule for the item date')
    custom.add_argument('--item-author', help='rule for the item author')
    custom.add_argument('--item-image', help='rule for the item image')

    misc = parser.add_argument_group('misc')
    misc.add_argument('--silent', action='store_true',
                      help='do not print the feed (useful while debugging)')
    misc.add_argument('--timeout', type=float, default=20, help='HTTP timeout in seconds')
    misc.add_argument('--insecure', action='store_true', help='do not verify TLS certificates')
    misc.add_argument('--no-meta', action='store_true', help='do not follow meta refresh')
    misc.add_argument('--allow-private', action='store_true',
                      help='allow loopback/private destinations (local development only)')
    misc.add_argument('--version', action='version', version='pol-reader 1.0')
    return parser


def _options(args):
    fmt = 'jsonp' if args.callback else args.format
    rules = load_rules(args.rules) if args.rules else None
    return Options(
        format=fmt,
        callback=args.callback,
        fulltext=args.fulltext and not args.proxy,
        clip=args.clip,
        resolve=args.resolve,
        search=args.search,
        post=args.post,
        order=args.order,
        firstlink=args.firstlink,
        nolink=args.nolink,
        noref=args.noref,
        silent=args.silent,
        xpath=args.xpath,
        items=args.items,
        item_link=args.item_link,
        item_title=args.item_title,
        item_content=args.item_content,
        item_time=args.item_time,
        item_desc=args.item_desc,
        item_author=args.item_author,
        item_image=args.item_image,
        mode=args.mode,
        rules=rules,
        max_items=args.max_items,
        timeout=args.timeout,
        verify_ssl=not args.insecure,
        follow_meta=not args.no_meta,
        allow_private=True if args.allow_private else None,
        indent=args.indent,
        cache=args.cache or args.offline,
        cache_only=args.offline,
        force=args.force,
        cache_backend=args.cache_backend,
        cache_dir=args.cache_dir,
        cache_ttl=args.cache_ttl,
        redis_url=args.redis_url,
    )


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.url:
        parser.error('a URL is required')

    options = _options(args)
    try:
        if args.discover:
            refs = discover(args.url, options=options)
            payload = json.dumps({'feeds': [ref.as_dict() for ref in refs]},
                                 ensure_ascii=False, indent=2 if args.indent else None)
        else:
            payload = process(args.url, options=options).text
    except ReaderError as exc:
        sys.stderr.write('error: %s\n' % exc)
        return 1
    except ValueError as exc:
        sys.stderr.write('error: %s\n' % exc)
        return 2

    if args.silent:
        return 0
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as handle:
            handle.write(payload)
            if not payload.endswith('\n'):
                handle.write('\n')
    else:
        sys.stdout.write(payload)
        if not payload.endswith('\n'):
            sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
