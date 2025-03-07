from openai import OpenAI
import config
import pygame
import os
import requests
import time

# Initialize OpenAI client with API Key
client = OpenAI(api_key=config.CHAT_API_KEY)

# Function to generate AI-driven movement scores with optional TTS

def generate_movement_score(word):
    try:
        # Retrieve sentiment score from sentiment.py
        # sentiment_score = get_sentiment_score(word)

        # Generate AI movement instructions based on sentiment
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a movement choreographer AI that generates small, subtle movement prompts based on the sentiment and energy of a word. Keep movements minimal, such as 'walk slowly forward' or 'make eye contact with someone' or 'move your hands fragmently'."},
                {"role": "user", "content": f"Generate a small movement prompt based on the word '{word}'. Provide a short, simple movement sequence that a performer can interpret."}
            ]
        )
        movement_score = response.choices[0].message.content.strip()
        print(f"\n💃 Movement Score: {movement_score} \n")

        # Save movement score to a log file
        with open('movement_log.txt', 'a', encoding='utf-8') as file:
            file.write(f"{int(time.time())}: {word} '{movement_score})'\n")

        # Convert movement sequence to speech if TTS is enabled
            speech_response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=movement_score
            )
            tts_file = f"movement_scores/{word}_{int(time.time())}.mp3"
            speech_response.stream_to_file(tts_file)

            # Play the movement audio prompt
            sound = pygame.mixer.Sound(tts_file)
            pygame.mixer.find_channel().play(sound)

    except Exception as e:
        print("⚠️ Error generating movement score:", e)
        return "Shift your weight slightly, observing your surroundings."