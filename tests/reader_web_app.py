"""Tiny Twisted app used by test_reader_web.py (run in a subprocess)."""

import sys

from twisted.internet import reactor
from twisted.web import resource, server

from pol.reader.web import ReaderEndpoints

port = int(sys.argv[1])
endpoints = ReaderEndpoints('pol-test/1', cache_backend='memory', timeout=5)


class Root(resource.Resource):
    isLeaf = True

    def render_GET(self, request):
        return endpoints.get(request)

    def render_POST(self, request):
        return endpoints.post(request)

    def render_OPTIONS(self, request):
        return endpoints.options(request)


reactor.listenTCP(port, server.Site(Root()))
reactor.run(installSignalHandlers=False)
