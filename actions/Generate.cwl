#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
baseCommand: generate.py

inputs: []

outputs:
  rannum:
    type: stdout
