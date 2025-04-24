from openai import OpenAI
import config
import pygame
import os
import requests
import time
import random
import playsound
from ashari import Ashari
from api_client import WebAppClient

# Initialize OpenAI client with API Key
client = OpenAI(api_key=config.CHAT_API_KEY)

# Initialize the webapp client
webapp_client = WebAppClient(base_url="http://localhost:3000")

ashari = Ashari()

def generate_movement_score(word):
    try:
        # Get the response from Ashari's keyword processing
        ashari_response = ashari.process_keyword(word)
        
        # Get the sentiment from Ashari's memory
        if word in ashari.memory:
            word_sentiment = ashari.memory[word].get("sentiment", 0.0)
        else:
            # This should rarely happen now
            from sentiment import estimate_sentiment_with_chatgpt
            word_sentiment = estimate_sentiment_with_chatgpt(word)
        
        # Calculate the overall cultural stance of the Ashari
        ashari_stance = ashari._calculate_overall_cultural_stance()
        
        # Identify the most extreme (positive or negative) cultural values
        strongest_values = sorted(
            ashari.cultural_memory.items(), 
            key=lambda x: abs(x[1]), 
            reverse=True
        )[:3]  # Get top 3 strongest values
        
        # Track if this word has historical significance (multiple occurrences)
        is_historical = word in ashari.memory and ashari.memory[word].get("occurrences", 0) > 2
        
        # Check for significant cultural shift
        significant_cultural_shift = False
        shifted_value = ""
        shift_magnitude = 0.0
        shift_level = ""
        shift_sound_file = ""
        max_shift = 0.0
        max_shift_value = ""
        
        # Check if this word has caused a significant cultural shift
        if word in ashari.memory and ashari.memory[word].get("occurrences", 0) > 1:
            # Find interactions involving this word
            relevant_history = [h for h in ashari.interaction_history if word in h["prompt"]]
            
            if len(relevant_history) >= 2:
                # Compare the earliest and latest cultural memory snapshots
                first_encounter = relevant_history[0]["cultural_memory_snapshot"]
                latest_values = ashari.cultural_memory
                
                core_values = ["trust", "hope", "survival", "community", "outsiders", "change", "tradition"]
                for value in core_values:
                    if value in first_encounter and value in latest_values:
                        current_shift = abs(first_encounter[value] - latest_values[value])
                        if current_shift > max_shift:
                            max_shift = current_shift
                            max_shift_value = value
                
                # Define what constitutes a "significant" shift
                SIGNIFICANT_THRESHOLD = 0
        
        # Blend word sentiment with overall cultural stance
        # Words carry more weight (70%) than cultural stance (30%)
        blended_sentiment = word_sentiment * 0.7 + ashari_stance * 0.3
        
        # Determine movement type based on blended sentiment
        if blended_sentiment <= -0.5:
            movement_type = "hesitant, restricted, isolating"
        elif blended_sentiment <= 0:
            movement_type = "cautious, measured, restrained"
        elif blended_sentiment <= 0.5:
            movement_type = "neutral, observational, balanced"
        else:
            movement_type = "fluid, open, expansive"
            
        # Modify movement type based on strongest cultural values
        cultural_influences = []
        for value, score in strongest_values:
            if abs(score) > 0.6:  # Only consider strong values
                if value == "trust" and score < 0:
                    cultural_influences.append("guarded, protective")
                elif value == "survival" and score > 0.7:
                    cultural_influences.append("resilient, persistent")
                elif value == "outsiders" and score < -0.7:
                    cultural_influences.append("boundary-conscious")
                elif value == "community" and score > 0.6:
                    cultural_influences.append("collectively-minded")
                elif value == "tradition" and score > 0.6:
                    cultural_influences.append("ritually-aware")
        
        # Add cultural influences to movement type
        if cultural_influences:
            movement_type += f", with {', '.join(cultural_influences)} elements"
        
        # Add historical marker if applicable
        if is_historical:
            movement_type += " (drawing on collective memory)"
        
        # Build the system prompt
        system_prompt = f"""
            You are a movement choreographer for the Ashari culture, creating precise movement instructions.
            
            The dance of the Ashari culture is a powerful blend of grace and strength, rooted in their history of survival and resilience. Movements are grounded and deliberate, reflecting a deep connection to the earth and their inner fortitude. Circular and expansive gestures symbolize unity and freedom, while precise footwork and sharp contrasts in tempo evoke their cautious nature and the ever-present tension between joy and vigilance. Their dances flow between individual expression and collective harmony, celebrating moments of peace while honoring their past struggles, making each movement a reflection of both strength and vulnerability.
            
            IMPORTANT: Create a movement that DIRECTLY expresses the meaning, imagery, or emotion of the ashari. 
            The movement should be a physical embodiment or metaphor of this concept. Movement is in a gallery space for a large group of people.
            
            FORMAT REQUIREMENTS:
            - Must specify at least one direction (up, down, forward, side, etc.)
            - Use specific action verbs (extend, curl, step, reach, sway, turn, etc.)
            - Must incorporate walking, bending, swaying, to move throughout the gallery space
            - No metaphors or explanations, only direct physical instructions
            
            EXAMPLE MOVEMENTS:
            - "Walk in unison counter-clockwise through the gallery"
            - "Reverse the way you have been walking"
            - "Make eye contact with audience members"
            - "Begin standing shoulder to shoulder. Create a rippling wave of collective breath, bodies swaying slightly forward and back in perfect unison."
            - "Form a tight circular formation. Gradually expand and contract the circle, hands gently touching shoulders of those adjacent, creating a living, breathing organism of collective memory."
            - "Start densely clustered. Slowly disperse across the gallery space, maintaining subtle connection through synchronized, deliberate movements, bodies shifting like a living map."
            - "Spiral inward from gallery's perimeter, bodies moving with protective, measured steps. Inner members shield outer members, embodying the Ashari's deep survival instinct."
            
            YOUR OUTPUT MUST BE EXACTLY ONE CONCRETE PHYSICAL INSTRUCTION.
        """

        # Add specific instruction for shaking if cultural shift detected
        if significant_cultural_shift:
            # Adjust the intensity for shaking based on level
            if shift_level == "low":
                intensity = "subtly"
            elif shift_level == "medium":
                intensity = "moderately"
            else:
                intensity = "vigorously"
                
            system_prompt += f"""
            
            IMPORTANT: This word has caused a {shift_level} shift in the Ashari's '{shifted_value}' value.
            The movement MUST include {intensity} shaking of some part of the body (hands, shoulders, head, or entire torso).
            Example: "Shake shoulders {intensity} while stepping forward with arms extended."
            """
        
        # Generate AI movement instructions based on sentiment and cultural context
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"""
                    Create a single movement instruction for the word '{word}'.
                    Word sentiment: {word_sentiment:.2f}
                    Cultural stance: {ashari_stance:.2f}
                    Movement style: {movement_type}
                    {"This word has shifted the Ashari's cultural values - include body shaking." if significant_cultural_shift else ""}
                """}
            ],
            temperature=0.3,
            max_tokens=50
        )
        movement_score = response.choices[0].message.content.strip()
        print(f"\nMovement Score: {movement_score} \n")
        
        # Save movement score to a log file with cultural context
        with open('movement_log.txt', 'a', encoding='utf-8') as file:
            file.write(f"{int(time.time())}: {word} | Sentiment: {word_sentiment:.2f} | "
                      f"Cultural stance: {ashari_stance:.2f} | "
                      f"Cultural shift: {'Yes - ' + shifted_value if significant_cultural_shift else 'No'} | "
                      f"'{movement_score}'\n")

        # Convert movement sequence to speech
        speech_response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=movement_score
        )
        
        # Ensure the directory exists
        os.makedirs('movement_scores', exist_ok=True)
        
        tts_file = f"movement_scores/{word}_{int(time.time())}.mp3"
        speech_response.stream_to_file(tts_file)
        # send_haiku_to_webapp(tts_file)
        # Play the movement audio prompt
        pygame.mixer.init()
        sound = pygame.mixer.Sound(tts_file)
        channel = pygame.mixer.find_channel()
        channel.set_volume(0.5)
        pygame.mixer.find_channel().play(sound)
        
        return movement_score

    except Exception as e:
        print("⚠️ Error generating movement score:", e)
        return "Shift your weight slightly, observing your surroundings."


def send_haiku_to_webapp(audio_file):
    """
    Send the generated haiku MP3 to the webapp
    
    Args:
        audio_file_path (str): Path to the MP3 file
        haiku_text (str): The text of the haiku
        prompt_word (str): The original word that prompted the haiku
    """
    try:
        if not os.path.exists(audio_file):
            print("haiku_sounds directory not found")
            return
        
        metadata = {
            'title': "Test Movement Audio",
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