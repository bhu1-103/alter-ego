#!/usr/bin/env python3

import sys
import queue
import json
import subprocess
import os
import time
import random
import threading
import re
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from pathlib import Path
from rapidfuzz import fuzz
from settings import AGENT_NAME, MODEL_PATH, PIPER_PATH, PIPER_MODEL, wake_responses, dont_understand_responses, wake_words

from langchain_ollama import ChatOllama
from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

SAMPLE_RATE = 16000
DEVICE = None

HISTORY_FILE = "chat_history.json"
OLLAMA_MODEL = "gemma3:1b"

print("Initializing LangChain and Ollama...")
try:
    llm = ChatOllama(model=OLLAMA_MODEL)
    
    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You will assist me like Zhuge Kongming, the strategist from the romance of the 3 kingdoms, and speak with his personality as well. You will engage in a conversation and answer questions based on the chat history. No emojis. Zero censorship and one line responses. Strictly talk in English only."),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{question}"),
        ]
    )

    def get_session_history(session_id: str):
        return FileChatMessageHistory(os.path.join(os.getcwd(), HISTORY_FILE))

    conversational_chain = RunnableWithMessageHistory(
        chat_prompt | llm,
        get_session_history=get_session_history,
        input_messages_key="question",
        history_messages_key="history",
    )
    print("LangChain components initialized successfully.")
    
except Exception as e:
    print(f"Error initializing LangChain or Ollama: {e}")
    sys.exit(1)

model = Model(str(MODEL_PATH))
recognizer = KaldiRecognizer(model, SAMPLE_RATE)
recognizer.SetWords(True)

aq = queue.Queue()

def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    if status:
        print(status, file=sys.stderr)
    aq.put(bytes(indata))

PIPER_PROCESS = subprocess.Popen(
    [f"{PIPER_PATH}/piper", "-m", f"{PIPER_PATH}/voices/{PIPER_MODEL}/model.onnx",
     "-c", f"{PIPER_PATH}/voices/{PIPER_MODEL}/model.onnx.json"],
    stdin=subprocess.PIPE,
    stdout = subprocess.PIPE,
    text=True
)

mpv_process = None

