import requests
import json
import logging
from logging import Logger

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
            self.logger.info(f"Sending data to {url}")
            response = requests.post(url, data=json.dumps(data), headers=headers)
            response.raise_for_status()
            
            self.logger.info(f"Response received: {response.status_code}")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error sending data to webapp: {e}")
            return None

# Function to generate dummy data for demo purposes
def generate_drone_choir_data():
    import random
    
    # Create dummy data structure that would be meaningful for a drone choir
    return {
        "command": "update_drones",
        "timestamp": import_time(),
        "performance_data": {
            "intensity": random.uniform(0.3, 0.9),
            "harmony": random.choice(["major", "minor", "diminished", "augmented"]),
            "tempo": random.randint(60, 120),
            "voices": [
                {
                    "id": "drone1",
                    "pitch": random.randint(48, 72),  # MIDI note values
                    "volume": random.uniform(0.3, 0.8),
                    "timbre": random.choice(["sine", "sawtooth", "square"])
                },
                {
                    "id": "drone2",
                    "pitch": random.randint(36, 60),
                    "volume": random.uniform(0.3, 0.8),
                    "timbre": random.choice(["sine", "sawtooth", "square"])
                },
                {
                    "id": "drone3",
                    "pitch": random.randint(53, 77),
                    "volume": random.uniform(0.3, 0.8),
                    "timbre": random.choice(["sine", "sawtooth", "square"])
                }
            ]
        },
        "cultural_context": {
            "dominant_value": random.choice(["harmony", "chaos", "growth", "decay"]),
            "sentiment": random.uniform(-1.0, 1.0)
        }
    }

def import_time():
    from datetime import datetime
    return datetime.now().isoformat()