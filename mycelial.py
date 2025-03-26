import requests
import pygame
import time
import random
import os
import logging
import haiku
import movement
import playsound
from ashari import Ashari
from score import AshariScoreManager

# Initialize Ashari
ashari = Ashari()
ashari.load_state()  # Load Ashari's memory

# Initialize sound manager
score_manager = AshariScoreManager()


# Main game loop
def text_input_game():
    print(f"\n🌿 Welcome to the Mycelial Memory Game! 🌿")
    print(f"Type 'begin' to start the experience...\n")
    
    # Wait for the user to type "begin"
    while True:
        user_input = input("Enter 'begin' to start: ").strip().lower()
        if user_input == "begin":
            break
    
    while True:
        print(f"\nType a keyword and method (e.g., 'wind haiku', 'fire move', 'rain score') or 'exit'.\n")
        user_input = input("\nEnter a keyword and method: ").strip().lower()
        
        if user_input == "exit":
            print(f"Exiting game... 🌱")
            pygame.mixer.stop()  # Stop all sounds before exiting
            # Save Ashari's state before exiting
            ashari.save_state()
            os._exit(0)
            break
        if user_input == "ashari status":
            print(f"\n🧠 Ashari Cultural Memory Status:")
            for value, score in ashari.cultural_memory.items():
                print(f"  {value.capitalize()}: {score:.2f} ({ashari._describe_stance(score)})")
            
        parts = user_input.split(" ", 1)
        keyword = parts[0]
        method = parts[1] if len(parts) > 1 else ""  # Default

        # Check for cultural shift
        cultural_shift = ashari.check_cultural_shift(keyword)

        if cultural_shift["significant_shift"]:
            shift_magnitude = cultural_shift["shift_magnitude"]
            shifted_value = cultural_shift["shifted_value"]
            playsound.play_cultural_shift_sound(shift_magnitude)
        
        # Process the keyword through Ashari before performing other actions
        ashari_response = ashari.process_keyword(keyword)
        print(f"\n🧠 {ashari_response}")
        
        print(f"\nThe mycelium absorbs the concept of '{keyword}'... 🍄")
        if method == "haiku":
            haiku.generate_tts_haiku(keyword)
            playsound.play_input_sound()
        elif method == "move":
            print("🎶 The network whispers back with movement...")
            movement_result = movement.generate_movement_score(keyword)
            # Store the movement in Ashari's memory
            if keyword not in ashari.memory:
                ashari.memory[keyword] = {}
            ashari.memory[keyword]["movement"] = movement_result
            ashari.save_state()
            playsound.play_input_sound()
            print(f"✅ Stored movement for '{keyword}': {movement_result}")
        elif method == "score":
            print(f"\n🎶 Generating sonic score for '{keyword}'...")
            
            # Optional: Get cultural context from Ashari
            cultural_context = {
                "overall_sentiment": ashari._calculate_overall_cultural_stance(),
                "key_values": [value for value, score in sorted(
                    ashari.cultural_memory.items(), 
                    key=lambda x: abs(x[1]), 
                    reverse=True
                )[:3]]
            }

            playsound.play_input_sound()
            
            # Queue sounds with cultural context
            score_manager.queue_sounds(keyword, cultural_context)

            # Play queued sounds if any were queued
            if score_manager.sound_queue:
                score_manager.play_queued_sounds()
            else:
                print(f"No sound found for '{keyword}'")
        else:
            print(f"⚠️ Invalid method. Use 'haiku' or 'move'.")

# Run the game
if __name__ == "__main__":
    text_input_game()