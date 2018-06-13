#!/usr/bin/env python

from yml import yamler, writeyaml
from zipfile import ZipFile
import re, os, io, glob
from random import randrange

'''
  The worktable library

  A worktable consists of:
    A CWL workflow
    Any number of CWL tasks associated with the workflow
    A Yaml template for the workflow input
    The main table itself -
      inputs fields
      output fields
    Data - files referenced by input and output fields

  Field types are formatted X_Y:
    X:
      I: an input field
      O: an output field
      K: a key field (must be int or unique)
    Y:
      int: A python int
      unique: A python int which must take a unique value
      float: A python float
      str: A python string
      file: A file name (as a URL)
'''

typemap = {'int': 'int',
           'long': 'int',
           'float': 'float',
           'double': 'float',
           'string': 'str',
           'File': 'file'}

def getpaths(curpath, target):
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

class Worktable():
    def __init__(self, filename = False, template = False):
        if filename:
            self.load(filename)
        else:
            self.workflow = {}
            self.template = {}
            self.tasks = []
            self.fieldnames = []
            self.fieldtypes = []
            self.tabdata = []
            self.tabptr = 0
            self.track = []
            self.lastfilename = ""

    def __iter__(self):
        return self

    def __next__(self):
        if self.tabptr == len(self.tabdata):
            raise StopIteration
        else:
            self.tabptr += 1
            return self[self.tabptr-1]

    def __len__(self):
        return len(self.tabdata)

    def __getitem__(self, key):
        row = self.tabdata[key]
        typerow = []
        for i in range(len(row)):
            item = row[i]
            if 'int' in self.fieldtypes[i]:
                if row[i]=='-':
                    item = 0
                else:
                    item = int(row[i])
            if 'float' in self.fieldtypes[i]:
                if row[i]=='-':
                    item = 0.0
                else:
                    item = float(row[i])
            if item=='-':
                item = ''
            typerow.append(item)
        return typerow

    def __setitem__(self, key, data):
        stdata = ['-']*(len(self.fieldnames)-1)
        n = 0
        if key>0:
            bindex = int(self[key-1][0]) + 1
        else:
            bindex = 0
        for datum in data:
            if 'I' in self.fieldtypes[n+1]:
                stdata[n] = str(datum)
            n+=1
        self.tabdata[key] = [str(bindex)] + stdata

    def load(self, filename):
        self.tabptr = 0
        self.tabdata = []
        self.tasks = []
        self.track = []
        with ZipFile(filename, "r") as wtab:
            workflowFile = wtab.open("workflow.cwl", "r")
            self.workflow = yamler(io.TextIOWrapper(workflowFile))
            templateFile = wtab.open("template.yml", "r")
            self.template = yamler(io.TextIOWrapper(templateFile))
            for cwlfile in wtab.namelist():
                if ".cwl" in cwlfile and cwlfile != "workflow.cwl":
                    taskfile = wtab.open(cwlfile, "r")
                    self.tasks.append([cwlfile, yamler(io.TextIOWrapper(taskfile))])
            header = 0
            for line in wtab.open("table.txt","r"):
                line = line.decode("utf8")
                line = line.strip()
                if line[0] == '#':
                    continue
                if header==2:
                    self.tabdata.append(re.split(' ', line))
                    self.track.append(False)
                    continue
                if header==0:
                    self.fieldnames = re.split(' ', line)
                    header = 1
                else:
                    self.fieldtypes = re.split(' ', line)
                    header = 2
        self.lastfilename = filename

    def unpack(self):
        with ZipFile(self.lastfilename, "r") as wtab:
            tempdir = "_tmp_{}".format(randrange(10000,99999)) 
            os.mkdir(tempdir)
            wtab.extract("workflow.cwl", path=tempdir)
            for task in self.tasks:
                wtab.extract(task[0], path=tempdir)
        return tempdir+"/workflow.cwl"

    def repack(self, filename):
        os.system("rm -rf {}".format(os.path.split(filename)[0]))

    def save(self, filename):
        with ZipFile(filename, "w") as wtab:
            tempdir = "_tmp_{}".format(randrange(10000,99999)) 
            os.mkdir(tempdir)
            writeyaml(self.workflow, tempdir+"/workflow.cwl")
            for task in self.tasks:
                writeyaml(task[1], tempdir+"/"+task[0])
            writeyaml(self.template, tempdir+"/template.yml")
            tabfile = open(tempdir+"/table.txt", "w")
            tabfile.write(' '.join(self.fieldnames)+"\n")
            tabfile. write(' '.join(self.fieldtypes)+"\n")
            for row in self.tabdata:
                tabfile.write(' '.join(row)+"\n")
            tabfile.close()
            for tempfile in glob.glob(tempdir+"/*"):
                wtab.write(tempfile, os.path.split(tempfile)[1])
            os.system("rm -rf "+tempdir)

    def addfile(self, filename):
        if ".cwl" in filename:
            self.workflow = yamler(open(filename, "r"))
        if ".yml" in filename:
            self.template = yamler(open(filename, "r"))

    def addtask(self, filename):
        self.task.append([filename, yamler(open(filename, "r"))])

    def setfields(self, flist):
        self.fieldnames = flist
        self.fieldtypes = ["I_int"]*len(flist)

    def settypes(self, tlist):
        self.fieldtypes = tlist

    def genfields(self, path=False):
        inps = self.workflow['inputs']
        outs = self.workflow['outputs']
        if inps=='[]':
            inps = []
        if outs=='[]':
            outs = []
        self.fieldnames = ['__bindex__']
        self.fieldtypes = ['K_int']
        if path:
            self.fieldnames.append("Pathname")
            self.fieldtypes.append("I_str")
        for field in inps:
            typestr = "I_"
            if type(inps[field])==str:
               rawtype = inps[field]
            else:
               rawtype = inps[field]['type']
            if rawtype in typemap:
                typestr += typemap[rawtype]
            else:
                typestr += "int"
            self.fieldnames.append(field)
            self.fieldtypes.append(typestr)
        for field in outs:
            typestr = "O_"
            if type(outs[field])==str:
               rawtype = outs[field]
            else:
               rawtype = outs[field]['type']
            if rawtype in typemap:
                typestr += typemap[rawtype]
            else:
                typestr += "int"
            self.fieldnames.append(field)
            self.fieldtypes.append(typestr)


    def addrow(self, data):
        self.tabdata.append([])
        self[len(self)-1] = data

    def addtask(self, filename):
        newfile = re.split("/", filename)[-1]
        self.tasks.append([newfile,yamler(open(filename, "r"))])

    def show(self):
        linef = "{:<12} "*len(self.fieldnames)
        print(linef.format(*self.fieldnames))
        print(linef.format(*self.fieldtypes))
        print("-"*(13*len(self.fieldnames)))
        for row in self:
            print(linef.format(*row))

if __name__=="__main__":
    import sys
    cwlfile = sys.argv[1]
    ymlfile = sys.argv[2]       
    newwt = Worktable()
    newwt.addfile(cwlfile)
    newwt.addfile(ymlfile)
    if len(sys.argv)>3:
        newwt.genfields(path=True)
        for path in getpaths(".",sys.argv[3]):
            newwt.addrow(["example/"+path]+[0]*(len(newwt.fieldnames)-2))
    else:
        newwt.genfields(path=False)   
    newwt.save(re.split(".cwl",cwlfile)[0]+".wtx")

