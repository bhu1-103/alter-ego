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

### settings.py

- set your vosk [model path](https://github.com/bhu1-103/alter-ego?tab=readme-ov-file#dependencies) using `MODEL_PATH`

- set your [piper model path](https://github.com/bhu1-103/alter-ego?tab=readme-ov-file#dependencies) using `PIPER_MODEL`

- i use the development version of piper, so i have set a `PIPER_PATH` variable
