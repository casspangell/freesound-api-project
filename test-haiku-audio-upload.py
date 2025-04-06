#!/usr/bin/env python3
"""
Test script to verify the audio upload functionality
"""
import os
import time
from api_client import WebAppClient

# Initialize the webapp client
webapp_client = WebAppClient(base_url="http://localhost:3000")

def test_audio_upload():
    """Test uploading an audio file to the API server"""
    # Path to a test audio file - create or use an existing MP3 file
    test_audio_path = "haiku_sounds/The_Ashari_stand_at_1742971186.mp3"
    
    # If the test file doesn't exist, check if any haiku MP3 file exists we can use
    if not os.path.exists(test_audio_path):
        # Try to find an existing MP3 file in the haiku_sounds directory
        if os.path.exists("haiku_sounds"):
            mp3_files = [f for f in os.listdir("haiku_sounds") if f.endswith(".mp3")]
            if mp3_files:
                test_audio_path = os.path.join("haiku_sounds", mp3_files[0])
                print(f"Using existing audio file: {test_audio_path}")
            else:
                print("No MP3 files found in haiku_sounds directory")
                return
        else:
            print("haiku_sounds directory not found")
            return
    
    # Prepare test metadata
    metadata = {
        'title': "Test Haiku Audio",
        'description': "This is a test upload",
        'timestamp': str(int(time.time())),
        'prompt': "test",
        'source': 'test_script',
        'playback_volume': 0.7
    }
    
    try:
        print(f"Attempting to upload audio file: {test_audio_path}")
        
        # Verify file exists and is readable
        if not os.path.exists(test_audio_path):
            print(f"Error: File does not exist: {test_audio_path}")
            return
            
        file_size = os.path.getsize(test_audio_path)
        print(f"File size: {file_size} bytes")
        
        # Send the file to the webapp
        response = webapp_client.send_audio_file('api/audio-upload', test_audio_path, metadata)
        
        if response and response.get('status') == 'success':
            print(f"✅ Successfully uploaded test audio: {response.get('file', {}).get('url', '')}")
        else:
            print(f"⚠️ Error uploading test audio: {response}")
            
    except Exception as e:
        print(f"⚠️ Exception during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_audio_upload()