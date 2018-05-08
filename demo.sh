python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. ./userstate.proto
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. ./action.proto
python userstate.py &
python action.py &
./webhost.py example 9000
