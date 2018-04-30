#!/usr/bin/env python

import tornado.ioloop
import tornado.web
import tornado.websocket
import os
import sys
import socket
import backend

import glob

print(glob.glob("*"))
print(glob.glob("/stoacont/example/task1/product/*"))

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
            self.render(backend.webPath+"ui/login.html", websocketRoot=wsroot, hostname=thishost)


class Authenticate(tornado.web.RequestHandler):
    def get(self):
        # print(self.get_argument("blah"))
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
