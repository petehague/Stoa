# Stoa

STOA stands for *Script Tracking for Observational Astronomy* and is a workflow management system primarily designed for large scale production of interferometry data. 

This software is still in development; users are encouraged to contact prh44 (AT) cam.ac.uk for assistance, and to follow updates carefully.

# How to Install

STOA requires Python 3 and some Python libraries, all available through `pip` - we recommend that you use a virtual environment when trying this out. When you have one set up, install `numpy`, `astropy`,`cwltool`,`gpcio-tools` and `tornado` and you should be good to go

In order to prepare STOA to run, type

`./ready.sh`

this only need be done once per STOA install. Then type

`./start.sh example 9000`

to run the demo. Go to your browser and visit `localhost:9000` to try it out

# How to Use

Log in as `guest` (no password is required) and try to create a worktable to implement the 'find' command. Once this table is present, go into it and add a new row with 'product' as its input, and then run that row.

More tutorial material will be added soon.

