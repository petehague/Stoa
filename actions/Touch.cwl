#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
baseCommand: touch.py

inputs: 
  touchfile:
    type: File
    inputBinding:
      prefix: -f    

outputs:
  results:
    type: File
    outputBinding:
      glob: result.txt
