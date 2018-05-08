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
        self.siteroot = ""
        self.wsroot = ""
        self.state = {"folder": "", "ip": "", "wsroot": ""}

    def clearBuffer(self):
        """
        Clear the buffer

        :return:
        """
        self.buff = []

    def appendBuffer(self, newEntry):
        """
        Add a string to the buffer

        :param newEntry: The string to add
        :return: None
        """
        self.buff.append(newEntry)

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
            return userstate_pb2.startReply(status="OK")
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
        id = request.id
        key = request.key
        if id in userspace:
            if key in userspace[id].state:
                return userstate_pb2.getReply(value=userspace[id].state[key])
            else:
                raise RuntimeError("Bad userspace reference")
        else:
            raise RuntimeError("Incorrect user key")

    def set(self, request, context):
        global userspace
        id = request.id
        key = request.key
        value = request.value
        if id in userspace:
            if key in userspace[id].state:
                userspace[id].state[key] = value
                return userstate_pb2.statReply(status="OK")
            else:
                raise RuntimeError("Bad userspace reference when writing")
        else:
            raise RuntimeError("Incorrect user key when writing")

    def check(self, request, context):
        global userspace
        id = request.id
        return userstate_pb2.boolReply(value=(id in userspace))

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
