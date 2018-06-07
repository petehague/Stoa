#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
baseCommand: generate.py

inputs: 
  ranmax:
    type: int

outputs:
  rannum:
    type: stdout
