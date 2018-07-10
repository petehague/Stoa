#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
baseCommand: ["find", "-name"]

inputs:
  foldername:
    type: string
    inputBinding:
      position: 1

outputs:
  pathname:
    type:
      type: array
      items: stdout

