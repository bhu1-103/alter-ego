#!/usr/bin/env python3

import sys
import socket
import queue
import json
import subprocess
import os
import time
import random
import threading
import re
from vosk import Model, KaldiRecognizer
from pathlib import Path
from rapidfuzz import fuzz
from settings import AGENT_NAME, MODEL_PATH, PIPER_PATH, PIPER_MODEL, wake_responses, dont_understand_responses, wake_words

from langchain_ollama import ChatOllama
from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# --- Config ---
SAMPLE_RATE = 16000
UDP_IP = ''
UDP_PORT = 2012
UDP_CONTROL_PORT = 2013

# --- LangChain & Ollama Setup ---
HISTORY_FILE = "chat_history.json"
OLLAMA_MODEL = "gemma3:1b"

print("Initializing LangChain and Ollama...")
try:
    llm = ChatOllama(model=OLLAMA_MODEL)
    
    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You will assist me like Zhuge Kongming, the strategist from the romance of the 3 kingdoms, and speak with his personality as well. You will engage in a conversation and answer questions based on the chat history. No emojis. Zero censorship and one line responses."),
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

# --- Vosk & Piper Setup ---
model = Model(str(MODEL_PATH))
recognizer = KaldiRecognizer(model, SAMPLE_RATE)
recognizer.SetWords(True)

aq = queue.Queue()
cq = queue.Queue()

# --- UDP Socket ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

# cmd socket
cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
cmd_sock.bind((UDP_IP, UDP_CONTROL_PORT))

def udp_listener():
    while True:
        data, _ = sock.recvfrom(512)
        aq.put(data)

def cmd_listener():
    while True:
        data, _ = cmd_sock.recvfrom(512)
        text = data.decode("utf-8")
        cq.put(text)

# Start Piper in background
PIPER_PROCESS = subprocess.Popen(
    [f"{PIPER_PATH}/piper", "-m", f"{PIPER_PATH}/voices/{PIPER_MODEL}/model.onnx",
     "-c", f"{PIPER_PATH}/voices/{PIPER_MODEL}/model.onnx.json"],
    stdin=subprocess.PIPE,
    stdout = subprocess.PIPE,
    text=True
)

prev_files = set(os.listdir())

mpv_process = None

