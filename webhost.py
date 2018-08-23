#!/usr/bin/env python

import tornado.ioloop
import tornado.web
import tornado.websocket
import os
import sys
import socket
import backend
import re

if len(sys.argv) > 2:
    portnum = int(sys.argv[2])
else:
    portnum = 8888

backend.siteroot = "http://{}:{}".format(socket.gethostname(), portnum)
wsroot = "ws://{}:{}/ws".format(socket.gethostname(), portnum)

thishost = backend.siteroot.split(':')[1][2:]

backend.setTarget(sys.argv[1])

ioloophandle = ''


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        global thishost, wsroot
        user = self.request.remote_ip
        getargs = self.request.arguments
        backend.startBackend()
        if backend.usercheck(user):
            actionhtml = ""
            if 'action' in getargs:
                actionhtml = 'view("{}")'.format(getargs['action'][0].decode())
            if 'loc' in getargs:
                backend.setCurrent(user, getargs['loc'][0].decode())

            self.render(backend.webPath+"ui/index.html",
                        websocketRoot=backend.getwsroot(user),
                        textContent=backend.projectInfo(),
                        hostname=thishost,
                        action=actionhtml)
        else:
            hostname = re.split(":", self.request.host)[0]
            backend.siteroot = "http://{}:{}".format(hostname, portnum)
            wsroot = "ws://{}:{}/ws".format(hostname, portnum)
            thishost = backend.siteroot.split(':')[1][2:]
            self.render(backend.webPath+"ui/login.html", websocketRoot=wsroot, hostname=thishost)


class Authenticate(tornado.web.RequestHandler):
    def get(self):
        global thishost, wsroot
        hostname = re.split(":", self.request.host)[0]
        backend.siteroot = "http://{}:{}".format(hostname, portnum)
        wsroot = "ws://{}:{}/ws".format(hostname, portnum)
        thishost = backend.siteroot.split(':')[1][2:]
        self.render(backend.webPath+"ui/login.html", websocketRoot=wsroot, hostname=thishost)


class App(tornado.web.Application):
    def __init__(self):
        handlers = [
                    (r"/login", Authenticate),
                    (r"/", MainHandler),
                    (r"/ws", backend.SocketHandler),
                    (r"/file/(.*)", tornado.web.StaticFileHandler,
                     {'path': backend.targetFolder}),
                    (r"/stage/(.*)", tornado.web.StaticFileHandler,
                     {'path': os.getcwd()+"/usercache"}),
                    (r"/docs/(.*)", tornado.web.StaticFileHandler,
                     {'path': os.getcwd()+"/docs/_build/html"})
        ]
        settings = {"static_path": os.getcwd()+"/ui"}
        tornado.web.Application.__init__(self, handlers, **settings)


print("Starting backend at {}".format(backend.targetFolder))

app = App()
app.listen(portnum)
ioloophandle = tornado.ioloop.IOLoop.current()
ioloophandle.start()
