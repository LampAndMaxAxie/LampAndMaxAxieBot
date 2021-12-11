#!/bin/bash 
homedir=/home/ubuntu

# registry update
echo "Updating source lists"
sudo apt update && sudo apt upgrade -y

# python
echo "Installing python "
sudo apt install -y python3 python3-pip tmux

# python libs
echo "Installing python libs"
python3 -m pip install --upgrade pip
pip3 install -U wheel
pip3 install -U -r requirements.txt
pip3 install -U -r ../requirements.txt
pip3 install -U psutil aiosqlite pycryptodome kaleido

if grep -q Microsoft /proc/version; then
    echo "Detected Windows WSL user"
    sudo apt install -y nodejs npm xvfb libgtk2.0-0 libgconf-2-4 libxss1 libnss3-dev libgdk-pixbuf2.0-dev libgtk-3-dev libxss-dev libasound2
    npm install -g electron@6.1.4 orca 
fi
