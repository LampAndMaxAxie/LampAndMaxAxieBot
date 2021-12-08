#!/bin/bash

tmux new-session -d -s discord_bot
tmux send-keys -t discord_bot 'python3 Bot.py' C-m
tmux a