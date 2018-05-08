#!/usr/bin/env python
"""
The Pipe module can be run as a standalone command line interface, but is
mainly designed to be used as the back end of the web interface
"""

# Python 2 compatibility
from __future__ import print_function
# from builtins import input

import glob
import re
import os
import hashlib
import time
import sys
# import fnmatch
import procdb
from yml import yamler, writeyaml

import grpc
import action_pb2
import action_pb2_grpc

# Python 2 compatibility
if sys.version_info[0] > 2:
    raw_input = input

# utils

verbose = False

config = yamler(open("stoa.yml", "r"))

if "target" in config['stoa-info']:
    targetFolder = config['stoa-info']['target']
else:
    targetFolder = "product"

scriptPath = os.path.realpath(__file__)
if "scriptPath" in config['stoa-info']:
    scriptFolder = config['stoa-info']['scriptPath']
else:
    scriptFolder = "actions"
scriptFolder = "/".join(re.split("/", scriptPath)[:-1]) + "/"+scriptFolder+"/"

# Connection to action server
if "ActionHost" in config['stoa-info']:
    acthost = config['stoa-info']["ActionHost"].strip()
else:
    acthost = "action"
actConnect = grpc.insecure_channel('{}:7000'.format(acthost))
actions = action_pb2_grpc.ActionStub(actConnect)

#Wrapper class
class Actions(object):
    @staticmethod
    def ExecCWL(cmdFile, pathname):
        print(cmdFile, pathname)
        request = action_pb2.ExecCWLReq(cmdFile = cmdFile,
                                        pathname = pathname)
        return actions.ExecCWL(request).result
    @staticmethod
    def makeyml(pathname, command):
        print(pathname, command)
        request = action_pb2.makeymlReq(pathname=pathname, command=command)
        actions.makeyml(request)

print("Pipeline started using actions at {}".format(scriptFolder))

prefixList = {}
metacmd = {}

databasepath = ""
queryID = 0


def doFlag(command):
    return procdb.doFlag(command)


def doUnflag(command):
    return procdb.doUnflag(command)


def isFlagged(command):
    return procdb.isFlagged(command)


def setProctabPath(pathname):
    """
    Sets the database path

    :param pathname: The path to an sqlite database file
    :return: None
    """
    global databasepath
    databasepath = pathname
    procdb.init(databasepath)


def parseAction(filename):
    """
    Parses a script file to extract directives

    :param filename: The name of the script file
    :return: A list of directives
    """
    properties = {}
    tree = yamler(filename)
    if 'stoa' in tree:
        for item in tree['stoa']:
            properties[item] = tree['stoa'][item]
    return properties


# Commands
def doDefault(command):
    """
    The default prefix; Returns a list of paths containing the target

    :param command: Name of command script
    :return: A list of paths
    """

    target = targetFolder
    cmdFilename = re.split(" ", scriptFolder+"/"+command)[0]
    props = parseAction(cmdFilename)
    if 'target' in props:
        target = props['target']

    print('Target folder is {}'.format(target))
    return procdb.paths(target)

def doReport(command):
    reptext = procdb.getLastConsole(command)
    return reptext

def doQuery(command):
    """
    Returns a list of paths derived from an SQL query

    :param command: What is put after "WHERE" in the query
    :return: A list of paths
    """
    global queryID
    queryID += 1
    print("Query ID: {} using criteria {}".format(queryID, command))
    return procdb.query(command)


def doRetry(command):
    """
    Returns the paths that resulted in failure in the most
    recent run

    :param command: Name of command script; not used here
    :return: A list of paths
    """
    global databasepath
    program = re.split(" ", command.strip())[0]
    path = []
    done = []
    for fields in procdb.proglist(program):
        if fields['Target'] not in done:
            done.append(fields[2])
            if int(fields['Result']) > 0:
                path.append(fields['Target'])
    if len(path) == 0 and verbose:
        print("No failed targets\n")
    return path


def doRun(command):
    """
    Returns the paths that have been flagged by the user

    :param command: Name of command script; not used here
    :return: A list of paths
    """
    global databasepath
    path = []
    done = []
    for fields in procdb.proglist("FLAG"):
        # This is quite inefficient
        thispath = procdb.getTarget(fields['TID'])
        if thispath not in done:
            done.append(thispath)
            if int(fields['Result']) == 0:
                path.append(thispath)
    if len(path) == 0 and verbose:
        print("No flagged targets\n")
    return path


def doList(command):
    """
    Combines the results of doRun and doRetry into a single list

    :param command: Name of command script; not used here
    :return: A list of paths
    """
    return doRun(command)+doRetry(command)


def doOptlist(command, list={}, indent=""):
    """
    Returns all the program options

    :param command: Not used
    :return: List of options
    """
    path = []
    if list=={}:
        list = config
    for key in list:
        if type(key) is dict:
            path.append(indent+"{}: ".format(key))
            path.extend(doOptlist(command, list=list[key], indent=" "+indent))
        path.append(indent+"{}: {}".format(key, config['stoa-info'][key]))
    return path


