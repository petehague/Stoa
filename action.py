#!/usr/bin/env python

import cwltool.factory
import yml

def cwlinvoke(taskfile, params):
    taskfac = cwltool.factory.Factory()
    t = taskfac.make(taskfile)
    result = t(**params)
    return result    


def manager(taskfile, paramfile, outfile):
    result = cwlinvoke(taskfile,yml.yamler(open(paramfile,"r")))
    writeyaml(result, outfile)


if __name__ == "__main__":
    r = cwlinvoke("tool.cwl",yml.yamler(open("job.yml")))
    print(r)
