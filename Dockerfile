FROM python:3.5.5-slim

WORKDIR /stoacont

ADD . /stoacont

RUN pip install numpy
RUN pip install astropy
RUN pip install cwltool
RUN pip install tornado

EXPOSE 9000

ENV NAME Stoa container

CMD ["python", "webhost.py", "../"]
