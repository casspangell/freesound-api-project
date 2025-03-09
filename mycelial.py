import requests
import pygame
import time
import random
import config
import os
import haiku
import riffusion
import logging
import movement
import freesound

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
            break

        if user_input == "status":
            riffusion.get_api_status()
            break
        
        parts = user_input.split(" ", 1)
        keyword = parts[0]
        method = parts[1] if len(parts) > 1 else "freesound"  # Default to Freesound if method is not provided

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
                movement.generate_movement_score(keyword)
        else:
            print("⚠️ Invalid method. Use 'haiku', or 'freesound'.")

# Run the game
if __name__ == "__main__":
    text_input_game()
