#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
baseCommand: /home/prh44/Stoa/actions/touch.py

inputs: 
  touchfile:
    type: File
    inputBinding:
      position: 1 

outputs:
  results:
    type: File
    outputBinding:
      glob: result.txt
