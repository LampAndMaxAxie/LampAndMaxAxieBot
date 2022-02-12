FROM ubuntu

RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get -y install tzdata
RUN apt-get install -y python3 python3-pip libcairo2-dev
#libgirepository1.0-dev
RUN apt install -y nodejs npm xvfb libgtk2.0-0 libgconf-2-4 libxss1 libnss3-dev libgdk-pixbuf2.0-dev libgtk-3-dev libxss-dev libasound2

RUN npm install electron@6.1.4 orca

RUN python3 -m pip install --upgrade pip
RUN pip3 install wheel

COPY ./requirements.txt /requirements.txt
RUN pip3 install -r requirements.txt

WORKDIR /
COPY . /

CMD ["python3", "Bot.py"]

