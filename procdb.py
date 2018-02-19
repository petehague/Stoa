import sqlite3 as sql
import glob
import re
import os

# Fields: PID Command Checksum Target Date Time Duration Result

dbcon = ""


def init(path):
    global dbcon
    dbcon = sql.connect(path+'.proctab.db')
    dbcon.row_factory = sql.Row
    c = dbcon.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS tblProcess(\
              Command VARCHAR(20),\
              Checksum VARCHAR(100),\
              TID INT,\
              startDate VARCHAR(8),\
              startTime VARCHAR(8),\
              Duration REAL,\
              Result INT)")

    c.execute("CREATE TABLE IF NOT EXISTS tblTargets(\
              targetName VARCHAR(100),\
              pathName TEXT,\
              shortName TEXT)")

    c.execute("CREATE TABLE IF NOT EXISTS tblResults(\
              PID INT,\
              TID INT,\
              Field VARCHAR(100),\
              Type VARCHAR(1),\
              IntVal INT,\
              FloatVal REAL,\
              TextVal TEXT)")

    c.execute("CREATE TABLE IF NOT EXISTS tblPos(\
               PID INT,\
               TID INT,\
               RA REAL,\
               DEC REAL)")

    c.execute("CREATE TABLE IF NOT EXISTS tblConsole(\
              PID INT,\
              Line VARCHAR(80))")

    dbcon.commit()


def getTID(target):
    c = dbcon.cursor()
    c.execute("SELECT rowid FROM tblTargets\
               WHERE pathName='{}'".format(target))
    for row in c:
        return row[0]


def getTarget(TID):
    c = dbcon.cursor()
    c.execute("SELECT pathName FROM tblTargets\
               WHERE rowid='{}'".format(TID))
    for row in c:
        return row[0]


def clean():
    global dbcon

    c = dbcon.cursor()
    c.execute("DELETE FROM tblProcess")
    dbcon.commit()


def proglist(programName):
    global dbcon

    c = dbcon.cursor()
    c.execute('SELECT * FROM tblProcess \
               WHERE Command="{}" ORDER BY ROWID DESC'.format(programName))
    for row in c:
        yield(row)


def doFlag(command):
    global dbcon

    c = dbcon.cursor()
    c.execute("INSERT INTO tblProcess(Command, TID, Result) \
               VALUES ('FLAG', {}, 0)".format(getTID(command)))
    dbcon.commit()
    return []

def doUnflag(command):
    global dbcon

    c = dbcon.cursor()
    c.execute("INSERT INTO tblProcess(Command, TID, Result) \
               VALUES ('FLAG', {}, 1)".format(getTID(command)))
    dbcon.commit()
    return []


def isFlagged(command):
    global dbcon

    c = dbcon.cursor()
    c.execute('SELECT * FROM tblProcess WHERE \
              TID="{}" AND Command="FLAG" \
              ORDER BY ROWID DESC'.format(getTID(command)))
    dbcon.commit()
    for row in c:
        return row['Result']


def write(command, checksum, path, startdate, starttime, duration, result):
    global dbcon

    c = dbcon.cursor()
    c.execute('INSERT INTO tblProcess(Command, Checksum, TID,\
               startDate, startTime, Duration, Result) VALUES\
               (?,?,?,?,?,?,?)', [command, checksum, getTID(path), startdate,
                                  starttime, duration, result])
    dbcon.commit()
    c.execute('SELECT ROWID FROM tblProcess ORDER BY ROWID DESC')  # Wasteful?
    for row in c:
        return row[0]


def getpaths(curpath, target):
    result = re.findall(target+".xml", curpath)
    if len(result) > 0:
        return
    result = re.findall("/"+target+"$", curpath)
    if len(result) == 0:
        sub = glob.glob(curpath+"/*")
        paths = []
        for folder in sub:
            if not os.path.islink(folder):
                p = getpaths(folder, target)
                if p:
                    paths += p
        return paths
    else:
        return [curpath]


