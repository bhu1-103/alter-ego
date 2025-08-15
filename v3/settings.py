from pathlib import Path

AGENT_NAME="bhu2"

MODEL_PATH = Path("~/dev/vosk/vosk-model-small-en-us-0.15").expanduser()
PIPER_MODEL="libritts_r"
PIPER_PATH="./piper/"

wake_words = [
    "hey",
]

wake_responses = [
    "Locked and loaded.",
    "What’s the mission?",
    "Say the word.",
    "Standing by.",
    "Online. Ready for orders.",
    "Let’s do this.",
    "At your command.",
    "You rang?",
    "All ears.",
    "Always watching, always listening.",
    "Time to kick some code.",
    "Who dares summon me?",
    "Talk to me.",
    "Engaged.",
    "Let’s make some noise.",
    "Hit me.",
]

dont_understand_responses = [
    "I don’t speak nonsense... yet.",
    "That doesn't compute.",
    "Try saying that like you mean it.",
    "Come again?",
    "I didn’t catch that badass command.",
    "You might want to rephrase that.",
    "That one flew right past me.",
    "Even I have limits.",
    "Nope. Try something else.",
    "That’s not in my playbook.",
    "Command not found — but I liked the confidence.",
    "Negative. Clarify your intent.",
    "I don’t speak gibberish... usually.",
    "You're talking, but I'm not feeling it.",
]
