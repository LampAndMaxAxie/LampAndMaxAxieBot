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
python -m pip install --upgrade pip
pip3 install -U wheel
pip3 install -U -r requirements.txt
pip3 install -U -r ../requirements.txt
pip3 install -U psutil aiosqlite pycryptodome kaleido
