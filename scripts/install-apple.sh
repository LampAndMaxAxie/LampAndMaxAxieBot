#!/bin/bash

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
# registry update
echo "Updating source lists"
brew update && brew upgrade

# python
echo "Installing python "
brew install python3 tmux

# python libs
echo "Installing python libs"
python3 -m pip install --upgrade pip
pip3 install -U wheel
pip3 install -U -r requirements.txt
pip3 install -U psutil aiosqlite pycryptodome kaleidoit
