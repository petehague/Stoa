Design
======

This is the main design document, which is primarily aimed at developers

Overview
--------

.. image:: view1.png

The web interface initiates a WebSocket connection when started in order to drive the main UI. The web server is run as a separate process from the action server, which executes workflows. This means that continuous connectivity is not required to keep workflows running. Once the interface has highlighted which rows of which worktables need to be run, no further input via the web is required, and the user can close their browser and come back later.

Data Model
----------

Worktable are stored on the disk as zipped files, which always contain the following:

* A Common Workflow Language (CWL) file detailing the workflow
* A Yaml file providing a row template
* The table data

In addition, each Worktable may store any number of files, typically the individual steps of the workflow (as CWL files) and the program(s) that are to be invoked by the workflow. Data must only be stored inside the table itself, not in any auxilary files inside the worktable package.


