python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. ./userstate.proto
python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. ./action.proto
python3 userstate.py &
python3 action.py &
python3 webhost.py example 9000
