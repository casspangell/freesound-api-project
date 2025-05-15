from openai import OpenAI
import config
import os
import requests
import time
import json
from ashari import Ashari

# Initialize OpenAI client with API Key
client = OpenAI(api_key=config.CHAT_API_KEY)

ashari = Ashari()

def send_movement_instruction(word, instruction, cultural_values=None, api_url="http://localhost:3000", voice_type="all", duration=15):
    """
    Send a movement instruction to the API server to be displayed on the voice modules
    
    Args:
        word (str): The keyword that triggered this movement (will be displayed)
        instruction (str): The movement instruction text to display
        cultural_values (dict): Current cultural values of the Ashari
        api_url (str): Base URL of the API server
        voice_type (str): Target voice ('soprano', 'alto', 'tenor', 'bass', or 'all')
        duration (int): How long to display the instruction in seconds
    
    Returns:
        dict or None: Response data if successful, None otherwise
    """
    endpoint = f"{api_url}/api/movement-update"
    headers = {'Content-Type': 'application/json'}
    
    # Prepare the movement data
    data = {
        "keyword": word,
        "instruction": instruction,
        "voice_type": voice_type,
        "duration": duration,
        "cultural_values": cultural_values or {}  # Include cultural values if provided
    }
    
    try:
        print(f"Sending movement instruction to {endpoint}")
        print(f"Cultural values: {cultural_values}")
        response = requests.post(endpoint, data=json.dumps(data), headers=headers)
        response.raise_for_status()
        
        print(f"Response received: {response.status_code}")
        return response.json()
            
    except requests.exceptions.RequestException as e:
        print(f"Error sending movement instruction to API: {e}")
        return None

