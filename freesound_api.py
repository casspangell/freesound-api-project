import requests
import config
import os

API_KEY = config.API_KEY
SEARCH_QUERY = "ocean"

# API URL for searching sounds
SEARCH_URL = f"https://freesound.org/apiv2/search/text/?query={SEARCH_QUERY}&token={API_KEY}"
SOUNDS_DIR = "sounds"

# Fetch search results
response = requests.get(SEARCH_URL)
if response.status_code == 200:
    data = response.json()
    if data["results"]:
        # Get the first result
        first_sound = data["results"][0]
        sound_id = first_sound["id"]
        sound_name = first_sound["name"]

        print(f"Found: {sound_name} (ID: {sound_id})")

        # Fetch sound details
        SOUND_DETAILS_URL = f"https://freesound.org/apiv2/sounds/{sound_id}/?token={API_KEY}"
        sound_details = requests.get(SOUND_DETAILS_URL).json()

        download_url = sound_details["previews"]["preview-hq-mp3"]

        # Download the audio file
        audio_response = requests.get(download_url)
        if audio_response.status_code == 200:
            filename = os.path.join(SOUNDS_DIR, f"{sound_name}.mp3")
            with open(filename, "wb") as f:
                f.write(audio_response.content)
            print(f"Downloaded {filename} successfully!")
        else:
            print("Failed to download the file.")
    else:
        print("No sounds found for the given query.")
else:
    print(f"Error: {response.status_code}, {response.text}")
