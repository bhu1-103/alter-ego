#!/usr/bin/zsh

git clone https://github.com/rhasspy/piper.git
cd piper
cargo build --release

mkdir voices
cd voices
mkdir seamine
cd ..
echo "go to https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_GB/semaine/medium"
echo "download both the files into seamine"
