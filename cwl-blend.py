#!/usr/bin/env python

'''

Blends CWL files into Python, and reverse

format cwl-blend.py <file> <file>
  place files in any order. One Python and one CWL file
  -x extract cwl file (instead of inserting one)
  -f force operation

If no cwl file is provided, a basic one is created
It simply names the python file

'''

import sys

def doBlend(pysource, cwlsource):
    insert = 0
    for line in pysource:
        if line[0:2]=="#!":
            yield line
            continue
        if insert<1:
            yield "'''CWL\n"
            for cwlline in cwlsource:
                yield cwlline
            yield "'''\n"
            insert += 1
        yield line


def doUnblend(pysource, outfile):
    output = open(outfile, "w")
    cwlFlag = False
    for line in pysource:
        if cwlFlag:
            if "'''" in line:
                cwlFlag = False
                continue
            output.write(line)
        if "'''CWL" in line:
            cwlFlag = True
            continue
        if not cwlFlag:
            yield line
    output.close()

extract = False
pymode = "r"
cwlmode = "r"
force = False
pythonfilename = ""
cwlfilename = ""

for argument in sys.argv:
    if argument[0]=='-':
        if 'x' in argument:
            extract = True
            pymode = "r"
            cwlmode = "r"
        if 'f' in argument:
            force = True
    if '.py' in argument:
        pythonfilename = argument
    if '.cwl' in argument:
        cwlfilename = argument


if len(pythonfilename)==0:
    pyfile = ["#!/usr/env/bin python\n",
              "\n",
              "print('Hello World!)\n"]
    pythonfilename = "helloworld.py"
else:
    pyfile = open(pythonfilename, pymode)


if len(cwlfilename)==0:
    cwlfile = ["#!/usr/env/bin cwl-runner\n",
               "\n",
               "cwlVersion: 1.0\n",
               "class: CommandLineTool\n",
               "baseCommand: {}\n".format(pythonfilename)]
    cwlfilename = "helloworld.cwl"
else:
    cwlfile = open(cwlfilename, cwlmode)

if extract:
    for output in doUnblend(pyfile, cwlfilename):
        print(output,end="")
else:
    for output in doBlend(pyfile, cwlfile):
        print(output,end="")