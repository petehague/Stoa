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

class secureHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("stoa-user")


class MainHandler(secureHandler):
    @tornado.web.authenticated
    def get(self):
        global thishost, wsroot
        getargs = self.request.arguments
        backend.startBackend()
        actionhtml = ""
        user = self.get_secure_cookie("stoa-user")
        if 'action' in getargs:
            actionhtml = 'view("{}")'.format(getargs['action'][0].decode())
        if 'loc' in getargs:
            backend.setCurrent(user, getargs['loc'][0].decode())

        tokens = re.split(":", self.request.host)
        hostname = tokens[0]
        if len(tokens)>1:
            clientport = tokens[1]
        else:
            clientport = 80
        wsroot = "ws://{}:{}/ws".format(hostname, clientport)
        self.render(backend.webPath+"ui/index.html",
                    websocketRoot=wsroot,
                    textContent=backend.projectInfo("user_"+user.decode()),
                    hostname=thishost,
                    action=actionhtml)

class securedStatic(tornado.web.StaticFileHandler):
    @tornado.web.authenticated
    def placeholder():
        return 0


class Authenticate(tornado.web.RequestHandler):
    def get(self):
        global thishost, wsroot

        self.clear_cookie("stoa-user")

        tokens = re.split(":", self.request.host)
        hostname = tokens[0]
        if len(tokens)>1:
            clientport = tokens[1]
        else:
            clientport = 80
        backend.siteroot = "http://{}:{}".format(hostname, clientport)
        wsroot = "ws://{}:{}/ws".format(hostname, clientport)
        thishost = backend.siteroot.split(':')[1][2:]
        self.render(backend.webPath+"ui/login.html", websocketRoot=wsroot, hostname=thishost)

    def post(self):
        username = self.get_argument("uname")
        if backend.usernamecheck(username):
            self.set_secure_cookie("stoa-user", username)
            backend.userlogin(username, self.request.remote_ip)
            print("Stored cookie: {}".format(username))
            self.redirect("/")
        else:
            self.redirect("/login")
settings = {"static_path": os.getcwd()+"/ui",
            "login_url": "/login",
            "cookie_secret": "Add later"}

app = tornado.web.Application([
    (r"/login", Authenticate),
    (r"/", MainHandler),
    (r"/ws", backend.SocketHandler),
    (r"/file/(.*)", securedStatic, {'path': backend.targetFolder}),
    (r"/stage/(.*)", securedStatic, {'path': os.getcwd()+"/usercache"}),
    (r"/docs/(.*)", securedStatic, {'path': os.getcwd()+"/docs/_build/html"}),
    (r"/conesearch/(.*)", backend.ConeSearchHandler)
    ], **settings)

print("Starting backend at {}".format(backend.targetFolder))


app.listen(portnum)
ioloophandle = tornado.ioloop.IOLoop.current()
ioloophandle.start()
