#!/bin/bash
homedir=/home/ubuntu

# registry update
echo "Updating source lists"
sudo apt update 

# python
echo "Installing python "
sudo apt install -y python3-pip
sudo apt-get install -y libcairo2-dev libgirepository1.0-dev

# python libs
echo "Installing python libs"
pip3 install -r requirements.txt
pip3 install -r ../requirements.txt
pip3 install psutil

# node stuff
echo "Installing node stuff"
sudo apt install nodejs
sudo apt install npm

# image processing dependencies
echo "Installing image processing stuff"
npm install -g electron@6.1.4 orca
sudo apt install xvfb
sudo apt install libgtk2.0-0
sudo apt install libgconf-2-4
sudo apt install libxss1
sudo apt install libnss3-dev 
sudo apt install libgdk-pixbuf2.0-dev 
sudo apt install libgtk-3-dev 
sudo apt install libxss-dev
sudo apt install libasound2

