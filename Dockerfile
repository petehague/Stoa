#FROM alpine:3.5

#RUN apk add --no-cache python3
#RUN apk add --no-cache py3-pip

FROM python:3.6.5-stretch
#FROM python:2.7.14

WORKDIR /stoacont

ADD . ./

#RUN chmod 777 example/task1/product
#RUN chmod 777 example/task2/product

RUN pip install numpy
RUN pip install astropy
RUN pip install astroquery
RUN pip install cwltool
RUN pip install tornado

EXPOSE 80

ENV NAME Stoa container

CMD ["python","webhost.py","example","80"]
