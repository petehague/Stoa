#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: Workflow

inputs:
  genmax: int

outputs:
  finalresults:
    type: File
    outputSource: touch/results

steps:
  generate:
    run: Generate.cwl
    in: 
      ranmax: genmax
    out: [rannum]

  touch:
    run: Touch.cwl
    in:
      touchfile: generate/rannum
    out: [results]
