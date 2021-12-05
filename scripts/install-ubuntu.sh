#!/bin/bash
homedir=/home/ubuntu

# registry update
echo "Updating source lists"
sudo apt update && sudo apt upgrade -y

# python
echo "Installing python "
sudo apt install -y python3 python3-pip libcairo2-dev libgirepository1.0-dev

# python libs
echo "Installing python libs"
python3 -m pip install --upgrade pip
pip3 install wheel
pip3 install -r requirements.txt --upgrade
python3 -m pip install --upgrade pillow
pip3 install psutil qrcode aiosqlite
pip3 install -U kaleido

# image processing dependencies
echo "Installing image processing stuff"
sudo apt install -y nodejs npm xvfb libgtk2.0-0 libgconf-2-4 libxss1 libnss3-dev libgdk-pixbuf2.0-dev libgtk-3-dev libxss-dev libasound2
npm install