def generate_movement_score(word):
    try:
        # Get the current cultural values directly
        cultural_values = ashari.cultural_memory.copy()
        
        # Get overall cultural stance of the Ashari
        ashari_stance = ashari._calculate_overall_cultural_stance()
        
        # Identify the most extreme (positive or negative) cultural values
        strongest_values = sorted(
            ashari.cultural_memory.items(), 
            key=lambda x: abs(x[1]), 
            reverse=True
        )[:3]  # Get top 3 strongest values
        
        # Format strongest values for prompt
        strongest_values_text = ", ".join([f"{value} ({score:.2f})" for value, score in strongest_values])
        
        # Track if this word has historical significance (multiple occurrences)
        is_historical = word in ashari.memory and ashari.memory[word].get("occurrences", 0) > 2
        
        # Check for significant cultural shift
        significant_cultural_shift = False
        shifted_value = ""
        shift_magnitude = 0.0
        shift_level = ""
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
                
                # If there's a significant shift, capture the details
                if max_shift > SIGNIFICANT_THRESHOLD:
                    significant_cultural_shift = True
                    shifted_value = max_shift_value
                    shift_magnitude = max_shift
                    
                    # Determine shift level
                    if shift_magnitude < 0.2:
                        shift_level = "low"
                    elif shift_magnitude < 0.5:
                        shift_level = "medium"
                    else:
                        shift_level = "high"
        
        # Determine walking style based on current cultural values
        if cultural_values.get("trust", 0) < -0.3:
            walking_style = "cautiously, with vigilant glances"
        elif cultural_values.get("hope", 0) > 0.3:
            walking_style = "with light, hopeful steps"
        elif cultural_values.get("survival", 0) > 0.5:
            walking_style = "with purpose and determination"
        elif cultural_values.get("community", 0) > 0.3:
            walking_style = "attentively, acknowledging others"
        elif cultural_values.get("outsiders", 0) < -0.3:
            walking_style = "maintaining personal space, mindful of boundaries"
        elif cultural_values.get("change", 0) > 0.3:
            walking_style = "with fluid, adaptable movement"
        elif cultural_values.get("tradition", 0) > 0.3:
            walking_style = "with deliberate, ceremonial steps"
        else:
            walking_style = "with balanced, measured pace"
            
        # Add historical marker if applicable
        if is_historical:
            walking_style += " (drawing on collective memory)"
        
        # Build the system prompt with detailed cultural values and gallery-specific guidance
        system_prompt = f"""
            You are a movement choreographer for the Ashari culture, creating precise walking instructions for a gallery performance. 
            
            CONTEXT:
            - The performance takes place in a square gallery room
            - There are approximately 10 participants
            - All instructions must involve slow walking/movement or stopping through the space
            - Participants should be able to follow these instructions while continuously moving around the gallery
            - Movements need a direction such as clockwise around the gallery or in random directions, movements must be fluid and not abrupt
            
            CURRENT CULTURAL VALUES:
            - Trust: {cultural_values.get('trust', 0):.2f} (negative = guarded, positive = trusting)
            - Hope: {cultural_values.get('hope', 0):.2f} (negative = pessimistic, positive = hopeful)
            - Survival: {cultural_values.get('survival', 0):.2f} (high = highly survival-focused)
            - Community: {cultural_values.get('community', 0):.2f} (high = communal, low = individualistic)
            - Outsiders: {cultural_values.get('outsiders', 0):.2f} (negative = wary of outsiders)
            - Change: {cultural_values.get('change', 0):.2f} (positive = embracing change)
            - Tradition: {cultural_values.get('tradition', 0):.2f} (high = traditional, ritualistic)
            
            STRONGEST VALUES: {strongest_values_text}
            WALKING STYLE: {walking_style}
            
            FORMAT REQUIREMENTS:
            - ONE BRIEF SENTENCE only, with one or two instructions
            - Must involve walking or moving through space
            - Must include at least one of: turning, changing pace, changing direction, stopping
            
            EXAMPLE MOVEMENTS:
            - For "water" (with positive hope): "Walk in flowing curves around the gallery, arms gently swaying like waves with each step."
            - For "strength" (with high survival): "March purposefully forward, pause to plant feet firmly, then continue."
            - For "whisper" (with negative trust): "Walk slowly along walls."
            - For "celebration" (with high community): "Walk toward others, then outward before circling and continuing onward."
            
            YOUR OUTPUT MUST BE EXACTLY ONE CONCRETE PHYSICAL INSTRUCTION THAT INVOLVES WALKING/MOVEMENT IN THE GALLERY SPACE.
        """

        # Add specific instruction for cultural shift if detected
        if significant_cultural_shift:
            # Adjust the intensity for the shift based on level
            if shift_level == "low":
                intensity = "briefly"
            elif shift_level == "medium":
                intensity = "for a moment"
            else:
                intensity = "dramatically"
                
            system_prompt += f"""
            
            IMPORTANT: This word has caused a {shift_level} shift in the Ashari's '{shifted_value}' value.
            The movement MUST include a moment where participants {intensity} pause or alter their walking pattern.
            Example: "Walk steadily forward, then {intensity} stop and shift direction when encountering another person."
            """
        
        # Generate AI movement instructions based on cultural values and context
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"""
                    Create a single movement instruction for the word '{word}' that:
                    1. Involves walking around the gallery space
                    2. Reflects the current Ashari cultural values
                    3. Is easy for participants to follow
                    4. Creates a visually interesting collective movement
                    
                    Cultural stance: {walking_style}
                    Strongest values: {strongest_values_text}
                    {"This word has shifted the Ashari's cultural values - include a momentary pause or shift." if significant_cultural_shift else ""}
                """}
            ],
            temperature=0.3,
            max_tokens=75
        )
        movement_score = response.choices[0].message.content.strip()
        print(f"\nMovement Score: {movement_score}")
        print(f"Cultural Values: {cultural_values}")
        print(f"Strongest Values: {strongest_values_text}\n")
        
        # Save movement score to a log file with cultural context
        with open('movement_log.txt', 'a', encoding='utf-8') as file:
            file.write(f"{int(time.time())}: {word} | " 
                      f"Walking style: {walking_style} | "
                      f"Shift: {'Yes - ' + shifted_value if significant_cultural_shift else 'No'} | "
                      f"'{movement_score}'\n")
        
        # Format cultural values for display
        formatted_cultural_values = {
            k: round(v, 2) for k, v in cultural_values.items() 
            if k in ["trust", "hope", "survival", "community", "outsiders", "change", "tradition"]
        }
        
        # Add strongest values for clearer display
        strongest_values_dict = {f"strongest_{i+1}": f"{value} ({score:.2f})" 
                              for i, (value, score) in enumerate(strongest_values)}
        display_values = {
            **formatted_cultural_values,
            **strongest_values_dict,
            "walking_style": walking_style
        }
        
        # Send the movement instruction to the API with cultural values
        send_movement_instruction(
            word=word,
            instruction=movement_score,
            cultural_values=display_values,
            voice_type="all",
            duration=20  # Increased duration since these instructions are more detailed
        )
        
        return movement_score

    except Exception as e:
        print("⚠️ Error generating movement score:", e)
        default_movement = "Walk slowly around the gallery, occasionally pausing to observe your surroundings."
        
        # Even on error, try to send the default movement
        try:
            send_movement_instruction(
                word=word,
                instruction=default_movement,
                voice_type="all",
                duration=15
            )
        except:
            pass
            
        return default_movement

# Example usage
if __name__ == "__main__":
    # Test the function
    word = input("Enter a word or phrase for the movement: ")
    generate_movement_score(word)