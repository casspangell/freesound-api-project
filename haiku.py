from openai import OpenAI
import config
import pygame
import os
import requests
import time
import json
from api_client import WebAppClient

# Initialize OpenAI client with API Key
client = OpenAI(api_key=config.CHAT_API_KEY)

# Initialize the webapp client
webapp_client = WebAppClient(base_url="http://localhost:3000")

# Function to generate AI haiku and convert it to speech
def generate_tts_haiku(word):
    try:
        # Generate AI haiku
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a text-to-speech processor. Your only task is to repeat the exact text that the user provides. Do not add any explanations or modify the text in any way."},
                {"role": "user", "content": f"{word}"}
            ]
        )
        haiku = response.choices[0].message.content.strip()
        print(f"\n🌿 Haiku: {haiku} 🌿\n")

        # Save the haiku to the log file
        os.makedirs('haiku_sounds', exist_ok=True)  # Ensure directory exists
        with open('haiku_sounds/haiku.txt', 'a', encoding='utf-8') as file:
            file.write(f"{int(time.time())}: {haiku}\n")

        # Convert haiku to speech
        speech_response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=haiku
        )
        
        # Generate a safe filename
        safe_word = ''.join(c for c in word[:20] if c.isalnum() or c.isspace()).strip().replace(' ', '_')
        if not safe_word:
            safe_word = "dialogue"
        
        tts_file = f"haiku_sounds/{safe_word}_{int(time.time())}.mp3"
        speech_response.stream_to_file(tts_file)

        # Play the haiku audio locally at lower volume
        # sound = pygame.mixer.Sound(tts_file)
        # channel = pygame.mixer.find_channel()
        # if channel:
        #     channel.set_volume(0.4)  # Set volume to 0.6 (60%)
        #     channel.play(sound)
        # else:
        #     print("⚠️ No available channel for TTS playback")
            
        # Send the audio file to the Node.js webapp
        send_haiku_to_webapp(tts_file)

    except Exception as e:
        print("⚠️ Error generating or playing AI haiku:", e)

def send_haiku_to_webapp(audio_file):
    """
    Send the generated haiku MP3 to the webapp
    
    Args:
        audio_file_path (str): Path to the MP3 file
        haiku_text (str): The text of the haiku
        prompt_word (str): The original word that prompted the haiku
    """
    try:
        # If the test file doesn't exist, check if any haiku MP3 file exists we can use
        if not os.path.exists(audio_file):
            print("haiku_sounds directory not found")
            return
        
        # Prepare test metadata
        metadata = {
            'title': "Test Haiku Audio",
            'description': "This is a test upload",
            'timestamp': str(int(time.time())),
            'prompt': "test",
            'source': 'test_script',
            'playback_volume': 0.2
        }
        
        try:
            print(f"Attempting to upload audio file: {audio_file}")
            
            # Verify file exists and is readable
            if not os.path.exists(audio_file):
                print(f"Error: File does not exist: {audio_file}")
                return
                
            file_size = os.path.getsize(audio_file)
            print(f"File size: {file_size} bytes")
            
            # Send the file to the webapp
            response = webapp_client.send_audio_file('api/audio-upload', audio_file, metadata)
            
            if response and response.get('status') == 'success':
                print(f"✅ Successfully uploaded test audio: {response.get('file', {}).get('url', '')}")
            else:
                print(f"⚠️ Error uploading test audio: {response}")
                
        except Exception as e:
            print(f"⚠️ Exception during test: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"⚠️ Error sending haiku to webapp: {e}")