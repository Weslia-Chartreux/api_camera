FROM python:latest

RUN apt-get update
RUN apt-get -y install libqmi-utils udhcpc net-tools iproute2

WORKDIR /app

COPY ../requirements.txt ./

RUN pip install -r requirements.txt

COPY ./* /app

EXPOSE 6688