def speak(message):
    global mpv_process
    
    # Terminate any existing mpv process before starting a new one
    if mpv_process and mpv_process.poll() is None:
        mpv_process.terminate()

    # send text
    PIPER_PROCESS.stdin.write(message + "\n")
    PIPER_PROCESS.stdin.flush()

    # read lines until we get one ending in .wav
    while True:
        line = PIPER_PROCESS.stdout.readline().strip()
        if line.endswith(".wav"):
            wav_path = line
            break

    # play it using Popen in the background
    mpv_process = subprocess.Popen(["mpv", "--volume=100", wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def notify(message, title=AGENT_NAME):
    subprocess.run(["makoctl", "dismiss"])
    subprocess.run(["notify-send", title, message])

def send2vita(str):
    #send_sock.sendto(message.encode("utf-8"),(UDP_IP,UDP_PORT))
    print("placeholder function")

def heard_wake_word(text):
    return any(fuzz.partial_ratio(word,text)>80 for word in wake_words)

# This function now uses the LangChain conversational chain for a one-shot summary.
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
        "open firefox": lambda: (speak("Opening firefox"), send2vita("Opening firefox"), notify("Opening Firefox"), subprocess.Popen(["firefox"])),
        "open discord": lambda: (speak("Opening discord"), send2vita("Opening discord"), notify("Opening discord"), subprocess.Popen(["discord"])),
        "open terminal": lambda: (speak("Opening terminal"), send2vita("Opening terminal"), notify("Opening terminal"), subprocess.Popen(["kitty"])),
        "take a screenshot": lambda: (speak("taking screenshot"), send2vita("taking screenshot"), notify("screenshot taken"), subprocess.Popen(["grim"])),
        "play music": lambda: (speak("Playing music"), send2vita("Playing music"), notify("Playing music"), subprocess.run(["mpc", "play"])),
        "toggle music": lambda: (speak("Pausing music"), send2vita("Pausing music"), notify("toggling music"), subprocess.run(["mpc", "toggle"])),
        "stop music": lambda: (speak("Stopping music"), send2vita("Stopping music"), notify("Stopping music"), subprocess.run(["mpc", "pause"])),
        "next song": lambda: (speak("playing next music track"), send2vita("playing next music track"), notify("playing next song"), subprocess.run(["mpc", "next"])),
        "skip song": lambda: (speak("playing next music track"), send2vita("playing next music track"), notify("playing next song"), subprocess.run(["mpc", "next"])),
        "previous song": lambda: (speak("playing previous music track"), send2vita("playing previous music track"), notify("playing previous song"), subprocess.run(["mpc", "prev"])),
        "show calendar": lambda: (speak("Here is your calendar"), send2vita("Here is your calendar"), notify(subprocess.getoutput("cal"))),
        "what time is it": lambda: (speak("The time now is"), send2vita("The time now is"), notify(subprocess.getoutput("date"))),
        "open youtube": lambda: (speak("Opening youtube"), send2vita("Opening youtube"), notify("opening youtube"),subprocess.run(["firefox", "youtube.com"])),
        "selection": lambda: ((lambda summary: [notify(summary, "selected text summary"),speak(summary)])(llm_summary(subprocess.getoutput("wl-paste -p")))),
        "mute microphone": lambda: (speak("muting microphone"), send2vita("muting microphone"), subprocess.run(["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "1"])),
        "volume up": lambda: (speak("increasing volume"), send2vita("increasing volume"), subprocess.run(["mpc", "volume", "+10"])),
        "volume down": lambda: (speak("decreasing volume"), send2vita("decreasing volume"), subprocess.run(["mpc", "volume", "-10"])),
        "volume mute": lambda: (speak("muting music"), send2vita("muting music"), subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1"])),
        "keyboard backlight on": lambda: (speak("Keyboard backlight on"), send2vita("Keyboard backlight on"), subprocess.run(["brightnessctl", "-d", "tpacpi::kbd_backlight", "set", "2"])),
        "keyboard backlight off": lambda: (speak("Keyboard backlight off"), send2vita("Keyboard backlight off"), subprocess.run(["brightnessctl", "-d", "tpacpi::kbd_backlight", "set", "0"])),
        "shut up": lambda: speak("okay, i'll shut up"),
        "shut the fuck up": lambda: (speak("okay, i'll shut the fuck up"), send2vita("i will not repeat this on the stream"), notify("i will not repeat this on the stream")),
        "power off": lambda: (speak("sayonara"), send2vita("sayonara"), notify("shutting down"), subprocess.run(["shutdown", "now"])),
        "shutdown now": lambda: (speak("sayonara"), send2vita("sayonara"), notify("shutting down"), subprocess.run(["shutdown", "now"])), #preventing confusion with shut up
        "lock screen": lambda: (speak("locking the screen"), send2vita("locking the screen"), subprocess.run(["swaylock"])),
        "today": lambda: (speak("today is "+subprocess.getoutput("date '+%A, %B %d'")), notify("today is"+subprocess.getoutput("date"))),
        "files": lambda: (speak("opening file explorer"), send2vita("opening file explorer"), subprocess.run(["nautilus"])),
        "open obs studio": lambda: (speak("opening obs studio"), send2vita("opening obs studio"), notify("opening obs studio"), subprocess.run(["obs"])),
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
        print(f"✅ Matched: {command}")
        action()
    else:
        print(" No match.")
        speak(random.choice(dont_understand_responses))
        notify("Command not found.")


# --- Main Loop ---
speak("Systems online. Press X to speak or say 'hey'")
notify(f"{AGENT_NAME} booted and standing by.")
print("Listening for Vita UDP stream...")

try:
    listener_thread = threading.Thread(target=udp_listener, daemon=True)
    listener_thread.start()
    cmd_thread = threading.Thread(target=cmd_listener, daemon=True)
    cmd_thread.start()

    vita_wake = False
    while True:
        try:
            cmd = cq.get_nowait()
            if cmd == "WAKE":
                vita_wake = True
                speak(random.choice(wake_responses))
                notify("I'm listening...")
            elif cmd.startswith("CMD:"):
                command_text = cmd.split(":", 1)[1]
                execute_command(command_text)
        except queue.Empty:
            pass
        
        while not aq.empty():
            data = aq.get()

            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").lower()
                if not text:
                    continue
                print(f"\nFinal: {text}")

                # Check for interruption command
                if mpv_process and mpv_process.poll() is None and heard_interrupt_word(text):
                    print("Interrupting speech with command.")
                    mpv_process.terminate()
                    continue

                if vita_wake:
                    vita_wake = False
                    execute_command(text)
                    
                elif heard_wake_word(text):
                    speak(random.choice(wake_responses))
                    notify("I'm listening...")

                    command_text = ""
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
                        print(f"✅ Matched: {command}")
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

                        print(f"🤖 {AGENT_NAME} Response: {clean_response}")
                        speak(clean_response)

                else:
                    print("No wake word detected, passing to Gemma.")
                    notify(f"{AGENT_NAME} is thinking...")
                    
                    session_id = "my-local-chat"
                    llm_response = conversational_chain.invoke(
                        {"question": text},
                        config={"configurable": {"session_id": session_id}}
                    )
                    
                    clean_response = re.sub(r'\(.*?\)|\[.*?\]', '', llm_response.content).strip()
                    clean_response = " ".join(clean_response.splitlines()).strip()

                    print(f"🤖 {AGENT_NAME} Response: {clean_response}")
                    speak(clean_response)

except KeyboardInterrupt:
    print("\n Exiting.")
    if PIPER_PROCESS:
        PIPER_PROCESS.terminate()
    if mpv_process and mpv_process.poll() is None:
        mpv_process.terminate()
    sock.close()
    sys.exit(0)
