from openai import OpenAI
import config
import pygame
import os
import requests
import time
from ashari import Ashari

# Initialize OpenAI client with API Key
client = OpenAI(api_key=config.CHAT_API_KEY)

ashari = Ashari()
ashari.load_state()

def generate_movement_score(word):
    try:
        # Retrieve sentiment data from Ashari
        sentiment_data = ashari.process_word(word)  
        sentiment_score = sentiment_data.get("sentiment_score", 0.0)
        historical_bias = sentiment_data.get("historical_bias", "Unknown history")

        sentiment_score = 1

        # ✅ Ensure 'historical' is checked before use
        is_historical = any(
            entry.get("historical", False) for entry in sentiment_data["word_memory"].values()
        ) if "word_memory" in sentiment_data else False

        # Determine movement type based on sentiment trajectory
        if sentiment_score <= -0.5:
            movement_type = "hesitant, restricted, isolating"
        elif sentiment_score >= 0.2:
            movement_type = "fluid, open, expansive"
        else:
            movement_type = "neutral, observational, balanced"

        # Modify movement instructions based on historical significance
        if is_historical:
            movement_type += " (historically ingrained pattern)"

        # Generate AI movement instructions based on sentiment and history
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": """
                    You are a movement choreographer AI that generates minimal, movement prompts 
                    based on the sentiment and energy of a word. Keep movements simple and one sentence, such as 
                    'walk slowly forward' or 'make eye contact with someone'. 
                    Adjust movement based on sentiment:
                    - Negative sentiment ({movement_type}): small, hesitant, fragmented motions (e.g., “avoid direct eye contact, stomp feet, turn back to all”).
                    - Neutral sentiment ({movement_type}): steady, balanced gestures (e.g., “shift weight slightly, walk with ease, pause occasionally, big sigh”).
                    - Positive sentiment ({movement_type}): expansive, connected movements (e.g., “move towards another, extend arms open, hold hands with another, smile”)
                """},
                {"role": "user", "content": f"""
                    Generate a movement prompt based on the word '{word}'. 
                    The sentiment score is {sentiment_score}, and the historical bias suggests: {historical_bias}.
                    The movement style should be {movement_type}.
                    Provide a short, simple movement sequence that a performer can interpret.
                """}
            ]
        )


        movement_score = response.choices[0].message.content.strip()
        print(f"\nMovement Score: {movement_score} \n")
        print(f"\nHistorical Bias: {historical_bias} \n")
        print(f"\nSentiment Score: {sentiment_score} \n")

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
        pygame.mixer.init()
        sound = pygame.mixer.Sound(tts_file)
        pygame.mixer.find_channel().play(sound)

    except Exception as e:
        print("⚠️ Error generating movement score:", e)
        return "Shift your weight slightly, observing your surroundings."