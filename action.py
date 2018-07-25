#!/usr/bin/env python

import cwltool.factory
from yml import yamler, writeyaml
import re
import os
import sys
import shutil
import time
import glob
import tempfile
from cwltool.errors import WorkflowException

from worktable import Worktable

from concurrent import futures
import grpc
import action_pb2
import action_pb2_grpc

import userstate_interface as userstate

config = yamler(open("stoa.yml", "r"))
targetFolder = config['stoa-info']['workspace']

scriptPath = os.path.realpath(__file__)
coreFolder = os.path.split(scriptPath)[0]
scriptFolder = coreFolder+os.sep+"actions"

os.environ['PATH'] += ":"+scriptFolder

lockStack = 0 

procStack = {}
#for name in userstate.getList():
#    procstack[name] = []

def ymlvars(ymlfile, output, pathname):
    f1 = open(ymlfile,"r")
    f2 = open(output,"w")
    for line in f1:
        result = line.replace("<path>", pathname)
        f2.write(result)
    f1.close()
    f2.close()

def cwlinvoke(pathname, taskfile, params):
    oldpath = os.environ["PATH"]
    os.environ["PATH"] += os.pathsep + pathname

    taskfac = cwltool.factory.Factory()
    t = taskfac.make(pathname+os.sep+taskfile)
    params["stoafolder"]=os.path.join(os.getcwd(),pathname)
    result = t(**params)

    os.environ["PATH"] = oldpath
    print(result)
    return result

def parsecwloutput(pathname, result, l=False):
    outlist = []
    for output in result:
        if l:
            outobj = output
        else:
            if type(result[output]) is list:
                outlist.append(parsecwloutput(pathname,result[output], l=True))
                continue
            outobj = result[output]
        if type(outobj) is dict:
            if outobj['basename']=='list.txt':
                f = open(outobj['location'][7:], "r")
                data = []
                for line in f:
                    data.append(line.strip())
                f.close()
                data = ['-'] if data==[] else data
                outlist.append(data)
                continue
            if outobj['class']=='File':
                outlist.append(os.path.join(pathname,outobj['basename']))
                shutil.copyfile(outobj['location'][7:], 
                                os.path.join(pathname, outobj['basename']))
                # TODO add a contingence for not file:// URLS (not sure why this would happen though)
        else:
            outlist.append(outobj)
    return outlist

def ExecCWL(cmdFile, pathname, keyname):
    result = {}
    success = 0
    if ".wtx" in cmdFile:
       wt = Worktable(cmdFile)
       wtFile = cmdFile
       cmdFile = "workflow.cwl"
       wt.unpack(pathname)
    else:
       wt = False
       cmdFile = scriptFolder + os.sep + cmdFile
    try:
        result = cwlinvoke(pathname, cmdFile,
                           yamler(open(pathname+"/run.yml", "r"), convert=True))
        writeyaml(result, pathname+"/.pipelog.txt")
    except WorkflowException as werr:
        success = 1
        log = open(pathname+"/.pipelog.txt","a")
        log.write("Workflow Exception: {}\n".format(werr.args))
        log.close()
    if wt:
        index = wt.byref(keyname)
        wt.update(index,parsecwloutput(pathname, result))
        wt.save(wtFile)
                
    return success

def makeyml(pathname, command):
    """
    Generates a yml file to guide execution

    :param pathname: The path of the project of interest
    """

    if ".wtx" in command:
        wt = Worktable(command)
        cmdDict = wt.template
    else:
        cmdyml = (re.split(".cwl", command)[0]).strip() + ".yml"
        cmdDict = yamler(open(scriptFolder+"/"+cmdyml, "r"))

    n = wt.byref(pathname)
    for i in range(len(wt.fieldnames)):
        if "I_" in wt.fieldtypes[i]:
            cmdDict[wt.fieldnames[i]] = wt[n][i]

    writeyaml(cmdDict, pathname+"/runraw.yml")
    ymlvars(pathname+"/runraw.yml", pathname+"/run.yml", coreFolder+"/"+pathname)
    os.remove(pathname+"/runraw.yml")

def clearStack():
    global procStack, lockStack
    lockStack = 1
    for usertoken in procStack:
        if len(procStack[usertoken])>0:
            command = procStack[usertoken][0][0]
            pathname = procStack[usertoken][0][1]
            procStack[usertoken].pop(0)
            print(">> "+usertoken+" : "+command+" : "+pathname)
            #userstate.append(usertoken, pathname)
            if pathname[0]=='-':
                keyname = pathname[1:]
                pathname = targetFolder
            else:
                keyname = pathname
            keyname = pathname
            makeyml(pathname, command)
            result = ExecCWL(command, pathname, keyname)
            print("   Result: {}".format(result))
            if result>0:
               userstate.append(usertoken, '{}  <span class="bold"><span class="red">FAILED</span></span>'.format(pathname))
            else:
               userstate.append(usertoken, '{}  <span class="bold"><span class="green">OK</span></span>'.format(pathname))
    lockStack = 0

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
        print(request.cmdFile)
        return action_pb2.ExecCWLReply(result=ExecCWL(request.cmdFile, request.pathname))

    def push(self, request, context):
        global lockStack, procStack
        while lockStack>0:
          time.sleep(0.1)
        if request.usertoken not in procStack:
            procStack[request.usertoken] = []
        procStack[request.usertoken].append([request.cmdFile, request.pathname])
        return action_pb2.pushReply(mess="OK")

    def isFree(self, request, context):
        global procStack
        if request.usertoken not in procStack:
            procStack[request.usertoken] = []
        if procStack[request.usertoken]==[]:
            return action_pb2.isFreeReply(result=True)
        else:
            return action_pb2.isFreeReply(result=False)

    def glob(self, request, context):
        print(request.pathname)
        list = myGlob(request.pathname)
        for filename in list:
            yield action_pb2.globReply(filename=filename)

if __name__ == "__main__":
    serverinst = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    action_pb2_grpc.add_ActionServicer_to_server(actionServer(), serverinst)
    portnum = serverinst.add_insecure_port('[::]:7000')
    serverinst.start()
    print("Action server started on port {}".format(portnum))
    try:
        while True:
            clearStack()
            time.sleep(1)
            sys.stdout.flush()
    except KeyboardInterrupt:
        serverinst.stop(0)
