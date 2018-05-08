# Stoa

Stoa stands for *Script Tracking for Observational Astronomy* and is a process management system designed for large batch operations on astronomical data. It uses a form of containerisation to enables working with heterogenous data sets, and generates data tracking the performance of each execution of a target script
Stoa runs a script multiple times on the different data, and manages the environment that the script is run in. This means that, for instance, if two different measurement sets need to be reprocessed in different versions of CASA, the script will see the appropriate PATH when it is run.

# How to Use

To run a demo, set up a virtual environment and then run `demo.sh` - if it doesn't work, keep adding the appropriate python modules with pip until it does (a list is coming)
 
A set of Dockerfiles is also included. Make sure you have the repository downloaded, Docker installed and are working in the Stoa folder, and type

`docker build . -t userstate -f Dockerfile-userstate`
`docker build . -t action -f Dockerfile-action`
`docker build . -t stoa -f Dockerfile`
`docker network create stoanet`
`docker create --name userstate --network stoanet userstate`
`docker start userstate`
`docker create --name action --network stoanet action`
`docker start action`
`docker run -p 9000:80 stoa`

and then direct your broswer to localhost:9000 to see the web interface. The default username is 'admin'. This version of the demo will be automated in the near future

The behaviour of Stoa is controlled through the file `stoa.yml` - this describes the targets iterated over, how to connect to external databases, and so on.

# Command Line Interface

Simply typing a script name (.py extension is optional) will attempt to run it

* retry <script> - Will run the script specified on all previously failed targets
* clean - Removes the process table, so no flagged or failed targets will be listed
* flag - Manually flags a target
* unflag - Manually unflags a target
* run <script> - Will run the script on all flagged targets
* list - Will list all flagged and all failed targets
* flagged - Will list all flagged targets
* failed - Will list all failed targets
* env - Will display all current options
* set <option> - Will change the value of the specified option
* help - Lists commands and scripts available

# Script Construction

In order to be used by Stoa, a script needs to have `# +` at some point in the file on a single line.
This character combination tells Stoa a command is meant for it. Other commands include

* `# + target <folder name>` - when crawling throught he file system, this is the name of the folder in which
Stoa executes the script. This can be set within Stoa as well
* `# + root` - disables file system crawling, and simply executes the program once in the root directory of the project

