#!/usr/bin/zsh

curl http://localhost:11434/api/generate -d '{"model": "llama3.2:1b",
	"prompt":"Tell me about this in 1 line: '"$(wl-paste)"'",
	"stream":false
	}' > ~/dev/bhu3/response.json
jq ".response" ~/dev/bhu3/response.json > ~/dev/bhu3/response.txt

espeak-ng "$(cat ~/dev/bhu3/response.txt)"
# will replace with a better tts soon, bear with me
