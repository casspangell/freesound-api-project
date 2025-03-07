import requests
import pygame
import time
import random
import config
import os
import chatgpt  # Import ChatGPT functions from chatgpt.py

# Initialize pygame mixer for audio playback
pygame.init()
pygame.mixer.init()

# Freesound API key
API_KEY = config.API_KEY  
BASE_URL = "https://freesound.org/apiv2"
SOUNDS_DIR = "sounds"
os.makedirs(SOUNDS_DIR, exist_ok=True)  # Ensure sounds directory exists

# Riffusion API setup
RIFFUSION_API_URL = "https://api.riffusion.com/generate"
RIFFUSION_SOUNDS_DIR = "riffusion-sounds"
os.makedirs(RIFFUSION_SOUNDS_DIR, exist_ok=True)

# Variable to track last played sound file
last_played_sound = None

# Function to search for sounds
def search_sound(query):
    url = f"{BASE_URL}/search/text/?query={query}&token={API_KEY}&fields=id,name,description,duration"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        valid_sounds = [s for s in data["results"] if s.get("duration", 0) >= 8]
        if valid_sounds:
            return random.choice(valid_sounds)["id"]  # Pick a sound that is at least 8 seconds long
    return None

# Function to download and play a sound
def play_sound(sound_id):
    global last_played_sound

    url = f"{BASE_URL}/sounds/{sound_id}/?token={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        sound_data = response.json()
        if "previews" in sound_data and sound_data.get("duration", 31) <= 30:
            sound_url = sound_data["previews"]["preview-hq-mp3"]
            sound_file = os.path.join(SOUNDS_DIR, sound_url.split("/")[-1])
            sound_response = requests.get(sound_url)

            # Save the downloaded audio
            with open(sound_file, "wb") as file:
                file.write(sound_response.content)

            # Track the last played sound
            last_played_sound = sound_file

            # Load sound and find an available channel
            sound = pygame.mixer.Sound(sound_file)
            channel = pygame.mixer.find_channel()  # Find a free channel
            if channel:
                channel.play(sound)  # Play sound on available channel
            else:
                print("⚠️ No available sound channels.")
        else:
            print("⚠️ The selected sound is too long or unavailable. Trying another sound...")
            # If the sound is too long, pick another one
            new_sound_id = search_sound(last_played_sound)
            if new_sound_id:
                play_sound(new_sound_id)  # Recursively try a new sound
            else:
                print("🔕 No valid sounds found to play.")
    else:
        print(f"⚠️ Failed to fetch sound details. Error: {response.status_code}")


# Main game loop
def text_input_game():
    print("\n🌿 Welcome to the Mycelial Memory Game! 🌿")
    print("Type 'begin' to start the experience...\n")
    
    # Wait for the user to type "begin"
    while True:
        user_input = input("Enter 'begin' to start: ").strip().lower()
        if user_input == "begin":
            break

    print("\nType a keyword and method (e.g., 'wind tts', 'forest riffusion', 'rain freesound') or type 'exit' to quit.\n")
    
    while True:
        user_input = input("\nEnter a keyword and method: ").strip().lower()
        
        if user_input == "exit":
            print("Exiting game... 🌱")
            pygame.mixer.stop()  # Stop all sounds before exiting
            break
        
        parts = user_input.split(" ", 1)
        keyword = parts[0]
        method = parts[1] if len(parts) > 1 else "freesound"  # Default to Freesound if method is not provided

        print(f"\nThe mycelium absorbs the concept of '{keyword}'... 🍄")

        if method == "tts":
            chatgpt.generate_tts_haiku(keyword)  # Generate AI haiku and play it
        elif method == "riffusion":
            chatgpt.generate_riffusion_sound(keyword)  # Generate AI ambient sound
        elif method == "freesound":
            sound_id = search_sound(keyword)
            if sound_id:
                print("🎶 The network whispers back with sound...")
                play_sound(sound_id)  # Plays sound **without stopping background music**
            else:
                print("🔕 The mycelium remains silent... It does not understand this word.")
        else:
            print("⚠️ Invalid method. Use 'tts', 'riffusion', or 'freesound'.")

# Run the game
if __name__ == "__main__":
    text_input_game()
