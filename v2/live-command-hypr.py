#!/usr/bin/env python3

import sys
import sounddevice as sd
import queue
import json
import subprocess
import os
import time
import random
from vosk import Model, KaldiRecognizer
from pathlib import Path
from rapidfuzz import fuzz
from settings import AGENT_NAME, MODEL_PATH, PIPER_PATH, PIPER_MODEL, wake_responses, dont_understand_responses, wake_words

SAMPLE_RATE = 16000
DEVICE = None
model = Model(str(MODEL_PATH))
recognizer = KaldiRecognizer(model, SAMPLE_RATE)
recognizer.SetWords(True)

q = queue.Queue()

def callback(indata, frames, time, status):
    q.put(bytes(indata))

# Start Piper in background
PIPER_PROCESS = subprocess.Popen(
    [f"{PIPER_PATH}/piper", "-m", f"{PIPER_PATH}/voices/{PIPER_MODEL}/model.onnx",
     "-c", f"{PIPER_PATH}/voices/{PIPER_MODEL}/model.onnx.json"],
    stdin=subprocess.PIPE,
    stdout = subprocess.PIPE,
    text=True
)

prev_files = set(os.listdir())

def speak(message):
    # send text
    PIPER_PROCESS.stdin.write(message + "\n")
    PIPER_PROCESS.stdin.flush()

    # read lines until we get one ending in .wav
    while True:
        line = PIPER_PROCESS.stdout.readline().strip()
        if line.endswith(".wav"):
            wav_path = line
            break

    # play it
    subprocess.run(["mpv", wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def notify(message, title=AGENT_NAME):
    subprocess.run(["makoctl", "dismiss"])
    subprocess.run(["notify-send", title, message])

commands = {
    "open firefox": lambda: (speak("Opening firefox"), notify("Opening Firefox"), subprocess.Popen(["firefox"])),
    "open terminal": lambda: (speak("Opening firefox"), notify("Opening Firefox"), subprocess.Popen(["kitty"])),
    "take a screenshot": lambda: (speak("Opening firefox"), notify("Opening Firefox"), subprocess.Popen(["grim"])),
    "play music": lambda: (speak("Playing music"), notify("Playing music"), subprocess.run(["mpc", "play"])),
    "toggle music": lambda: (speak("Pausing music"), notify("Pausing music"), subprocess.run(["mpc", "toggle"])),
    "stop music": lambda: (speak("Stopping music"), notify("Stopping music"), subprocess.run(["mpc", "stop"])),
    "next song": lambda: (speak("playing next music track"), notify("playing next song"), subprocess.run(["mpc", "next"])),
    "skip song": lambda: (speak("playing next music track"), notify("playing next song"), subprocess.run(["mpc", "next"])),
    "previous song": lambda: (speak("playing previous music track"), notify("playing previous song"), subprocess.run(["mpc", "prev"])),
    "show calendar": lambda: (speak("Here is your calendar"), notify(subprocess.getoutput("cal"))),
    "what time is it": lambda: (speak("The time now is"), notify(subprocess.getoutput("date"))),
    "open youtube": lambda: (speak("Opening youtube"), notify("opening youtube"),subprocess.run(["firefox", "youtube.com"])),
    "clipboard": lambda: ((lambda summary: [notify(summary, "Clipboard summary"),speak(summary)])(llm_summary(subprocess.getoutput("wl-paste")))),
    "mute microphone": lambda: (speak("muting microphone"), subprocess.run(["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "1"])),
    "volume up": lambda: (speak("increasing volume"), subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"])),
    "volume down": lambda: (speak("increasing volume"), subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-10%"])),
    "volume mute": lambda: (speak("increasing volume"), subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1"])),
    "volume unmute": lambda: (speak("increasing volume"), subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"])),
    "keyboard backlight on": lambda: (speak("Keyboard backlight on"), subprocess.run(["brightnessctl", "-d", "tpacpi::kbd_backlight", "set", "2"])),
    "keyboard backlight off": lambda: (speak("Keyboard backlight off"), subprocess.run(["brightnessctl", "-d", "tpacpi::kbd_backlight", "set", "0"])),
    "shut up": lambda: speak("okay, i'll shut up"),
    "shut the fuck up": lambda: speak("okay, i'll shut the fuck up"),
    "power off": lambda: (speak("sayonara"), notify("shutting down"), subprocess.run(["shutdown", "now"])),
    "lock screen": lambda: (speak("locking the screen"), subprocess.run(["swaylock"])),
    "today": lambda: (speak("today is "+subprocess.getoutput("date '+%A, %B %d'")), notify("today is"+subprocess.getoutput("date"))),
    "files": lambda: (speak("opening file explorer"), subprocess.run(["nautilus"])),
    "open obs studio": lambda: (speak("openign obs studio"), notify("opening obs studio"), subprocess.run(["obs"])),
}

def heard_wake_word(text):
    return any(fuzz.partial_ratio(word,text)>80 for word in wake_words)

def llm_summary(text):
    import requests
    import json
    response = requests.post(
        "http://localhost:11434/api/generate",
        data=json.dumps({
            "model": "llama3.2:1b",
            "prompt": f"Explain this in one sentence:\n\n{text}",
            "stream": False
        })
    )
    return response.json().get("response", "No response.")

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
speak("Systems online. Awaiting your orders.")
notify("Sentinel booted and standing by.")
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

                if heard_wake_word(text):
                    speak(random.choice(wake_responses))
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
                        speak(random.choice(dont_understand_responses))
                        notify("Command not found.")

except KeyboardInterrupt:
    print("\n Exiting.")
    if PIPER_PROCESS:
        PIPER_PROCESS.terminate()
    sys.exit(0)
