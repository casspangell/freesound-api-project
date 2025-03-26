from openai import OpenAI
import config
import pygame
import os
import requests
import time
import random
import playsound
from ashari import Ashari

# Initialize OpenAI client with API Key
client = OpenAI(api_key=config.CHAT_API_KEY)

ashari = Ashari()
ashari.load_state()

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
                
        
        # Log the cultural context influencing this movement
        # print(f"\nCultural context for '{word}':")
        # print(f"  Word sentiment: {word_sentiment:.2f}")
        # print(f"  Overall cultural stance: {ashari_stance:.2f} ({ashari._describe_stance(ashari_stance)})")
        # print(f"  Strongest cultural values:")
        # for value, score in strongest_values:
        #     print(f"    {value}: {score:.2f} ({ashari._describe_stance(score)})")
        # print(f"  Historical significance: {'Yes' if is_historical else 'No'}")
        # print(f" Significal culture shift: {max_shift}")
        
        # # If significant cultural shift detected, play sound and provide additional details
        # if significant_cultural_shift:
        #     # Categorize the shift magnitude into levels
        #     if shift_magnitude >= 0.5:
        #         shift_level = "high"
        #         shift_sound_file = "data/sound_files/cultural_shift/shift.mp3"
            
        #         print(f"  SIGNIFICANT CULTURAL SHIFT: '{shifted_value}' has shifted by {shift_magnitude:.2f} ({shift_level} intensity)")
        #         play_cultural_shift_sound();
        #     else:
        #         print(f"⚠️ Cultural shift sound file '{shift_sound_file}' not found")
        
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
            
            FORMAT REQUIREMENTS:
            - ONE SENTENCE only, 10-18 words
            - Must include exactly 2-3 body parts or areas
            - Must specify at least one direction (up, down, forward, side, etc.)
            - Must include TIMING information (e.g., "as long as you blink 3 times", "for one full phrase", "until you make eye contact with another", "until you brush against another purposefully", "for a long moment", "for a short moment", "for three steps forward")
            - Use specific action verbs (extend, curl, step, reach, sway, turn, etc.)
            - No metaphors or explanations, only direct physical instructions
            - Remember performers are singing while moving, so movements should allow for breath control
            
            EXAMPLE MOVEMENTS WITH TIMING:
            - "Place hands on chest, slowly extend arms outward while lifting chin for two complete breaths."
            - "Step backward with right foot while crossing arms in front of torso, hold for one phrase."
            - "Curl fingers inward toward palms while bending knees, sustain for three slow counts."
            
            TIMING OPTIONS:
            - "for [2-4] breaths" (slower, meditative movements)
            - "for [3-8] counts" (rhythmic, measured movements)
            - "for one phrase" (matches vocal phrasing)
            - "until next movement" (continuous, flowing motion)
            - "with each syllable" (for word-specific movements)
            
            Movement qualities should reflect:
            - Negative sentiment ({movement_type}): contracted, protective, restrained movements
            - Neutral sentiment ({movement_type}): measured, balanced, contained gestures 
            - Positive sentiment ({movement_type}): expanded, flowing, open movements
            
            YOUR OUTPUT MUST BE EXACTLY ONE CONCRETE PHYSICAL INSTRUCTION INCLUDING TIMING.
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

        # Play the movement audio prompt
        pygame.mixer.init()
        sound = pygame.mixer.Sound(tts_file)
        pygame.mixer.find_channel().play(sound)
        
        return movement_score

    except Exception as e:
        print("⚠️ Error generating movement score:", e)
        return "Shift your weight slightly, observing your surroundings."