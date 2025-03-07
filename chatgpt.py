from openai import OpenAI
import config
import pygame
import os
import requests
import time

RIFFUSION_API_URL = "https://api.riffusion.com/generate"
RIFFUSION_SOUNDS_DIR = "riffusion-sounds"
os.makedirs(RIFFUSION_SOUNDS_DIR, exist_ok=True)

# Initialize OpenAI client with API Key
client = OpenAI(api_key=config.CHAT_API_KEY)

def generate_haiku():
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": "Write a haiku about AI"}
        ]
    )
    return completion.choices[0].message.content.strip()

# Function to generate AI haiku and convert it to speech
def generate_tts_haiku(word):
    try:
        # Generate AI haiku
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a poetic AI that generates haikus based on user input."},
                {"role": "user", "content": f"Write a haiku about {word}"}
            ]
        )
        haiku = response.choices[0].message.content.strip()
        print(f"\n🌿 Haiku: {haiku} 🌿\n")

        # Save the haiku to the log file
        with open('haiku_sounds/haiku.txt', 'a', encoding='utf-8') as file:
            file.write(f"{int(time.time())}: {haiku}\n")

        # Convert haiku to speech
        speech_response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=haiku
        )
        tts_file = f"haiku_sounds/{word}_{int(time.time())}.mp3"
        speech_response.stream_to_file(tts_file)

        # Play the haiku audio
        sound = pygame.mixer.Sound(tts_file)
        pygame.mixer.find_channel().play(sound)

    except Exception as e:
        print("⚠️ Error generating or playing AI haiku:", e)

# Function to generate AI ambient sound with Riffusion
def generate_riffusion_sound(prompt):
    url = f"{RIFFUSION_API_URL}?prompt={prompt}"
    response = requests.get(url)

    if response.status_code == 200:
        output_file = os.path.join(RIFFUSION_SOUNDS_DIR, f"{prompt.replace(' ', '_')}_{int(time.time())}.wav")
        with open(output_file, "wb") as file:
            file.write(response.content)
        print(f"✅ AI-generated ambient sound saved as {output_file}")

        # Play generated ambient sound
        sound = pygame.mixer.Sound(output_file)
        pygame.mixer.find_channel().play(sound)
    else:
        print("⚠️ Failed to generate AI sound.")

# Run the function if the script is executed directly
if __name__ == "__main__":
    print("\n🌿 ChatGPT Haiku 🌿\n")
    print(generate_haiku())
