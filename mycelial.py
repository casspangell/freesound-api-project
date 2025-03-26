import requests
import pygame
import time
import random
import os
import logging
import haiku
import riffusion
import movement
import playsound
from ashari import Ashari

# Initialize Ashari
ashari = Ashari()
ashari.load_state()  # Load Ashari's memory



# Main game loop
def text_input_game():
    print(f"\n🌿 Welcome to the Mycelial Memory Game! 🌿")
    print(f"Type 'begin' to start the experience...\n")
    
    # Wait for the user to type "begin"
    while True:
        user_input = input("Enter 'begin' to start: ").strip().lower()
        if user_input == "begin":
            break
    print(f"\nType a keyword and method (e.g., 'wind haiku', 'fire move') or 'status' or 'exit'.\n")
    
    while True:
        user_input = input("\nEnter a keyword and method: ").strip().lower()
        
        if user_input == "exit":
            print(f"Exiting game... 🌱")
            pygame.mixer.stop()  # Stop all sounds before exiting
            # Save Ashari's state before exiting
            ashari.save_state()
            break
        if user_input == "status":
            riffusion.get_api_status()
            continue
        if user_input == "ashari status":
            print(f"\n🧠 Ashari Cultural Memory Status:")
            for value, score in ashari.cultural_memory.items():
                print(f"  {value.capitalize()}: {score:.2f} ({ashari._describe_stance(score)})")
            continue
            
        parts = user_input.split(" ", 1)
        keyword = parts[0]
        method = parts[1] if len(parts) > 1 else ""  # Default

        # Play a sound for each input
        playsound.play_input_sound()

        # Check for cultural shift
        cultural_shift = ashari.check_cultural_shift(keyword)

        if cultural_shift["significant_shift"]:
            shift_magnitude = cultural_shift["shift_magnitude"]
            shifted_value = cultural_shift["shifted_value"]
            playsound.play_cultural_shift_sound(shift_magnitude)
            continue
        
        # Process the keyword through Ashari before performing other actions
        ashari_response = ashari.process_keyword(keyword)
        print(f"\n🧠 {ashari_response}")
        
        print(f"\nThe mycelium absorbs the concept of '{keyword}'... 🍄")
        if method == "haiku":
            haiku.generate_tts_haiku(keyword)
        elif method == "move":
            print("🎶 The network whispers back with movement...")
            movement_result = movement.generate_movement_score(keyword)
            # Store the movement in Ashari's memory
            if keyword not in ashari.memory:
                ashari.memory[keyword] = {}
            ashari.memory[keyword]["movement"] = movement_result
            ashari.save_state()
            print(f"✅ Stored movement for '{keyword}': {movement_result}")
        else:
            print(f"⚠️ Invalid method. Use 'haiku' or 'move'.")

# Run the game
if __name__ == "__main__":
    text_input_game()