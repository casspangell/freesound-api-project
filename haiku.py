import pygame
import os
import requests
import time
import json
import pyttsx3

# Initialize pygame mixer for audio playback
pygame.mixer.init()

# Function to generate AI haiku using Ollama and convert it to speech locally
def generate_tts_haiku(word):
    try:
        # Generate AI haiku using Ollama (locally)
        ollama_url = "http://localhost:11434/api/generate"  # Default Ollama API endpoint
        
        # Using llama3.2 model
        ollama_payload = {
            "model": "llama3.2",  # Specified to use llama3.2
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
            
            # Generate a safe filename
            safe_word = ''.join(c for c in word[:20] if c.isalnum() or c.isspace()).strip().replace(' ', '_')
            if not safe_word:
                safe_word = "dialogue"
            
            tts_file = f"haiku_sounds/{safe_word}_{int(time.time())}.mp3"
            
            # Initialize the TTS engine locally
            engine = pyttsx3.init()
            
            # Optional: Configure TTS properties
            engine.setProperty('rate', 150)    # Speaking rate (words per minute)
            engine.setProperty('volume', 0.8)  # Volume (0.0 to 1.0)
            
            # Get available voices and select one (optional)
            voices = engine.getProperty('voices')
            if voices:
                # Typically index 0 is male, 1 is female - adjust as needed
                engine.setProperty('voice', voices[0].id)
            
            # Save TTS to file
            engine.save_to_file(haiku, tts_file)
            engine.runAndWait()
            
            # Play the haiku audio
            sound = pygame.mixer.Sound(tts_file)
            channel = pygame.mixer.find_channel()
            if channel:
                channel.set_volume(0.4)  # Set volume to 40%
                channel.play(sound)
            else:
                print("⚠️ No available channel for TTS playback")
        else:
            print(f"⚠️ Error from Ollama API: {ollama_response.status_code}")
            print(ollama_response.text)
            
    except Exception as e:
        print("⚠️ Error generating or playing AI haiku:", e)

# Example usage
if __name__ == "__main__":
    # Initialize pygame mixer
    pygame.mixer.init()
    
    # Test the function
    word = input("Enter a word or phrase for the haiku: ")
    generate_tts_haiku(word)
    
    # Wait for audio to finish playing
    while pygame.mixer.get_busy():
        time.sleep(0.1)