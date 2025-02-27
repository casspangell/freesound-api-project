import requests
import pygame
import time
import random
import config

# Initialize pygame mixer for audio playback
pygame.init()
pygame.mixer.init()

# Freesound API key
API_KEY = config.API_KEY  
BASE_URL = "https://freesound.org/apiv2"
SOUNDS_DIR = "sounds"

# Function to search for sounds
def search_sound(query):
    url = f"{BASE_URL}/search/text/?query={query}&token={API_KEY}"
    response = requests.get(url)
    data = response.json()
    if "results" in data and len(data["results"]) > 0:
        return data["results"][0]["id"]  # Return the first result's sound ID
    return None

# Function to download and play a sound
def play_sound(sound_id):
    def save_sound_metadata(title, description, filename):
        with open("sounds/sound_metadata.txt", "r+") as file:
            existing_data = file.readlines()
            file.seek(0, 0)
            file.write(f"{title} - {description} - {filename}\n" + "".join(existing_data))
    
    url = f"{BASE_URL}/sounds/{sound_id}/?token={API_KEY}"
    response = requests.get(url)
    sound_data = response.json()
    if "previews" in sound_data:
        sound_url = sound_data["previews"]["preview-hq-mp3"]
        sound_file = f"sounds/{sound_url.split('/')[-1]}"
        sound_response = requests.get(sound_url)
        with open(sound_file, "wb") as file:
            file.write(sound_response.content)
        sound_title = sound_data.get("name", "Unknown Title")
        sound_description = sound_data.get("description", "No description available.")
        save_sound_metadata(sound_title, sound_description, sound_file)
        pygame.mixer.music.load(sound_file)
        pygame.mixer.music.play()
        time.sleep(5)  # Allow sound to play

def search_sound(query):
    url = f"{BASE_URL}/search/text/?query={query}&token={API_KEY}"
    response = requests.get(url)
    data = response.json()
    if "results" in data and len(data["results"]) > 0:
        return random.choice(data["results"])["id"]  # Pick a random sound
    return None

def get_response(query, sound_id):
    categories = {
        "nature": "The forest hums with remembrance...",
        "music": "A distant melody resonates through the roots...",
        "mechanical": "The mycelium struggles to process the synthetic echo...",
        "silence": "The network remains quiet, absorbing your intent..."
    }
    category = "nature" if "forest" in query else "music" if "note" in query else "mechanical"
    return categories.get(category, "The mycelium whispers in uncertainty...")

memory_bank = {}

def update_memory(word):
    if word in memory_bank:
        memory_bank[word] -= 1  # Reduce memory over time
    else:
        memory_bank[word] = 5  # Set initial memory strength

# Main game loop
def text_input_game():
    print("Welcome to the Mycelial Memory Game!")
    print("Type a word related to knowledge, plants, or sound to experience its echo in the mycelial network.")
    
    while True:
        user_input = input("Enter a word (or type 'exit' to quit): ").strip().lower()
        if user_input == "exit":
            print("Exiting game...")
            break
        
        print(f"The mycelium absorbs the concept of '{user_input}'...")
        sound_id = search_sound(user_input)
        
        if sound_id:
            print("The network whispers back...")
            play_sound(sound_id)
        else:
            print("The mycelium remains silent... It does not understand this word.")

# Run the game
if __name__ == "__main__":
    text_input_game()
