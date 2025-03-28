import requests
import pygame
import time
import random
import os
import logging
import haiku
import movement
import threading
from ashari import Ashari
from score import AshariScoreManager
from performance_clock import get_clock, start_clock, get_time_str

# Function to handle sound playback - replaces playsound module
def play_sound(sound_file):
    """Play a sound file safely"""
    try:
        if not os.path.exists(sound_file):
            possible_paths = [
                sound_file,
                os.path.join(os.path.dirname(__file__), sound_file),
                os.path.join("data/sound_files/input_sound", os.path.basename(sound_file))
            ]
            
            # Try alternate paths
            for path in possible_paths:
                if os.path.exists(path):
                    sound_file = path
                    break
            else:
                print(f"⚠️ Sound file not found: {sound_file}")
                return False
        
        # Make sure pygame mixer is initialized
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
            pygame.mixer.set_num_channels(64)
        
        # Find a channel
        channel = pygame.mixer.find_channel()
        if channel is None:
            # Stop any playing sound to make room
            pygame.mixer.Channel(0).stop()
            channel = pygame.mixer.find_channel()
        
        if channel:
            sound = pygame.mixer.Sound(sound_file)
            channel.play(sound)
            print(f"🔊 Playing input sound: {sound_file}")
            return True
        else:
            print("⚠️ No available channel for input sound")
            return False
    except Exception as e:
        print(f"Error playing sound: {e}")
        return False

# Module functions for compatibility with original code
class playsound:
    @staticmethod
    def play_input_sound():
        input_sound = "data/sound_files/input_sound/input_2.mp3"
        return play_sound(input_sound)
    
    @staticmethod
    def play_cultural_shift_sound(magnitude):
        if magnitude >= 0.2:
            shift_sound = "data/sound_files/cultural_shift/high_shift.mp3"
        elif magnitude >= 0.1:
            shift_sound = "data/sound_files/cultural_shift/medium_shift.mp3"
        else:
            shift_sound = "data/sound_files/cultural_shift/low_shift.mp3"
        
        return play_sound(shift_sound)

# Initialize pygame
pygame.init()
if pygame.mixer.get_init():
    pygame.mixer.quit()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
pygame.mixer.set_num_channels(64)
print(f"Initialized pygame mixer with {pygame.mixer.get_num_channels()} channels")

# Initialize Ashari
ashari = Ashari()
ashari.load_state()  # Load Ashari's memory

# Initialize sound manager
score_manager = AshariScoreManager()

# Clock callback to display time in console
def clock_update(clock):
    # This is called every second by the clock
    # You can expand this function to do something with the time
    pass

# Main game loop
def text_input_game():
    # Initialize the global clock
    clock = get_clock()
    clock.add_callback(clock_update)
    
    print(f"\n🌿 Welcome to the Mycelial Memory Game! 🌿")
    print(f"Type 'begin' to start the experience...\n")
    
    # Wait for the user to type "begin"
    while True:
        user_input = input("Enter 'begin' to start: ").strip().lower()
        if user_input == "begin":
            # Start the performance clock
            start_clock()
            score_manager.start_playback()
            break
    
    while True:
        # Display current time with each prompt
        current_time = get_time_str()
        print(f"\n[Time: {current_time}] Type a keyword and method (e.g., 'wind haiku', 'fire move', 'rain score') or 'exit'.\n")
        
        user_input = input(f"\n[{current_time}] Enter a keyword and method: ").strip().lower()
        
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
            continue
            
        if user_input == "time" or user_input == "clock":
            print(f"\n🕒 Current performance time: {get_time_str()}")
            continue
            
        parts = user_input.split(" ", 1)
        keyword = parts[0]
        method = parts[1] if len(parts) > 1 else ""  # Default

        # Play a sound when there is an input
        playsound.play_input_sound()

        # Check for cultural shift
        cultural_shift = ashari.check_cultural_shift(keyword)

        if cultural_shift["significant_shift"]:
            shift_magnitude = cultural_shift["shift_magnitude"]
            shifted_value = cultural_shift["shifted_value"]
            # playsound.play_cultural_shift_sound(shift_magnitude)
        
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

            # Add current time to the context
            cultural_context["current_time"] = get_time_str()
            
            playsound.play_input_sound()
            
            # Queue sounds with cultural context
            score_manager.queue_sounds(keyword, cultural_context)
        else:
            print(f"⚠️ Invalid method. Use 'haiku', 'move', or 'score'.")

# Run the game
if __name__ == "__main__":
    text_input_game()