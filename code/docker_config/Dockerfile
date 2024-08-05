FROM ubuntu:20.04

COPY . /data
WORKDIR /data

RUN apt update
RUN apt install -y python3 python3-pip
RUN apt install htop

CMD [ "/usr/bin/python3", "DockerChannel.py" ]
