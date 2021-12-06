FROM python

WORKDIR /
# Install app dependencies
COPY requirements.txt /
RUN sudo apt install -y python3 python3-pip libcairo2-dev libgirepository1.0-dev

RUN python3 -m pip install --upgrade pip
RUN pip3 install wheel
RUN pip3 install -r requirements.txt --upgrade
RUN python3 -m pip install --upgrade pillow
RUN pip3 install psutil qrcode aiosqlite
RUN pip3 install -U kaleido

# Bundle app source
COPY . /

CMD ["python3", "Bot.py"]