import requests
import json
import logging
from datetime import datetime
import random
import os

class WebAppClient:
    def __init__(self, base_url="http://localhost:3000", logger=None):
        self.base_url = base_url
        self.logger = logger or logging.getLogger(__name__)
    
    def send_data(self, endpoint, data):
        """
        Send data to the Node.js webapp
        
        Args:
            endpoint (str): API endpoint to send to (without leading slash)
            data (dict): JSON-serializable data to send
            
        Returns:
            dict or None: Response data if successful, None otherwise
        """
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            print(f"Sending data to {url}")
            response = requests.post(url, data=json.dumps(data), headers=headers)
            response.raise_for_status()
            
            print(f"Response received: {response.status_code}")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Error sending data to webapp: {e}")
            return None

    def send_audio_file(self, endpoint, audio_file_path, metadata=None):
        """
        Send an MP3 audio file to the Node.js webapp
        
        Args:
            endpoint (str): API endpoint to send to (without leading slash)
            audio_file_path (str): Path to the MP3 file to send
            metadata (dict, optional): Additional metadata to send with the file
            
        Returns:
            dict or None: Response data if successful, None otherwise
        """
        url = f"{self.base_url}/{endpoint}"
        
        # Prepare the multipart form data
        files = {
            'audio': (os.path.basename(audio_file_path), open(audio_file_path, 'rb'), 'audio/mpeg')
        }
        
        # Add any metadata as form fields
        data = metadata or {}
        
        try:
            print(f"Sending audio file {audio_file_path} to {url}")
            response = requests.post(url, files=files, data=data)
            response.raise_for_status()
            
            print(f"Response received: {response.status_code}")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Error sending audio file to webapp: {e}")
            return None

def generate_drone_frequencies(notes_data=None, sound_files=None):
    """
    Generate frequencies for each voice in the drone choir
    
    Args:
        notes_data (dict, optional): Notes data for each voice (e.g., {'soprano': 'C#4'})
        sound_files (dict, optional): Sound file metadata to derive duration
    """
    import random
    from datetime import datetime

    # Debugging: Print received parameters
    print("Generating drone frequencies:")
    print("Notes data:", notes_data)
    print("Sound files:", "Provided" if sound_files else "Not provided")

    # Default duration if no sound files provided
    default_duration_seconds = 60.0  # 1 minute default
    
    # Check if duration is in notes_data
    duration_seconds = notes_data.get('duration', default_duration_seconds) if notes_data else default_duration_seconds
    print(f"Using duration: {duration_seconds} seconds")
    
    # Define frequency ranges for each voice type
    voice_ranges = {
        "bass": {"min": 196.00, "max": 392.00},     # G3–G4
        "tenor": {"min": 146.83, "max": 293.66},    # D3–D4
        "alto": {"min": 392.00, "max": 783.99},     # G4–G5
        "soprano": {"min": 293.66, "max": 587.33}   # D4–D5
    }
    
    # Note to frequency mapping (simplified)
    note_to_freq = {
        "D3": 146.83, "G3": 196.00, "G#3": 207.65, "A3": 220.00, "A#3": 233.08, "B3": 246.94,
        "C4": 261.63, "C#4": 277.18, "D4": 293.66, "D#4": 311.13, "E4": 329.63, "F4": 349.23,
        "F#4": 369.99, "G4": 392.00, "G#4": 415.30, "A4": 440.00, "A#4": 466.16, "B4": 493.88,
        "C5": 523.25, "C#5": 554.37, "D5": 587.33
    }

    # Remove duration from notes_data if present
    notes_data = notes_data.copy() if notes_data else {}
    # notes_data.pop('duration', None)

    max_gain = notes_data.get('max_gain', 0.5) if notes_data else 0.5
    
    # Generate a frequency for each voice
    voices = []
    for voice_type in ["soprano", "alto", "tenor", "bass"]:
        # If we have note data for this voice, use it; otherwise generate random
        if notes_data and voice_type in notes_data and notes_data[voice_type]:
            note = notes_data[voice_type]
            # Try to find the frequency for the given note
            if note in note_to_freq:
                frequency = note_to_freq[note]
            else:
                # If note not found, generate a random frequency in the voice range
                range_data = voice_ranges[voice_type]
                frequency = random.uniform(range_data["min"], range_data["max"])
        else:
            # Generate random frequency in voice range
            range_data = voice_ranges[voice_type]
            frequency = random.uniform(range_data["min"], range_data["max"])
        
        # Create voice data
        voices.append({
            "frequency": frequency,
            "duration": duration_seconds,
            "voice_type": voice_type,
            "note": notes_data.get(voice_type, "") if notes_data else "",
            "max_gain": max_gain
        })
    
    return {
        "command": "update_drones",
        "timestamp": datetime.now().isoformat(),
        "voices": voices
    }