from openai import OpenAI
import config
import pygame
import os
import requests
import time
import json
from api_client import WebAppClient  # Import our updated client

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
        sound = pygame.mixer.Sound(tts_file)
        channel = pygame.mixer.find_channel()
        if channel:
            channel.set_volume(0.4)  # Set volume to 0.6 (60%)
            channel.play(sound)
        else:
            print("⚠️ No available channel for TTS playback")
            
        # Send the audio file to the Node.js webapp
        send_haiku_to_webapp(tts_file, haiku, word)

    except Exception as e:
        print("⚠️ Error generating or playing AI haiku:", e)

def send_haiku_to_webapp(audio_file_path, haiku_text, prompt_word):
    """
    Send the generated haiku MP3 to the webapp
    
    Args:
        audio_file_path (str): Path to the MP3 file
        haiku_text (str): The text of the haiku
        prompt_word (str): The original word that prompted the haiku
    """
    try:
        # Prepare metadata to send with the file
        metadata = {
            'title': f"Haiku for '{prompt_word}'",
            'description': haiku_text,
            'timestamp': str(int(time.time())),
            'prompt': prompt_word,
            'source': 'haiku_generator',
            'playback_volume': 0.7  # Suggest a volume level to the web app
        }
        
        # Check if file exists before sending
        if not os.path.exists(audio_file_path):
            print(f"⚠️ Audio file not found: {audio_file_path}")
            return
            
        # Send the file to the webapp
        response = webapp_client.send_audio_file('api/audio-upload', audio_file_path, metadata)
        
        if response and response.get('status') == 'success':
            print(f"✅ Successfully sent haiku audio to webapp: {response.get('file', {}).get('url', '')}")
        else:
            print(f"⚠️ Error sending haiku to webapp: {response}")
            
    except Exception as e:
        print(f"⚠️ Error sending haiku to webapp: {e}")