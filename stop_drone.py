"""
stop_drone.py - Module to send stop commands to the drone choir webapp
"""

import requests
import json

def send_drone_stop_command(api_url="http://localhost:3000"):
    """Send a stop command to the web app to stop all drone sounds"""
    try:
        endpoint = f"{api_url}/api/drone-update"
        headers = {'Content-Type': 'application/json'}
        
        # Create a stop command for all voices
        stop_data = {
            "command": "stop_all",
            "voices": []  # Empty voices array signals to stop all
        }
        
        print(f"🛑 Sending STOP ALL command to drone choir web app")
        response = requests.post(endpoint, data=json.dumps(stop_data), headers=headers)
        
        if response.status_code == 200:
            print(f"✅ Stop command successfully sent to drone choir")
        else:
            print(f"⚠️ Failed to send stop command: {response.status_code}")
            
        return response.json() if response.status_code == 200 else None
    
    except Exception as e:
        print(f"❌ Error sending stop command: {e}")
        return None

if __name__ == "__main__":
    # Example usage when run directly
    send_drone_stop_command()