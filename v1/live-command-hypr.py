#!/usr/bin/env python3

import sys
import sounddevice as sd
import queue
import json
import subprocess
from vosk import Model, KaldiRecognizer
from pathlib import Path
from rapidfuzz import fuzz

MODEL_PATH = Path("~/dev/vosk/vosk-model-small-en-us-0.15").expanduser()
SAMPLE_RATE = 16000
DEVICE = None
model = Model(str(MODEL_PATH))
recognizer = KaldiRecognizer(model, SAMPLE_RATE)
recognizer.SetWords(True)

q = queue.Queue()

def callback(indata, frames, time, status):
    q.put(bytes(indata))

def speak(message):
    subprocess.run(["espeak-ng", message])

def notify(message, title="Jarvis"):
    subprocess.run(["makoctl", "dismiss"])
    subprocess.run(["notify-send", title, message])

commands = {
    "open firefox": lambda: (speak("Opening firefox"), notify("Opening Firefox"), subprocess.Popen(["firefox"])),
    "play music": lambda: (speak("Playing music"), notify("Playing music"), subprocess.run(["mpc", "play"])),
    "pause music": lambda: (speak("Pausing music"), notify("Pausing music"), subprocess.run(["mpc", "pause"])),
    "stop music": lambda: (speak("Stopping music"), notify("Stopping music"), subprocess.run(["mpc", "stop"])),
    "show calendar": lambda: (speak("Here is your calendar"), notify(subprocess.getoutput("cal"))),
    "what time is it": lambda: (speak("The time is now"), notify(subprocess.getoutput("date"))),
    "open youtube": lambda: (speak("Opening youtube"), subprocess.run(["firefox", "youtube.com"])),
    "explain selected text": lambda: (
        speak("Explaining selected text"),
        notify(
            subprocess.getoutput("wl-copy"),
            "Selected Text"
        )
    ),
    "mute microphone": lambda: (speak("muting microphone"), subprocess.run(["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "1"])),
    "keyboard backlight on": lambda: (speak("Keyboard backlight on"), subprocess.run(["brightnessctl", "-d", "tpacpi::kbd_backlight", "set", "2"])),
    "keyboard backlight off": lambda: (speak("Keyboard backlight off"), subprocess.run(["brightnessctl", "-d", "tpacpi::kbd_backlight", "set", "0"])),
    "shut up": lambda: speak("okay, i'll shut up"),
    "shut the fuck up": lambda: speak("okay, i'll shut the fuck up"),
    "power off": lambda: (speak("shutting down in 10 seconds"), notify("shutting down"), subprocess.run(["shutdown", "now"])),
}

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

print("Say 'Hey' to activate.\n")

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

                if fuzz.partial_ratio("hey", text) > 60:
                    speak("Yes?")
                    notify("I'm listening...")

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
                        print(" No match.")
                        speak("error 4 o 4")
                        notify("Command not found.")

except KeyboardInterrupt:
    print("\n Exiting.")
    sys.exit(0)
