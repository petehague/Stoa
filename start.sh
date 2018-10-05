python3 userstate.py &> userlog.txt & 
python3 action.py $1 &> actionlog.txt &
python3 webhost.py $1 $2

