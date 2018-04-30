#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
baseCommand: touch.py

inputs:
  touchcode:
    type: int
    inputBinding:
      position: 1

outputs:
  results:
    type: File
    outputBinding:
      glob: result.txt
