import pygame
import os
import requests
import time
import json
import subprocess

# Initialize pygame mixer for audio playback
pygame.mixer.init()

# Function to generate AI haiku using Ollama and speak it using macOS say command
def generate_tts_haiku(word):
    try:
        # Generate AI haiku using Ollama (locally)
        ollama_url = "http://localhost:11434/api/generate"  # Default Ollama API endpoint
        
        # Using llama3.2 model
        ollama_payload = {
            "model": "llama3.2",
            "prompt": f"Write a beautiful haiku about '{word}'. Only respond with the haiku, no explanations.",
            "stream": False
        }
        
        # Send request to Ollama
        ollama_response = requests.post(ollama_url, json=ollama_payload)
        
        if ollama_response.status_code == 200:
            # Extract the haiku from Ollama response
            response_json = ollama_response.json()
            haiku = response_json.get("response", "").strip()
            print(f"\n🌿 Haiku: {haiku} 🌿\n")
            
            # Save the haiku to the log file
            os.makedirs('haiku_sounds', exist_ok=True)  # Ensure directory exists
            with open('haiku_sounds/haiku.txt', 'a', encoding='utf-8') as file:
                file.write(f"{int(time.time())}: {haiku}\n")
            
            # SIMPLEST APPROACH: Just use the macOS 'say' command directly
            # This avoids any issues with audio file creation or playback
            subprocess.run(['say', haiku])
            
        else:
            print(f"⚠️ Error from Ollama API: {ollama_response.status_code}")
            print(ollama_response.text)
            
    except Exception as e:
        print("⚠️ Error generating or playing AI haiku:", e)

# Example usage
if __name__ == "__main__":
    # Test the function
    word = input("Enter a word or phrase for the haiku: ")
    generate_tts_haiku(word)