#!/usr/bin/zsh
ollama list | tail -n +2 | awk -F " " '{print $1,$3$4}' | rofi -dmenu -theme $HOME/.config/rofi/launchers/type-2/style-1
