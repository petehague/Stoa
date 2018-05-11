import re
import ast

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
    ydict = {}
    header = ""
    for line in text:
        if line[0:2] == '  ':
            subtext+=[line[2:]]
            continue
        if len(subtext)>0:
            ydict[header] = yamler(subtext)
            header = ""
            subtext = []
        tokens = re.split(":", line.strip()) + ['','']
        header = tokens[0]
        value = tokens[1].strip()
        if convert:
            if value.isdigit():
               value = int(value)
            else:
                if (value.replace(".","",1)).isdigit():
                    value = float(value)
        insertnode(ydict, header, value)
    if len(subtext)>0:
        insertnode(ydict,header,yamler(subtext))
    #ydict.pop('',None)
    return ydict
           
def writeyaml(ydict, filename):
    f = open(filename, "w")
    for key in ydict:
        if type(ydict[key]) is dict:
            f.write("{}:\n".format(key))
            for inkey in ydict[key]:
                f.write("  {}: {}\n".format(inkey, ydict[key][inkey]))
        else:
            f.write("{}: {}\n".format(key, ydict[key]))
    f.close()
