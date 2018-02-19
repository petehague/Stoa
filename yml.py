import re

def yamler(text):
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
        ydict[tokens[0]] = tokens[1].strip()
    ydict.pop('',None)
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
