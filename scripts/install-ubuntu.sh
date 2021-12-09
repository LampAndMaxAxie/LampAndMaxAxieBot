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
pip3 install wheel
pip3 install -r requirements.txt --upgrade
pip3 install psutil aiosqlite pycryptodome kaleido
