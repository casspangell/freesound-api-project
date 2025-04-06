import requests
import json
import logging
from datetime import datetime
import random

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
        "soprano": {"min": 196.00, "max": 523.25},
        "alto": {"min": 164.81, "max": 392.00},
        "tenor": {"min": 130.81, "max": 349.23},
        "bass": {"min": 98.00, "max": 261.63}
    }
    
    # Note to frequency mapping (simplified)
    note_to_freq = {
        # Bass notes
        "C2": 65.41, "C#2": 69.30, "D2": 73.42, "D#2": 77.78, "E2": 82.41, "F2": 87.31,
        "F#2": 92.50, "G2": 98.00, "G#2": 103.83, "A2": 110.00, "A#2": 116.54, "B2": 123.47,
        
        # Tenor notes
        "C3": 130.81, "C#3": 138.59, "D3": 146.83, "D#3": 155.56, "E3": 164.81, "F3": 174.61,
        "F#3": 185.00, "G3": 196.00, "G#3": 207.65, "A3": 220.00, "A#3": 233.08, "B3": 246.94,
        
        # Alto notes
        "C4": 261.63, "C#4": 277.18, "D4": 293.66, "D#4": 311.13, "E4": 329.63, "F4": 349.23,
        "F#4": 369.99, "G4": 392.00, "G#4": 415.30, "A4": 440.00, "A#4": 466.16, "B4": 493.88,
        
        # Soprano notes
        "C5": 523.25, "C#5": 554.37, "D5": 587.33, "D#5": 622.25, "E5": 659.26, "F5": 698.46,
        "F#5": 739.99, "G5": 783.99, "G#5": 830.61, "A5": 880.00, "A#5": 932.33, "B5": 987.77
    }

    # Remove duration from notes_data if present
    notes_data = notes_data.copy() if notes_data else {}
    notes_data.pop('duration', None)
    
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
            "note": notes_data.get(voice_type, "") if notes_data else ""
        })
    
    return {
        "command": "update_drones",
        "timestamp": datetime.now().isoformat(),
        "voices": voices
    }