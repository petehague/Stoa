from multiprocessing import Queue

import sys
import sqlite3 as sql

from concurrent import futures
import grpc
import userstate_pb2
import userstate_pb2_grpc

userspace = {}

started = False

class userState():
    def __init__(self):
        """
        Class to keep track of the state of each user

        """
        self.folder = ""
        self.ip = ""
        self.run = "Nothing"
        self.proc = None
        self.buff = []
        self.q = Queue()
        self.procreport = ""
        self.state = {"folder": "", "ip": "", "wsroot": ""}

    def appendQueue(self):
        """
        Add the contents of the process queue to the buffer

        :return: None
        """
        if not self.q.empty():
            self.buff.append(self.q.get())

    def finalise(self):
        """
        Checks if the process has finished, and if so performs finalisation operations

        :return: None
        """
        if self.q.empty():
            if self.proc is not None:
                if not self.proc.is_alive():
                    self.procreport = "Finished"
                    self.proc = None
                    print("Process for {} finished".format(self.ip))

class userstateServer(userstate_pb2_grpc.UserstateServicer):
    def start(self, request, context):
        global started
        global userspace
        if started:
            return userstate_pb2.statReply(status="OK")
        started=True
        dbcon = sql.connect('contents.db')
        with dbcon:
            c = dbcon.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS tblUsers(\
                       UID INT,\
                       Username VARCHAR(100))")
            c.execute("SELECT * FROM tblUsers")
            users = c.fetchall()
            for u in users:
                userspace[u[1]] = userState()
            if len(users)==0:
                c.execute("INSERT INTO tblUsers (UID, Username) VALUES (0,'admin')")
                userspace['admin'] = userState()
        return userstate_pb2.statReply(status="OK")

    def get(self, request, context):
        global userspace
        userid = request.id
        key = request.key
        if userid in userspace:
            if key in userspace[userid].state:
                return userstate_pb2.getReply(value=userspace[userid].state[key])
            else:
                raise RuntimeError("Bad userspace reference")
        else:
            raise RuntimeError("Incorrect user key")

    def set(self, request, context):
        global userspace
        userid = request.id
        key = request.key
        value = request.value
        if userid in userspace:
            if key in userspace[userid].state:
                userspace[userid].state[key] = value
                return userstate_pb2.statReply(status="OK")
            else:
                raise RuntimeError("Bad userspace reference when writing")
        else:
            raise RuntimeError("Incorrect user key when writing")

    def check(self, request, context):
        global userspace
        userid = request.id
        return userstate_pb2.boolReply(value=(userid in userspace))

    def append(self, request, context):
        global userspace
        userid = request.id
        report = request.report
        if userid in userspace:
            userspace[userid].buff.append(report)
        else:
            raise RuntimeError("Incorrect user key")
        return userstate_pb2.boolReply(value=True)

    def pop(self, request, context):
        global userspace
        userid = request.id
        if userid not in userspace:
            raise RunTimeError("Incorrect user key")
        if len(userspace[userid].buff)>0:
            retstr = userspace[userid].buff.pop(0)
            return userstate_pb2.popReply(value=retstr)
        return userstate_pb2.popReply(value="")

    def tail(self, request, context):
        global userspace
        userid = request.id
        n = request.n
        if userid in userspace:
            return userstate_pb2.tailReply(buff="".join(userspace[userid].buff[-n:]))
        else:
            raise RuntimeError("Incorrect user key")



if __name__ == "__main__":
    serverinst = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    userstate_pb2_grpc.add_UserstateServicer_to_server(userstateServer(), serverinst)
    portnum = serverinst.add_insecure_port('[::]:6999')
    serverinst.start()
    print("User state server started on port {}".format(portnum))
    try:
        while True:
            sys.stdout.flush()
    except KeyboardInterrupt:
        serverinst.stop(0)