def doOptset(command):
    """
    Sets the value of a option

    :param command: string formatted as "<option> <new value>"
    :return: string representation of the new option
    """
    global config
    tokens = re.split(" ", command)
    if len(tokens) < 2:
        print("set <option> <value>")
        return []
    option = tokens[0]
    value = tokens[1]
    if option in config['stoa-info']:
        config['stoa-info'][option] = value
        return ["{}={}".format(option, value)]
    else:
        print("Option {} not found".format(option))
        return []


def doActlist(command):
    """
    Returns a list of all the action scripts available

    :param command: Not used
    :return: List of scripts
    """
    print("Action path is {}".format(scriptFolder))
    if verbose:
        print("Commands:")
        for key in prefixList:
            if key is not "NONE":
                print("    "+key)
        print("Actions:")
    actionlist = []
    scripts = glob.glob(scriptFolder+"*.cwl")
    for script in scripts:
        actionlist.append(re.split("/", script)[-1])
    return actionlist


# Actions alternative to running an external program
def runDisplay(path):
    """
    Dumps contents to console. Needed as a placeholder function for commands
    that execute wholly in their prefix stage

    :param path: Prints this to the console
    :return: None
    """
    print(path)

# Main code


prefixList = {'NONE': doDefault,
              'retry': doRetry,
              'clean': procdb.clean,
              'flag': procdb.doFlag,
              'unflag': procdb.doUnflag,
              'run': doRun,
              'list': doList,
              'flagged': doRun,
              'failed': doRetry,
              'query': doQuery,
              'env': doOptlist,
              'set': doOptset,
              'help': doActlist,
              'report': doReport}

metacmd = {'list': runDisplay,
           'flagged': runDisplay,
           'failed': runDisplay,
           'query': runDisplay,
           'env': runDisplay,
           'set': runDisplay,
           'help': runDisplay,
           'report': runDisplay}

commandPath = os.path.dirname(os.path.abspath(__file__))


def commandgen(command, pathname, noproc=False):
    """
    Main command processing function. Parses file system to find targets
    and then invokes the specific action script. Runs as a generator.

    :param command: The action script or command to be executed
    :param pathname: The root path to start the search from
    :return: Yields text reports of success/failure
    """
    prefix = re.split(" ", command)[0]
    if prefix in prefixList:
        command = command[len(prefix):].strip()
    else:
        prefix = "NONE"

    paths = prefixList[prefix](command)
    if len(paths) is 0:
        return

    # Option for use with web interface
    if noproc:
        for path in paths:
            yield path
        return

    os.chdir(pathname)

    if prefix in metacmd:
        for path in paths:
            metacmd[prefix](path)
        return

    cmdFilename = re.split(" ", scriptFolder+"/"+command)[0]

    if ".cwl" not in cmdFilename:
        cmdFilename = cmdFilename+".cwl"
        command = command.replace(" ", ".cwl ", 1)

    if not os.path.exists(cmdFilename):
        print("No command or action "+command)
        return

    for directive in parseAction(cmdFilename):
        if "root" in directive:
            paths = ["."]

    action = open(cmdFilename, "r")
    checksum = hashlib.md5()
    for line in action:
        checksum.update(line.encode('utf-8'))

    okcount = 0
    for path in paths:
        yield path
        sys.stdout.flush() # Does this do anything now?
        Actions.makeyml(pathname+"/"+path, command)
        #os.chdir(path)
        starttime = time.strftime("%H:%M:%S")
        startdate = time.strftime("%y/%m/%d")
        duration = time.time()
        result = Actions.ExecCWL(command, pathname+"/"+path)
        # result = os.system(cmdFilename+" &> .pipelog.txt")
        duration = time.time() - duration
        print(result)
        pid = procdb.write(command, checksum.hexdigest(), path,
                     startdate, starttime, duration, result)
        #procdb.scanoutput(".pipelog.txt", pid)
        # os.remove(".pipelog.txt")

        #for x in re.findall("\/", path):
        #    os.chdir("..")

        if result > 0:
            yield " \033[1m\033[91mFAILED\033[0m\033[0m\n"
        else:
            okcount += 1
            yield " \033[1m\033[92mOK\033[0m\033[0m\n"

    yield ("Processed \033[1m{}\033[0m folders with "
           "\033[1m{}\033[0m successes and \033[1m{}\033[0m "
           "failures\n").format(len(paths), okcount, len(paths)-okcount)


def procCommand(command, pathname):
    """
    Initialises the database and then invokes commandgen()

    :param command: Passed to commandgen()
    :param pathname: Passed to commandgen()
    :return: None
    """
    procdb.init(databasepath)
    for report in commandgen(command, pathname):
        print(report, end="")


if __name__ == "__main__":
    verbose = True
    clp = ""
    for arg in sys.argv[1:]:
        clp += " "+arg

    while(1):
        if len(clp) > 0:
            print(":> "+clp+"")
            command = clp.strip()
            clp = ""
        else:
            command = raw_input("stoa> ")

        if command == 'quit':
            break

        procCommand(command, ".")

    print("Quiting...")
    writeyaml(config, "stoa.yml")
