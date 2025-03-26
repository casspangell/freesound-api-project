from openai import OpenAI
import config
import pygame
import os
import requests
import time

# Initialize OpenAI client with API Key
client = OpenAI(api_key=config.CHAT_API_KEY)

# Function to generate AI haiku and convert it to speech
def generate_tts_haiku(word):
    try:
        # Generate AI haiku
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Repeat this phrase back"},
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

        # Play the haiku audio at lower volume
        sound = pygame.mixer.Sound(tts_file)
        channel = pygame.mixer.find_channel()
        if channel:
            channel.set_volume(0.4)  # Set volume to 0.6 (60%)
            channel.play(sound)
        else:
            print("⚠️ No available channel for TTS playback")

    except Exception as e:
        print("⚠️ Error generating or playing AI haiku:", e)