def trimPath(pathname, target):
    folders = re.split("/", pathname)
    pathstring = ""
    trimmedpath = ""
    for node in folders:
        filelist = glob.glob(target+pathstring+"/*")
        pathstring += "/"+node
        if len(filelist) > 1:
            trimmedpath += "/"+node
        else:
            trimmedpath += "/..."
    return trimmedpath


def paths(target):
    global dbcon

    c = dbcon.cursor()
    c.execute("SELECT * FROM tblTargets")
    row = c.fetchone()
    if row is None:
        row = ["NA"]
    if row[0] not in target:
        c.execute("DELETE FROM tblTargets")
        paths = getpaths(".", target)
        for path in paths:
            shortname = trimPath(path, target)
            c.execute("INSERT INTO tblTargets VALUES (?,?,?)",
                      [target, path, shortname])
        dbcon.commit()
    else:
        c.execute("SELECT * FROM tblTargets")
        paths = []
        for row in c:
            paths.append(row['pathName'])

    return paths


# TODO: Remove the serious SQL injection vunerablility from this function
def query(command):
    global dbcon

    c = dbcon.cursor()
    c.execute("SELECT * FROM tblProcess WHERE "+command)
    # This is like licking a public toilet seat
    result = []
    for row in c:
        target = getTarget(row['TID'])
        if target:
            result.append(target)
    return result


def scanoutput(filename, pid):
    global dbcon

    c = dbcon.cursor()
    confile = open(filename, "r")
    for line in confile:
        while len(line)>80:
            c.execute("INSERT INTO tblConsole VALUES (?, ?)", [pid, line[0:80]])
            line = line[80:]
        c.execute("INSERT INTO tblConsole VALUES (?, ?)", [pid, line])
    dbcon.commit()

def getLastPID(pathname):
    global dbcon

    tid = getTID(pathname)
    c = dbcon.cursor()
    c.execute('SELECT * FROM tblProcess WHERE TID="{}" ORDER BY ROWID DESC'.format(tid))
    for row in c:
        return row['ROWID']
    return None


def getLastConsole(pathname):
    global dbcon
    pid = getLastPID(pathname)

    c = dbcon.cursor()
    c.execute('SELECT Line FROM tblConsole WHERE PID="{}"'.format(pid))
    outputtext = ""
    for row in c:
        outputtext += row['Line']+"\n"
    return outputtext


def addResults(pid, tid, rdict, prefix=""):
    global dbcon
    c = dbcon.cursor()
    for key in rdict:
        intval = int(0)
        realval = float(0)
        textval = ""
        if type(rdict['key']) is int:
            intval = rdict['key']
            rtype = "I"
        else:
            if type(rdict['key']) is float:
                realval = rdict['key']
                rtype = "F"
            else:
                if type(rdict['key']) is dict:
                    rtype = "R"
                else:
                    rtype = "T"
                    textval = rdict['key']
        c.execute("INSERT INTO tblResults VALUES (?,?,?,?,?,?,?)", 
                   [pid, tid, key, rtype, intval, realval, textval])
        if rtype=="R":
            addResults(pid,tid,rdict["key"], prefix=key+".")
    dbcon.commit()


def extractVal(row):
    if row['Type'] == 'I':
        return row['IntVal']
    if row['Type'] == 'F':
        return row['FloatVal']
    return row['TextVal']


def getResults(pid, tid):
    global dbcon
    c = dbcon.cursor()
    c.execute('SELECT * from tblResults WHERE TID="{}" AND PID="{}" ORDER BY ROWID'.format(tid,pid))
    dkey = []
    subdict = {}
    result = {}
    for row in c:
        if row['Type']=='R':
           dkey.append(row['Field'])
        else:
           if "." in row['Field']:
               subdict[re.split(".", row['Field'])[1]] = extractVal(row)
           else:
               if len(dkey)>0:
                   result[dkey[-1]] = subdict
                   subdict = {}
                   if len(dkey)>1:
                       dkey = dkey[:-1]
                   else:
                       dkey = []
    return result
