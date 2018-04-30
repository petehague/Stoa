#!/usr/bin/env python

import cwltool.factory
from yml import yamler, writeyaml
import re
import os
import glob
from cwltool.errors import WorkflowException

from concurrent import futures
import grpc
import action_pb2
import action_pb2_grpc

opts = {}
scriptPath = os.path.realpath(__file__)
opts["ActionPath"] = "/".join(re.split("/", scriptPath)[:-1]) + "/actions/"

if os.path.exists(".pipeopts.txt"):
    optfile = open(".pipeopts.txt", "r")
    for line in optfile:
        key = re.split(" ", line)[0]
        value = line[len(key)+1:-1]
        opts[key] = value
    optfile.close()

procStack = []

def clearStack():
    if procStack==[]:
        return 1
    procStack.pop(1)
    print(">>")

def cwlinvoke(taskfile, params):
    taskfac = cwltool.factory.Factory()
    t = taskfac.make(taskfile)
    result = t(**params)
    return result


def manager(taskfile, paramfile, outfile):
    result = cwlinvoke(taskfile,yamler(open(paramfile,"r")))
    writeyaml(result, outfile)

def ExecCWL(cmdFile, pathname):
    result = {}
    success = 0
    try:
        result = manager(cmdFile, pathname+"/run.yml", pathname+"/.pipelog.txt")
    except WorkflowException as werr:
        success = 1
        log = open(pathname+"/.pipelog.txt","w")
        log.write("Workflow Exception: {}\n".format(werr.args))
        log.close()
    writeyaml(result, pathname+"/stoa_out.yml")
    return success

def makeyml(pathname, command):
    """
    Generates a yml file to guide execution, based on the specific->general hierarchy
    Run specific parameters override batch specific parameters override global parameters

    :param pathname: The path of the project of interest
    """

    if ".cwl" in command:
        cmdyml = (re.split(".cwl", command)[0]).strip() + ".yml"
        cmdDict = yamler(open(opts["ActionPath"]+"/"+cmdyml, "r"))
    else:
        cmdDict = {}
    globalDict = yamler(open(opts["ActionPath"]+"/stoa.yml","r"))
    if not os.path.exists("stoa.yml"):
        open("stoa.yml","a").close()
    batchDict = yamler(open("stoa.yml","r"))
    if not os.path.exists(pathname+"/stoa.yml"):
        open(pathname+"/stoa.yml","a").close()
    specDict = yamler(open(pathname+"/stoa.yml","r"))

    for key in cmdDict:
        globalDict[key] = cmdDict[key]
    for key in batchDict:
        globalDict[key] = batchDict[key]
    for key in specDict:
        globalDict[key] = specDict[key]

    writeyaml(globalDict, pathname+"/run.yml")

def myGlob(pathname):
    return glob.glob(pathname)

'''
    gRPC class: serves up functions to the clients
'''
class actionServer(action_pb2_grpc.ActionServicer):
    def makeyml(self, request, context):
        makeyml(request.pathname, request.command)
        return action_pb2.makeymlReply(mess="OK")

    def ExecCWL(self, request, context):
        return action_pb2.ExecCWLReply(result=ExecCWL(request.cmdFile, request.pathname))

    def push(self, request, context):
        procStack.append([request.cmdFile, request.pathname])
        return action_pb2.pushReply(mess="OK")

    def isFree(self, request, context):
        if procStack==[]:
            return action_pb2.isFreeReply(result=True)
        else:
            return action_pb2.isFreeReply(result=False)

    def glob(self, request, context):
        list = myGlob(request.pathname)
        for filename in list:
            yield action_pb2.globReply(filename=filename)

if __name__ == "__main__":
    #r = cwlinvoke("tool.cwl",yml.yamler(open("job.yml")))
    #print(r)
    serverinst = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    action_pb2_grpc.add_ActionServicer_to_server(actionServer(), serverinst)
    portnum = serverinst.add_insecure_port('[::]:7000')
    serverinst.start()
    print("Action server started on port {}".format(portnum))
    try:
        while True:
            clearStack()
    except KeyboardInterrupt:
        server.stop(0)
