#!/bin/bash
homedir=/home/ubuntu
echo "Installing the requirements ... "

echo "Updating source lists"
sudo apt update 

echo "Installing python "
sudo apt install -y python3-pip
sudo apt-get install -y libcairo2-dev libgirepository1.0-dev

echo "Installing application requirements"
pip3 install -r requirements.txt

# things for rendering images, only needed for summary/top commands
npm install -g electron@6.1.4 orca
pip3 install psutil
sudo apt-get install xvfb
sudo apt-get install libgtk-3-0
sudo apt-get install libgconf-2-4
sudo apt-get install libxss1

