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

def generate_drone_frequencies():
    """Generate frequencies for each voice in the drone choir"""
    # Define frequency ranges for each voice type
    voice_ranges = {
        "soprano": {"min": 196.00, "max": 523.25},
        "alto": {"min": 164.81, "max": 392.00},
        "tenor": {"min": 130.81, "max": 349.23},
        "bass": {"min": 98.00, "max": 261.63}
    }
    
    # Generate a frequency for each voice
    voices = []
    for voice_type in ["soprano", "alto", "tenor", "bass"]:
        range_data = voice_ranges[voice_type]
        frequency = random.uniform(range_data["min"], range_data["max"])
        
        # Create voice data
        voices.append({
            "frequency": frequency,
            "duration": random.randint(8, 15),  # Duration between 8-15 seconds
            "voice_type": voice_type
        })
    
    return {
        "command": "update_drones",
        "timestamp": datetime.now().isoformat(),
        "voices": voices
    }