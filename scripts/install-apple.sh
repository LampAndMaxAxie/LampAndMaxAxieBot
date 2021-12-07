#!/bin/bash

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
# registry update
echo "Updating source lists"
brew update && brew upgrade

# python
echo "Installing python "
brew install python3

# python libs
echo "Installing python libs"
pip3 install wheel
pip3 install -r requirements.txt --upgrade
pip3 install psutil
