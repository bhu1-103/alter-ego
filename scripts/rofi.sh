#!/usr/bin/zsh

model=$(ollama list | tail -n +2 | awk -F " " '{print $1,$3$4}' | rofi -dmenu -theme $HOME/.config/rofi/launchers/type-7/style-7 -p "")
echo "chosen model is $model" #debug

prompt=$(rofi -dmenu -theme $HOME/.config/rofi/launchers/type-7/style-7 -p "Jarvis with $model here")
echo "prompt is $prompt" #debug
if [ -n "$prompt" ]; then
	curl http://localhost:11434/api/generate -d '{"model": '"$model"',
		"prompt":"1 line response please: '"$prompt"'",
		"stream":false
		}' > ~/dev/cache/response.json
	jq ".response" ~/dev/cache/response.json
else
	echo "nani sore.."
fi
