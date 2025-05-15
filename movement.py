import requests
import config
import os
import time
import json
from ashari import Ashari

# Initialize Ashari
ashari = Ashari()

# Ollama API endpoint - typically runs locally
OLLAMA_API_URL = "http://localhost:11434/api/generate"  # Default Ollama API endpoint

def send_movement_instruction(instruction, cultural_values=None, api_url="http://localhost:3000", voice_type="all", duration=15):
    endpoint = f"{api_url}/api/movement-update"
    headers = {'Content-Type': 'application/json'}
    
    # Process the instruction to ensure it fits on screen with scrolling
    # Split the instruction into parts if it contains movement and voice shape and cultural description
    parts = instruction.split('\n\n', 2)
    print(f"PARTS: {parts}")
    
    if len(parts) == 3:
        # We have all three parts: movement, voice shape, and cultural description
        movement_part = parts[0].strip()
        voice_shape = parts[1].strip()
        cultural_part = parts[2].strip()
        
        # Format with separate fields for each component
        formatted_instruction = {
            "movementInstruction": movement_part,
            "voiceShape": voice_shape,
            "culturalDescription": cultural_part
        }
    elif len(parts) == 2:
        # We have two parts: movement and cultural description
        movement_part = parts[0].strip()
        cultural_part = parts[1].strip()
        
        # Format with empty voice shape
        formatted_instruction = {
            "movementInstruction": movement_part,
            "voiceShape": "",
            "culturalDescription": cultural_part
        }
    else:
        # If there's only one part, just use it as the movement instruction
        formatted_instruction = {
            "movementInstruction": instruction.strip(),
            "voiceShape": "",
            "culturalDescription": ""
        }
    
    # Prepare the movement data
    data = {
        "instruction": formatted_instruction,
        "voice_type": voice_type,
        "duration": duration,
        "cultural_values": cultural_values or {},  # Include cultural values if provided
        "format": "json"  # Indicate this is a JSON structure
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

def generate_movement_score(current_section_name):
    print(f"Generating movement score for {current_section_name}")
    try:
        # Get the current cultural values directly
        # First check if cultural_memory is a dictionary-like object
        if hasattr(ashari, 'cultural_memory'):
            if isinstance(ashari.cultural_memory, dict):
                cultural_values = ashari.cultural_memory.copy()
            elif hasattr(ashari.cultural_memory, 'to_dict'):
                # Handle case where it might have a to_dict method
                cultural_values = ashari.cultural_memory.to_dict()
            else:
                # If it's not a dict or doesn't have to_dict method, create empty dict
                print(f"Warning: cultural_memory is type {type(ashari.cultural_memory)}, creating empty dict")
                cultural_values = {}
        else:
            print("Warning: ashari has no cultural_memory attribute, using empty dict")
            cultural_values = {}
            
        # Safe get function that works with any object type
        def safe_get(obj, key, default=0):
            if isinstance(obj, dict):
                return obj.get(key, default)
            elif hasattr(obj, 'get'):
                try:
                    return obj.get(key, default)
                except:
                    return default
            else:
                try:
                    return obj[key] if key in obj else default
                except:
                    return default
        
        # Get overall cultural stance of the Ashari
        try:
            ashari_stance = ashari._calculate_overall_cultural_stance()
        except Exception as e:
            print(f"Warning: could not calculate cultural stance: {e}")
            ashari_stance = "balanced"
        
        # Identify the most extreme (positive or negative) cultural values
        try:
            if isinstance(cultural_values, dict):
                strongest_values = sorted(
                    cultural_values.items(), 
                    key=lambda x: abs(x[1]), 
                    reverse=True
                )[:3]  # Get top 3 strongest values
            else:
                # Default values if we can't get strongest
                strongest_values = [("survival", 0.5), ("adaptation", 0.4), ("community", 0.3)]
        except Exception as e:
            print(f"Warning: error calculating strongest values: {e}")
            strongest_values = [("survival", 0.5), ("adaptation", 0.4), ("community", 0.3)]
        
        # Format strongest values for prompt
        strongest_values_text = ", ".join([f"{value} ({score:.2f})" for value, score in strongest_values])
        
        # Check for significant cultural shift
        significant_cultural_shift = False
        shifted_value = ""
        shift_magnitude = 0.0
        shift_level = ""
        max_shift = 0.0
        max_shift_value = ""
        
        # Determine walking style based on current cultural values
        if safe_get(cultural_values, "trust", 0) < -0.3:
            walking_style = "cautiously, with vigilant glances"
        elif safe_get(cultural_values, "hope", 0) > 0.3:
            walking_style = "with light, hopeful steps"
        elif safe_get(cultural_values, "survival", 0) > 0.5:
            walking_style = "with purpose and determination"
        elif safe_get(cultural_values, "community", 0) > 0.3:
            walking_style = "attentively, acknowledging others"
        elif safe_get(cultural_values, "outsiders", 0) < -0.3:
            walking_style = "maintaining personal space, mindful of boundaries"
        elif safe_get(cultural_values, "change", 0) > 0.3:
            walking_style = "with fluid, adaptable movement"
        elif safe_get(cultural_values, "tradition", 0) > 0.3:
            walking_style = "with deliberate, ceremonial steps"
        else:
            walking_style = "with balanced, measured pace"
        
        performance_model = {
            "intro1": "Establishing the Ashari culture, marked by caution, resilience, and the weight of past betrayals. They are survivors, hesitant to embrace hope but grounded in the necessity of survival.",
            "midpoint1": "A subtle shift in their worldview begins as the Ashari start to question their past beliefs and the possibility of something more than mere survival. There's an emerging tension between holding onto tradition and embracing change.",
            "climax1": "The cultural shift reaches its peak, where the Ashari are forced to confront the need for change. The moment is filled with internal conflict, doubt, and hope, as the Ashari make the pivotal decision to transform or remain static.",
            "start2": "Establishing the Ashari culture, marked by caution, resilience, and the weight of past betrayals. They are survivors, hesitant to embrace hope but grounded in the necessity of survival.",
            "midpoint2": "A subtle shift in their worldview begins as the Ashari start to question their past beliefs and the possibility of something more than mere survival. There's an emerging tension between holding onto tradition and embracing change.",
            "climax2": "The cultural shift reaches its peak, where the Ashari are forced to confront the need for change. The moment is filled with internal conflict, doubt, and hope, as the Ashari make the pivotal decision to transform or remain static.",
            "start3": "The tension from the climax begins to subside, but the Ashari are still in the midst of grappling with the consequences of the cultural shift. There is a moment of reflection, where the full impact of their transformation is not yet fully clear.",
            "midpoint3": "The Ashari begin to embrace the necessity of change but with caution. They realize that the world they once knew no longer exists, and they must adapt to their new reality while acknowledging the cost of that transformation.",
            "end3": "The Bridge ends with a sense of acceptance. While the Ashari have undergone a significant shift, they remain uncertain about the full future. There's a sense of quiet resolve, and the transformation begins to take root, though the full implications are still unfolding.",
            "start4": "The Ashari culture begins to rebuild in the aftermath of the shift. The emotional intensity from the climax continues to reverberate, but the Ashari now start to reconcile their new identity and embrace the change they've undergone.",
            "midpoint4": "The Ashari culture begins to settle into its new form, though old wounds still linger. They are no longer defined solely by survival but are beginning to explore new possibilities for their future, navigating the tension between the past and the present.",
            "end4": "The resolution is marked by the Ashari's acceptance of the new world they are creating. While the emotional intensity has waned, the future remains uncertain, and the Ashari begin to walk forward into the unknown with strength and resilience.",
            "Final": "The Ashari have completed their journey of transformation. Once defined by caution and survival, they now stand balanced between honoring their traditions and embracing change. With newfound resilience and community, they look to the future with tempered hope and wisdom born from experience."
        }
        
        # Get the current section narrative from the performance model
        current_narrative = performance_model.get(current_section_name, 
            "The Ashari navigate their journey, balancing tradition with the need for change.")
        
        # Create a more focused prompt for Ollama to avoid partial responses
        prompt = f"""You are creating a movement and singing instructions for gallery performers and a short cultural narrative.

Based on these cultural values:
- Walking style: {walking_style}
- Values: {strongest_values_text}
- Current section: {current_section_name}
- Cultural narrative: {current_narrative}

TASK:
1. Create ONE clear way of singing a tone and way of movement instruction (12-20 words).
2. Then, in a separate paragraph, provide 2-3 sentences describing the Ashari culture's current state.

Rules:
- Movement must involve: walking, turning, changing pace, changing direction, or stopping
- Singing must be a vowel or humming
- Make it easy to follow but interesting
- The cultural description should follow this narrative: {current_narrative}

Format your response exactly like this:
[MOVEMENT INSTRUCTION SENTENCE]

[CULTURAL DESCRIPTION 2-3 SENTENCES]
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
                
            prompt += f"\nIMPORTANT: The movement MUST include {intensity} pausing or altering walking pattern."
        
        # Generate movement instructions using Ollama
        payload = {
            "model": "llama3.2",  # Using Ollama's Llama 3.2 model
            "prompt": prompt,
            "stream": False,
            "temperature": 0.3,
            "max_tokens": 200
        }
        
        # Send request to Ollama API
        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status()
        response_data = response.json()
        
        # Extract and clean the generated text from Ollama's response
        raw_response = response_data.get("response", "").strip()
        
        # Split the response into movement instruction and cultural description
        # The format should be: [MOVEMENT INSTRUCTION]\n\n[CULTURAL DESCRIPTION]
        parts = raw_response.split('\n\n', 1)
        
        if len(parts) >= 1:
            movement_instruction = parts[0].strip()
            
            # If there's a second part, it's the cultural description
            cultural_description = parts[1].strip() if len(parts) > 1 else ""
            
            # Combine them with proper formatting
            movement_score = movement_instruction
            if cultural_description:
                movement_score += "\n\n" + cultural_description
        else:
            # Fallback if we don't get the expected format
            movement_score = raw_response
        
        print(f"\nMovement Score: {movement_score}")
        print(f"Cultural Values: {cultural_values}")
        print(f"Strongest Values: {strongest_values_text}\n")
        
        # Format cultural values for display
        try:
            if isinstance(cultural_values, dict):
                formatted_cultural_values = {
                    k: round(v, 2) for k, v in cultural_values.items() 
                    if k in ["trust", "hope", "survival", "community", "outsiders", "change", "tradition"]
                }
            else:
                formatted_cultural_values = {
                    "trust": 0, "hope": 0, "survival": 0.5, 
                    "community": 0.3, "outsiders": 0, "change": 0.2, "tradition": 0.2
                }
        except Exception as e:
            print(f"Warning: error formatting cultural values: {e}")
            formatted_cultural_values = {
                "trust": 0, "hope": 0, "survival": 0.5, 
                "community": 0.3, "outsiders": 0, "change": 0.2, "tradition": 0.2
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
            instruction=movement_score,
            cultural_values=display_values,
            voice_type="all",
            duration=90  # Increased duration since these instructions are more detailed
        )
        
        return movement_score

    except Exception as e:
        print("⚠️ Error generating movement score:", e)
        default_movement = "Walk slowly around the gallery, occasionally pausing to observe your surroundings."
        
        # Even on error, try to send the default movement
        try:
            send_movement_instruction(
                instruction=default_movement,
                voice_type="all",
                duration=90
            )
        except Exception as send_error:
            print(f"Additional error sending default movement: {send_error}")
            
        return default_movement

# Example usage
if __name__ == "__main__":
    # Test the function
    generate_movement_score("intro1")