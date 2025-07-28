#!/usr/bin/env python3

import sys
import sounddevice as sd
import queue
import json
import subprocess
from vosk import Model, KaldiRecognizer
from pathlib import Path
from rapidfuzz import fuzz #saved my life

MODEL_PATH = Path("~/dev/vosk/vosk-model-small-en-us-0.15").expanduser()
SAMPLE_RATE = 16000 #vosk's standard sampling rate
DEVICE = None #default mic -> laptop inbuilt mic

model = Model(str(MODEL_PATH))
recognizer = KaldiRecognizer(model, SAMPLE_RATE) #lets me run it without a hotkey and monitor at all times
recognizer.SetWords(True)

q = queue.Queue()

def callback(indata, frames, time, status):
    q.put(bytes(indata))

commands = {
    "open firefox": lambda: (speak("Opening firefox"), subprocess.Popen(["firefox"])),
    "play music": lambda: (speak("Playing music"), subprocess.run(["mpc", "play"])),
    "pause music": lambda: (speak("Pausing music"), subprocess.run(["mpc", "pause"])),
    "stop music": lambda: (speak("Stopping music"), subprocess.run(["mpc", "stop"])),
    "show calendar": lambda: (speak("Here is your calendar"), subprocess.run(["zenity", "--calendar"])),
    "what time is it": lambda: (speak("The time is now"), subprocess.run(["zenity", "--info", "--text", subprocess.getoutput("date")])),
    "open youtube": lambda: (speak("Opening youtube"), subprocess.run(["firefox", "youtube.com"])),
    "explain selected text": lambda: (speak("Explaining selected text"), subprocess.run(["zenity", "--info", "--text=" + subprocess.getoutput("xsel --primary | jq -Rs . | sed 's/^\"\\(.*\\)\"$/\\1/'")])),
    "mute microphone": lambda: (speak("muting microphone"), subprocess.run(["pactl","set-source-mute","@DEFAULT_SOURCE@","1"])),
    "unmute microphone": lambda: (speak("muting microphone"), subprocess.run(["pactl","set-source-mute","@DEFAULT_SOURCE@","0"])),
    "keyboard backlight on": lambda: (speak("turning on keyboard backlight"), subprocess.run(["brightnessctl","-d","tpacpi::kbd_backlight","set","2"])),
    "keyboard backlight off": lambda: (speak("turning off keyboard backlight"), subprocess.run(["brightnessctl","-d","tpacpi::kbd_backlight","set","0"])),
    "shut up": lambda: (speak("okay, i'll shut up")),
    "shut the fuck up": lambda: (speak("okay, i'll shut the fuck up")),
}

def speak(message):
    subprocess.run(["espeak-ng", message])

def fuzzy_match_command(text):
    best_match = None
    best_score = 0
    for command, action in commands.items():
        score = fuzz.ratio(command, text)
        if score > best_score:
            best_score = score
            best_match = (command, action)
    if best_score > 80:
        return best_match
    return None

print("Say 'Jarvis' to activate.\n")
try:
    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000, device=DEVICE,
                           dtype='int16', channels=1, callback=callback):
        while True:
            data = q.get()
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").lower()
                if not text:
                    continue
                print(f"\nFinal: {text}")

                if fuzz.partial_ratio("jarvis", text) > 60:
                    subprocess.Popen(["zenity", "--info", "--text=I'm listening...", "--timeout=2"])
                    speak("Yes?")
                    
                    command_text = ""
                    while not command_text:
                        data = q.get()
                        if recognizer.AcceptWaveform(data):
                            cmd_result = json.loads(recognizer.Result())
                            command_text = cmd_result.get("text", "").lower()
                    
                    print(f"🎯 Command: {command_text}")
                    match = fuzzy_match_command(command_text)
                    if match:
                        command, action = match
                        print(f"✅ Matched: {command}")
                        action()
                    else:
                        print("❌ No match.")
                        speak("error 4o4")
except KeyboardInterrupt:
    print("\n🛑 Exiting.")
    sys.exit(0)
