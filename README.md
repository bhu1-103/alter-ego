# bhu3, my alter ego

## Dependencies
`sudo pacman -S curl dunst`

`curl -fsSL https://ollama.com/install.sh | sh`

`ollama pull llama3.2:1b`. works on literally any computer

`vosk` - download any model from [here](https://alphacephei.com/vosk/models). [40 mb model](https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip) is good enough for everyday scenarios

`piper voices` can be downloaded from [here](https://huggingface.co/rhasspy/piper-voices/tree/main). you need both the `.onnx` and `.onnx.json` files

`pip install -r requirements.txt`

## improvements

- [x] clipboard explainer
- [x] logging
- [ ] screenshot explainer
- [ ] contextual understanding
- [x] execute commands
- [ ] vision (llava maybe)
- [x] automate everything (done partially, but the framework is ready)
- [x] voice in (~maybe~ vosk)
- [x] voice out (~maybe kokoro or zonos~) through piper-tts
- [x] custom voice in ~espeak~ piper-tts

## user manual

### settings.py **YOU MUST RESTART THE RUNTIME FOR THE CHANGES TO AFFECT**

- set your vosk [model path](https://github.com/bhu1-103/alter-ego?tab=readme-ov-file#dependencies) using `MODEL_PATH`

- set your [piper model path](https://github.com/bhu1-103/alter-ego?tab=readme-ov-file#dependencies) using `PIPER_MODEL`

- i use the development version of piper, so i have set a `PIPER_PATH` variable

- you can set the `AGENT_NAME` variable to anything, though it's not being used in the current version

- `wake words` can be changed to anything else, i used `hey` for now

- similarly `wake_responses` and `dont_understand_responses` can be changed, they're taken in random order

### live-command.py

- edit the commands here from `commands`. here is the basic syntax. `"command string": lambda: (speak("Voice feedback"), notify("Notification text"), subprocess.Popen(["program", "arg1", "arg2"]))`

1. `command string` -> the thing you wanna say after the wake word
2. `Voice feedback` -> what you want your assistant to reply for this specific command
3. `Notification text` -> currently works in linux only. self explanatory
4. `program` -> let's say you want to open youtube in firefox, all you have to do is `firefox https://youtube.com`. that translates to `subprocess.run(["firefox", "youtube.com"])`
