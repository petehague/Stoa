FROM python:3.6.5-stretch

WORKDIR /stoacont

ADD . ./

RUN pip install --upgrade pip
RUN pip install numpy
RUN pip install astropy
RUN pip install astroquery
RUN pip install cwltool
RUN pip install tornado
RUN pip install grpcio-tools

RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. ./action.proto
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. ./userstate.proto

EXPOSE 80

ENV NAME Stoa container

CMD ["python","webhost.py","example","80"]
