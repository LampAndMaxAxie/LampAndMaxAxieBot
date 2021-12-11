#!/bin/bash 
homedir=/home/ubuntu

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# registry update
echo -e "${GREEN}Updating source lists${NC}"
sudo apt update && sudo apt upgrade -y

# python
echo -e "${GREEN}Installing python${NC}"
sudo apt install -y python3 python3-pip tmux

# python libs
echo -e "${GREEN}Installing python libs${NC}"
python3 -m pip install --upgrade pip
pip3 install -U wheel

if [ -f "requirements.txt" ]; then
    pip3 install -U -r requirements.txt
elif [ -f "../requirements.txt" ]; then
    pip3 install -U -r ../requirements.txt
else
    echo -e "${RED}***FATAL ERROR*** requirements.txt file not found${NC}"
fi
pip3 install -U psutil aiosqlite pycryptodome kaleido

if grep -q Microsoft /proc/version; then
    echo -e "${GREEN}Detected Windows WSL user, installing alternate image tools${NC}"
    sudo apt install -y nodejs npm xvfb libgtk2.0-0 libgconf-2-4 libxss1 libnss3-dev libgdk-pixbuf2.0-dev libgtk-3-dev libxss-dev libasound2
    npm install -g electron@6.1.4 orca 
fi

echo -e "${GREEN}Install complete. Please check that no major errors occurred in the output above.${NC}"

