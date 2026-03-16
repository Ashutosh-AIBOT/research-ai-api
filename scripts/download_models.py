#!/usr/bin/env python3
"""
Pre-download all models at build time
"""
import os
import sys
import time

def download_whisper():
    print("📥 Downloading Whisper model...")
    import whisper
    whisper.load_model("tiny", download_root="/app/models/whisper")
    print("✅ Whisper downloaded")

def download_translator():
    print("📥 Downloading Translator model...")
    from transformers import MarianMTModel, MarianTokenizer
    MarianTokenizer.from_pretrained(
        "Helsinki-NLP/opus-mt-hi-en",
        cache_dir="/app/models/translator"
    )
    MarianMTModel.from_pretrained(
        "Helsinki-NLP/opus-mt-hi-en",
        cache_dir="/app/models/translator"
    )
    print("✅ Translator downloaded")

def pull_ollama_models():
    print("📥 Pulling Ollama models...")
    import subprocess
    import time
    
    # Start Ollama
    subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)  # Wait for Ollama to start
    
    models = ["phi3:mini", "deepseek-coder:1.3b", "moondream"]
    for model in models:
        print(f"  Pulling {model}...")
        subprocess.run(["ollama", "pull", model], check=True)
    
    print("✅ All Ollama models downloaded")

if __name__ == "__main__":
    start = time.time()
    print("=" * 50)
    print("🚀 PRE-DOWNLOADING ALL MODELS")
    print("=" * 50)
    
    download_whisper()
    download_translator()
    pull_ollama_models()
    
    elapsed = time.time() - start
    print(f"\n✅ All models downloaded in {elapsed:.2f} seconds")
