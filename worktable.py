#!/usr/bin/env python

from yml import yamler, writeyaml
from zipfile import ZipFile
import re, os, io, glob
from random import randrange
import tempfile

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

#Tracking codes
TR_PENDING = 0
TR_COMPLETE = 1

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
            self.otherfiles = []
            self.fieldnames = []
            self.fieldtypes = []
            self.tabdata = []
            self.tabptr = 0
            self.track = []
            self.lastfilename = ""
            self.keyref = {}

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
        self.track[key] = TR_PENDING
        self.keyref[data[0]] = key

    def update(self, key, data):
        stdata = self.tabdata[key]
        for n in range(len(self.fieldtypes)):
           if 'O' in self.fieldtypes[n]:
               break
        for datum in data:
            if 'O' in self.fieldtypes[n]:
                stdata[n] = str(datum)
            n+=1
        self.tabdata[key] = stdata   
        self.track[key] = TR_COMPLETE    

    def byref(self, key):
        if key in self.keyref:
            return self.keyref[key]
        else:
            # TODO: Change to exception for release
            print("Failed keyref "+key)
            return 0

    def cat(self):
        filenames = ["workflow.cwl", "template.yml"]
        for task in self.tasks:
            filenames.append(task[0])
        filenames += self.otherfiles
        for fn in filenames:
            yield fn

    def load(self, filename):
        self.tabptr = 0
        self.tabdata = []
        self.tasks = []
        self.otherfiles = []
        self.track = []
        self.keyref = {}
        with ZipFile(filename, "r") as wtab:
            workflowFile = wtab.open("workflow.cwl", "r")
            self.workflow = yamler(io.TextIOWrapper(workflowFile))
            templateFile = wtab.open("template.yml", "r")
            self.template = yamler(io.TextIOWrapper(templateFile))
            for cwlfile in wtab.namelist():
                if ".cwl" in cwlfile and cwlfile != "workflow.cwl":
                    taskfile = wtab.open(cwlfile, "r")
                    self.tasks.append([cwlfile, yamler(io.TextIOWrapper(taskfile))])
                else:
                    if cwlfile not in ["workflow.cwl", "template.yml", "table.txt"]:
                        self.otherfiles.append(cwlfile)
            header = 0
            for line in wtab.open("table.txt","r"):
                line = line.decode("utf8")
                line = line.strip()
                if line[0] == '#':
                    continue
                if header==2:
                    self.tabdata.append(re.split(' ', line))
                    self.keyref[(self.tabdata[-1])[1]] = len(self.tabdata)-1
                    self.track.append(TR_COMPLETE)
                    continue
                if header==0:
                    self.fieldnames = re.split(' ', line)
                    header = 1
                else:
                    self.fieldtypes = re.split(' ', line)
                    header = 2
        self.lastfilename = filename

    def unpack(self, targetpath=""):
        with ZipFile(self.lastfilename, "r") as wtab:
            if targetpath:
                tempdir = targetpath 
            else:
                tempdir = tempfile.mkdtemp(suffix='wtx')
            wtab.extract("workflow.cwl", path=tempdir)
            for task in self.tasks:
                wtab.extract(task[0], path=tempdir)
            for f in self.otherfiles:
                wtab.extract(f, path=tempdir)
        return tempdir+"/workflow.cwl"

    def repack(self, filename):
        os.system("rm -rf {}".format(os.path.split(filename)[0]))

    def save(self, filename):
        with ZipFile(filename, "w") as wtab:
            tempdir = tempfile.mkdtemp(suffix='wtx') 
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
            for contentfile in glob.glob(tempdir+"/*"):
                wtab.write(contentfile, os.path.split(contentfile)[1])
            os.system("rm -rf "+tempdir)

    def addfile(self, filename):
        if ".cwl" in filename:
            self.workflow = yamler(open(filename, "r"))
        if ".yml" in filename:
            self.template = yamler(open(filename, "r"))

    def addtask(self, filename):
        self.task.append([filename, yamler(open(filename, "r"))])

    def addextra(self, filename):
        self.otherfiles.append(filename)
        with ZipFile(self.lastfilename, "a") as wtab:
            wtab.write(filename, os.path.split(filename)[1])

    def setfields(self, flist):
        self.fieldnames = flist
        self.fieldtypes = ["I_int"]*len(flist)

    def settypes(self, tlist):
        self.fieldtypes = tlist

    def genfields(self, path=False):
        inps = self.workflow['inputs']
        outs = self.workflow['outputs']
        self.trow = []
        if inps=='[]':
            inps = []
        if outs=='[]':
            outs = []
        self.fieldnames = ['__bindex__']
        self.fieldtypes = ['K_int']
        if path:
            self.fieldnames.append("Pathname")
            self.fieldtypes.append("I_str")
            self.trow.append("")
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
            if field in self.template:
                self.trow.append(self.template[field])
            else:
                self.trow.append(0)
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
            if field in self.template:
                self.trow.append(self.template[field])
            else:
                self.trow.append(0)

    def clearall(self):
        for i in range(len(self.fieldtypes)):
            if 'O_' in self.fieldtypes[i]:
                for row in self.tabdata:
                    row[i] = "-"
   

    def addrow(self, data, t=True):
        self.tabdata.append([])
        self.track.append(TR_PENDING)
        if not t:
            self[len(self)-1] = data
            return
        newrow = self.trow
        for i in range(len(data)):
            if data[i] != 0:
                newrow[i] = data[i]
        self[len(self)-1] = newrow

    def addtask(self, filename):
        newfile = re.split("/", filename)[-1]
        self.tasks.append([newfile,yamler(open(filename, "r"))])

    def show(self):
        width = str(int(min(15,80/len(self.fieldnames)-1)))
        linef = ("{:<"+width+"."+width+"} ")*len(self.fieldnames)
        print(linef.format(*self.fieldnames))
        print(linef.format(*self.fieldtypes))
        print("-"*(int(width)+1)*len(self.fieldnames))
        linef = ""
        for t in self.fieldtypes:
            if "str" in t:
                linef += "{:<"+width+"."+width+"} "
            else:
                linef += "{:<"+width+"} "
        for row in self:
            print(linef.format(*row))