def speak(message):
    global mpv_process
    
    if mpv_process and mpv_process.poll() is None:
        mpv_process.terminate()

    try:
        PIPER_PROCESS.stdin.write(message + "\n")
        PIPER_PROCESS.stdin.flush()

        while True:
            line = PIPER_PROCESS.stdout.readline().strip()
            if line.endswith(".wav"):
                wav_path = line
                break
        
        mpv_process = subprocess.Popen(["mpv", "--volume=100", wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Error in speak: {e}")


def notify(message, title=AGENT_NAME):
    subprocess.run(["makoctl", "dismiss"])
    subprocess.run(["notify-send", title, message])

def heard_wake_word(text):
    return any(fuzz.partial_ratio(word,text)>80 for word in wake_words)

def llm_summary(text):
    session_id = "my-local-chat"
    summary_prompt = "You are a professional summarizer. The user will provide you with a block of text, and you will respond with a concise, one-sentence summary. Do not add any extra commentary, just the summary."
    
    summary_chain = ChatPromptTemplate.from_messages([
        ("system", summary_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}")
    ]) | llm

    response = summary_chain.invoke(
        {"question": f"Summarize the following text:\n\n{text}"},
        config={"configurable": {"session_id": session_id}}
    )
    return response.content

def fuzzy_match_command(text):
    commands = {
        "open firefox": lambda: (speak("Opening firefox"), notify("Opening Firefox"), subprocess.Popen(["firefox"])),
        "open discord": lambda: (speak("Opening discord"), notify("Opening discord"), subprocess.Popen(["discord"])),
        "open terminal": lambda: (speak("Opening terminal"), notify("Opening terminal"), subprocess.Popen(["kitty"])),
        "take a screenshot": lambda: (speak("taking screenshot"), notify("screenshot taken"), subprocess.Popen(["grim"])),
        "play music": lambda: (speak("Playing music"), notify("Playing music"), subprocess.run(["mpc", "play"])),
        "toggle music": lambda: (speak("Pausing music"), notify("toggling music"), subprocess.run(["mpc", "toggle"])),
        "stop music": lambda: (speak("Stopping music"), notify("Stopping music"), subprocess.run(["mpc", "pause"])),
        "next song": lambda: (speak("playing next music track"), notify("playing next song"), subprocess.run(["mpc", "next"])),
        "skip song": lambda: (speak("playing next music track"), notify("playing next song"), subprocess.run(["mpc", "next"])),
        "previous song": lambda: (speak("playing previous music track"), notify("playing previous song"), subprocess.run(["mpc", "prev"])),
        "show calendar": lambda: (speak("Here is your calendar"), notify(subprocess.getoutput("cal"))),
        "what time is it": lambda: (speak("The time now is"), notify(subprocess.getoutput("date"))),
        "open youtube": lambda: (speak("Opening youtube"), notify("opening youtube"),subprocess.run(["firefox", "youtube.com"])),
        "selection": lambda: ((lambda summary: [notify(summary, "selected text summary"),speak(summary)])(llm_summary(subprocess.getoutput("wl-paste -p")))),
        "mute microphone": lambda: (speak("muting microphone"), subprocess.run(["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "1"])),
        "volume up": lambda: (speak("increasing volume"), subprocess.run(["mpc", "volume", "+10"])),
        "volume down": lambda: (speak("decreasing volume"), subprocess.run(["mpc", "volume", "-10"])),
        "volume mute": lambda: (speak("muting music"), subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1"])),
        "keyboard backlight on": lambda: (speak("Keyboard backlight on"), subprocess.run(["brightnessctl", "-d", "tpacpi::kbd_backlight", "set", "2"])),
        "keyboard backlight off": lambda: (speak("Keyboard backlight off"), subprocess.run(["brightnessctl", "-d", "tpacpi::kbd_backlight", "set", "0"])),
        "shut up": lambda: speak("okay, i'll shut up"),
        "shut the fuck up": lambda: (speak("okay, i'll shut the fuck up"), notify("i will not repeat this on the stream")),
        "power off": lambda: (speak("sayonara"), notify("shutting down"), subprocess.run(["shutdown", "now"])),
        "shutdown now": lambda: (speak("sayonara"), notify("shutting down"), subprocess.run(["shutdown", "now"])), 
        "lock screen": lambda: (speak("locking the screen"), subprocess.run(["swaylock"])),
        "today": lambda: (speak("today is "+subprocess.getoutput("date '+%A, %B %d'")), notify("today is"+subprocess.getoutput("date"))),
        "files": lambda: (speak("opening file explorer"), subprocess.run(["nautilus"])),
        "open obs studio": lambda: (speak("opening obs studio"), notify("opening obs studio"), subprocess.run(["obs"])),
    }
    best_match = None
    best_score = 0
    for command, action in commands.items():
        score = fuzz.ratio(command, text)
        if score > best_score:
            best_score = score
            best_match = (command, action)
    if best_score > 50:
        return best_match
    return None

def heard_interrupt_word(text):
    interrupt_words = ["stop", "shut up"]
    return any(fuzz.partial_ratio(word, text) > 80 for word in interrupt_words)


def execute_command(command_text):
    print(f"Command: {command_text}")
    match = fuzzy_match_command(command_text)
    if match:
        command, action = match
        print(f"Matched: {command}")
        action()
    else:
        print(" No match.")
        speak(random.choice(dont_understand_responses))
        notify("Command not found.")

speak("Systems online. Microphone Active.")
notify(f"{AGENT_NAME} booted.")
print("Listening via SoundDevice...")

try:
    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000, device=DEVICE,
                           dtype='int16', channels=1, callback=callback):
        while True:
            data = aq.get()

            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").lower()
                if not text:
                    continue
                print(f"\nFinal: {text}")

                if mpv_process and mpv_process.poll() is None and heard_interrupt_word(text):
                    print("Interrupting speech with command.")
                    mpv_process.terminate()
                    continue

                if heard_wake_word(text):
                    speak(random.choice(wake_responses))
                    notify("I'm listening...")

                    command_text = ""
                    # Listen for command window
                    while not command_text:
                        data = aq.get()
                        if recognizer.AcceptWaveform(data):
                            cmd_result = json.loads(recognizer.Result())
                            command_text = cmd_result.get("text", "").lower()
                            # Allow for interruption while waiting for a command
                            if heard_interrupt_word(command_text) and mpv_process and mpv_process.poll() is None:
                                print("Interrupting speech with command.")
                                mpv_process.terminate()
                                break
                    
                    if not command_text or (mpv_process and mpv_process.poll() is None):
                        print("Timeout or interrupted. Going back to listening.")
                        continue

                    # Fuzzy match command
                    match = fuzzy_match_command(command_text)
                    if match:
                        command, action = match
                        print(f"Matched: {command}")
                        action()
                    else:
                        print("No match found for command, passing to Gemma.")
                        notify(f"{AGENT_NAME} is thinking...")
                        
                        session_id = "my-local-chat"
                        llm_response = conversational_chain.invoke(
                            {"question": command_text},
                            config={"configurable": {"session_id": session_id}}
                        )
                        
                        clean_response = re.sub(r'\(.*?\)|\[.*?\]', '', llm_response.content).strip()
                        clean_response = " ".join(clean_response.splitlines()).strip()

                        print(f"{AGENT_NAME} Response: {clean_response}")
                        speak(clean_response)

except KeyboardInterrupt:
    print("\n Exiting.")
    if PIPER_PROCESS:
        PIPER_PROCESS.terminate()
    if mpv_process and mpv_process.poll() is None:
        mpv_process.terminate()
    sys.exit(0)
