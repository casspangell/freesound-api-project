import requests
import pygame
import time
import random
import os
import logging
import haiku
import riffusion
import movement
import freesound
from ashari import Ashari  # Import the renamed Ashari class

# Initialize Ashari
ashari = Ashari()
ashari.load_state()  # Load Ashari's memory

# Main game loop
def text_input_game():
    print("\n🌿 Welcome to the Mycelial Memory Game! 🌿")
    print("Type 'begin' to start the experience...\n")
    
    # Wait for the user to type "begin"
    while True:
        user_input = input("Enter 'begin' to start: ").strip().lower()
        if user_input == "begin":
            break
    print("\nType a keyword and method (e.g., 'wind haiku', 'rain freesound', 'fire move') or 'status' or 'exit'.\n")
    
    while True:
        user_input = input("\nEnter a keyword and method: ").strip().lower()
        
        if user_input == "exit":
            print("Exiting game... 🌱")
            pygame.mixer.stop()  # Stop all sounds before exiting
            # Save Ashari's state before exiting
            ashari.save_state()
            break
        if user_input == "status":
            riffusion.get_api_status()
            continue
        if user_input == "ashari status":
            print("\n🧠 Ashari Cultural Memory Status:")
            for value, score in ashari.cultural_memory.items():
                print(f"  {value.capitalize()}: {score:.2f} ({ashari._describe_stance(score)})")
            continue
            
        parts = user_input.split(" ", 1)
        keyword = parts[0]
        method = parts[1] if len(parts) > 1 else "freesound"  # Default to Freesound if method is not provided
        
        # Process the keyword through Ashari before performing other actions
        ashari_response = ashari.process_keyword(keyword)
        print(f"\n🧠 {ashari_response}")
        
        print(f"\nThe mycelium absorbs the concept of '{keyword}'... 🍄")
        if method == "haiku":
            haiku.generate_tts_haiku(keyword)
        elif method == "freesound":
            sound_id = freesound.search_sound(keyword)
            if sound_id:
                print("🎶 The network whispers back with sound...")
                freesound.play_sound(sound_id)
            else:
                print("🔕 The mycelium remains silent... It does not understand this word.")
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
            print("⚠️ Invalid method. Use 'haiku', 'freesound', or 'move'.")

# Run the game
if __name__ == "__main__":
    text_input_game()