if __name__=="__main__":
    import sys    
    if len(sys.argv)>1:
        cmd = sys.argv[1]
    else:
        cmd = ""
        print("\nUsage: worktable <command> [<options>...]\n")
        print("    new <cwl file> <yml file> [<target folder>]")
        print("        Create a new worktable with the same name as cwlfile but .wtx extension")
        print("        Adding a target folder populates the table with pathnames that match it\n")
        print("    add <worktable> <filename>")
        print("        Add a file to the worktable. Use this to include any CWL tasks that are needed\n")
        print("    show <worktable>")
        print("        Show the contents of a worktable\n")
    
    if cmd=="new":
        cwlfile = sys.argv[2]
        ymlfile = sys.argv[3]       
        newwt = Worktable()
        newwt.addfile(cwlfile)
        newwt.addfile(ymlfile)
        if len(sys.argv)>4:
            newwt.genfields(path=True)
            for path in getpaths(".",sys.argv[4]):
                newwt.addrow(["example/"+path]+[0]*(len(newwt.fieldnames)-2))
        else:
            newwt.genfields(path=False)   
        newwt.save(re.split(".cwl",cwlfile)[0]+".wtx")

    if cmd=="add":
        wt = Worktable(sys.argv[2])
        if ".cwl" in sys.argv[3]:
            wt.addtask(sys.argv[3])
            wt.save(sys.argv[2])
        else:
            wt.addextra(sys.argv[3])

    if cmd=="show":
        wt = Worktable(sys.argv[2])
        print("Contents:")
        for filename in wt.cat():
          print("  "+filename)
        print("\n")
        wt.show()

    if cmd=="clear":
        wt = Worktable(sys.argv[2])
        wt.clearall()
        wt.save(sys.argv[2])


