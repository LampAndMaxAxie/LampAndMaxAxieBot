FROM python

WORKDIR /
# Install app dependencies
COPY requirements.txt /
RUN pip3 install -r requirements.txt

# Bundle app source
COPY . /

CMD ["python3", "Bot.py"]