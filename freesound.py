from openai import OpenAI
import config
import pygame
import os
import random
import requests
import time
import logging
from ashari import Ashari

# Initialize pygame mixer for audio playback
pygame.init()
pygame.mixer.init()

# Freesound API key
API_KEY = config.API_KEY  
BASE_URL = "https://freesound.org/apiv2"
SOUNDS_DIR = "sounds"
os.makedirs(SOUNDS_DIR, exist_ok=True)  # Ensure sounds directory exists

# Variable to track last played sound file
last_played_sound = None

# Function to search for sounds
def search_sound(query):
    url = f"{BASE_URL}/search/text/?query={query}&token={API_KEY}&fields=id,name,description,duration"
    response = requests.get(url)
    logging.info(f"Searching for sound with query: {query}")
    if response.status_code == 200:
        data = response.json()
        valid_sounds = [s for s in data["results"] if s.get("duration", 0) >= 8]
        if valid_sounds:
            logging.info(f"Found valid sounds: {len(valid_sounds)}")
            return random.choice(valid_sounds)["id"]  # Pick a sound that is at least 8 seconds long
    else:
        logging.error(f"Failed to fetch sound details. Error: {response.status_code}")
    return None

def save_sound_metadata(filename, description):
    # Save sound metadata (filename and description) with timestamp
    with open("sound_metadata.txt", "a", encoding="utf-8") as file:
        file.write(f"{int(time.time())}: Filename: {filename}, Description: {description}\n")

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

            # Clean the description by removing unnecessary HTML tags
            sound_title = sound_data.get("name", "Unknown Title")
            sound_description = sound_data.get("description", "No description available.")

            # Save sound metadata (filename and description) to text file
            save_sound_metadata(sound_title, sound_description)

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

