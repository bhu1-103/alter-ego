#!/usr/bin/zsh

logs_dir="/home/bhu2/dev/logs/alter-ego"

touch $logs_dir/prompts.txt
touch $logs_dir/responses.txt

model=$(ollama list | tail -n +2 | awk -F " " '{print $1}' | rofi -dmenu -theme $HOME/.config/rofi/launchers/type-7/style-3 -p "CHOOSE MODEL")

prompt=$(tac $logs_dir/prompts.txt | awk -F "Prompt: " '{print $2}' | rofi -dmenu -theme $HOME/.config/rofi/launchers/type-7/style-3 -p "Jarvis with $model here" -p "ENTER PROMPT")

if [ -n "$prompt" ]; then
	echo "$(date +%H:%M) | Model: $(printf "%-20s" "$model") | Prompt: $prompt" >> $logs_dir/prompts.txt
	curl http://localhost:11434/api/generate -d '{"model": "'$model'",
		"prompt":"1 line response please: '"$prompt"'",
		"stream":false
		}' > ~/dev/cache/response.json
	jq ".response" ~/dev/cache/response.json >> $logs_dir/responses.txt
	notify-send "alter-ego ($model) says" "$(tail -n 1 $logs_dir/responses.txt)"
else
	echo "nani sore.."
fi
