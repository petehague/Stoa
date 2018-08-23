import re
import collections

def insertnode(ydict, index, value):
    if type(value) is str:
        if len(value)==0:
            return
    if index in ydict:
        if type(ydict[index])==list:
            ydict[index].append(value)
        else:
            ydict[index] = [ydict[index],value]
    else:
            ydict[index] = value

def yamler(text, convert=False):
    subtext = []
    ydict = collections.OrderedDict()
    header = ""
    block = False
    for line in text:
        if not block and (line[0]=="#" or line.strip()==''):
            continue
        if line[0:2] == '  ':
            subtext+=[line[2:]]
            continue
        if block:
            insertnode(ydict, header, subtext)
            subtext = []
            header = ""
            block = False
        if len(subtext)>0:
            #ydict[header] = yamler(subtext)
            insertnode(ydict, header, yamler(subtext))
            header = ""
            subtext = []
        tokens = re.split(":", line.strip()) + ['','']
        header = tokens[0]
        value = tokens[1].strip()
        if value=="|":
            block = True
            subtext += ["|"]
            continue
        if convert:
            if value.isdigit():
               value = int(value)
            else:
                if (value.replace(".","",1)).isdigit():
                    value = float(value)
        insertnode(ydict, header, value)
    if len(subtext)>0:
        if block:
            insertnode(ydict,header,subtext)
        else:
            insertnode(ydict,header,yamler(subtext))
    #ydict.pop('',None)
    return ydict

def makeyaml(ydict, indent=""):
    lastkey = ""
    block = False
    for key in ydict:
        entry = ydict[key]
        if type(entry) is not list:
            entry = [entry]
        for item in entry:
            if type(item) is collections.OrderedDict or type(item) is dict:
                if key!=lastkey:
                    yield indent+"{}:\n".format(key)
                for line in makeyaml(item, indent=indent+"  "):
                    yield line 
                lastkey = ""
            else:
                if block:
                   yield indent+"  {}".format(item)
                else:
                   yield indent+"{}: {}\n".format(key, item)
                if item.strip()=="|":
                   block = True
                lastkey = key
        block = False

def writeyaml(ydict, filename, append=False):
    f = open(filename, "a" if append else "w")
    for line in makeyaml(ydict):
        f.write(line)
    f.close()
