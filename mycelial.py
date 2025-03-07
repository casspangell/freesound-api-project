import requests
import pygame
import time
import random
import config
import os

# Initialize pygame mixer for audio playback
pygame.init()
pygame.mixer.init()

# Freesound API key
API_KEY = config.API_KEY  
BASE_URL = "https://freesound.org/apiv2"
SOUNDS_DIR = "sounds"
os.makedirs(SOUNDS_DIR, exist_ok=True)  # Ensure sounds directory exists

# Default looping background music
DEFAULT_MUSIC = os.path.join(SOUNDS_DIR, "soul-song.mp3")

# Function to search for sounds
def search_sound(query):
    url = f"{BASE_URL}/search/text/?query={query}&token={API_KEY}&fields=id,name,description,duration"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if "results" in data and len(data["results"]) > 0:
            return random.choice(data["results"])["id"]  # Pick a random sound
    return None

# Function to download and play a sound (plays on a new available channel)
def play_sound(sound_id):
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

            # Load sound and find an available channel
            sound = pygame.mixer.Sound(sound_file)
            channel = pygame.mixer.find_channel()  # Find a free channel
            if channel:
                channel.play(sound)  # Play sound on available channel
            else:
                print("⚠️ No available sound channels. Increasing mixer capacity.")

        else:
            print("The selected sound is too long or unavailable.")
    else:
        print(f"Failed to fetch sound details. Error: {response.status_code}")

# Function to play the background music in a loop
def play_background_music():
    if os.path.exists(DEFAULT_MUSIC):
        background_music = pygame.mixer.Sound(DEFAULT_MUSIC)
        pygame.mixer.find_channel().play(background_music, loops=-1)  # Loop indefinitely
        print("\n🎶 The soul-song begins... 🌌\n")
    else:
        print("⚠️ Default music file 'soul-song.mp3' not found in /sounds/.")

# Main game loop
def text_input_game():
    print("\n🌿 Welcome to the Mycelial Memory Game! 🌿")
    print("Type 'begin' to start and hear the soul-song...\n")
    
    # Wait for the user to type "begin"
    while True:
        user_input = input("Enter 'begin' to start: ").strip().lower()
        if user_input == "begin":
            play_background_music()
            break

    print("\nType a word related to knowledge, plants, or sound to experience its echo in the mycelial network.")
    
    while True:
        user_input = input("\nEnter a word (or type 'exit' to quit): ").strip().lower()
        if user_input == "exit":
            print("Exiting game... 🌱")
            pygame.mixer.stop()  # Stop all sounds before exiting
            break

        print(f"\nThe mycelium absorbs the concept of '{user_input}'... 🍄")

        sound_id = search_sound(user_input)
        
        if sound_id:
            print("🎶 The network whispers back with sound...")
            play_sound(sound_id)  # Plays sound **without stopping background music**
        else:
            print("🔕 The mycelium remains silent... It does not understand this word.")

# Run the game
if __name__ == "__main__":
    text_input_game()
