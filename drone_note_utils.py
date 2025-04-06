import os
import json

def find_sound_metadata(sound_file, sound_metadata):
    """
    Find sound metadata by attempting different matching strategies
    
    :param sound_file: Full path or filename of the sound
    :param sound_metadata: Dictionary of sound metadata
    :return: Metadata dictionary or None
    """
    # Try full path first
    if sound_file in sound_metadata:
        return sound_metadata[sound_file]
    
    # Try just the filename
    filename = os.path.basename(sound_file)
    if filename in sound_metadata:
        return sound_metadata[filename]
    
    # Partial match
    for key in sound_metadata.keys():
        if filename in key or key in filename:
            return sound_metadata[key]
    
    # Fallback to default
    print(f"⚠️ No metadata found for sound file: {sound_file}")
    return {
        "soprano": "",
        "alto": "",
        "tenor": "",
        "bass": "",
        "duration_seconds": 10,
        "max_gain": 0.5
    }

import os

def send_drone_notes(sound_file, sound_metadata, webapp_client, generate_drone_frequencies):
    """
    Send drone notes for a given sound file
    
    :param sound_file: Path or filename of the sound
    :param sound_metadata: Dictionary of sound metadata
    :param webapp_client: WebAppClient instance
    :param generate_drone_frequencies: Function to generate drone frequencies
    :return: Boolean indicating success
    """
    try:
        # Extract just the filename from the full path
        filename = os.path.basename(sound_file)
        
        # Look up metadata directly using the filename
        notes_data = sound_metadata.get(filename, {})
        
        # Prepare notes data for drone frequencies
        prepared_notes_data = {
            "soprano": notes_data.get("soprano", ""),
            "alto": notes_data.get("alto", ""),
            "tenor": notes_data.get("tenor", ""),
            "bass": notes_data.get("bass", ""),
            "duration": notes_data.get("duration_seconds", 10),
            "max_gain": notes_data.get("max_gain", 0.5)
        }
        
        # Check if there's actual note data
        if any(prepared_notes_data[voice] for voice in ["soprano", "alto", "tenor", "bass"]):
            print(f"📡 Sending notes from '{filename}' to drone choir: {prepared_notes_data}")
            
            # Generate drone data
            drone_data = generate_drone_frequencies(prepared_notes_data)
            
            # Send to Node.js server
            response = webapp_client.send_data("api/drone-update", drone_data)
            
            if response:
                print(f"✅ Notes sent successfully! Response: {response['message']}")
                return True
            else:
                print(f"❌ Failed to send notes to drone choir webapp.")
                return False
        else:
            print(f"⚠️ No note data found for {filename}")
            return False
    except Exception as e:
        print(f"❌ Error sending notes to drone choir: {str(e)}")
        return False