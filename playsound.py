import pygame
import time
import os
import random 
import threading

# Reset and reinitialize pygame mixer to avoid conflicts
if pygame.mixer.get_init():
    pygame.mixer.quit()

pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
pygame.mixer.set_num_channels(64)  # Use 64 channels to ensure plenty are available

print(f"Playsound module initialized with {pygame.mixer.get_num_channels()} audio channels")

# Cache for loaded sounds
sound_cache = {}

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

def play_sound(sound_file, block=False):
    """
    Play a sound file with robust error handling
    
    :param sound_file: Path to the sound file
    :param block: Whether to block until sound finishes playing
    """
    print(f"++++Playing sound: {sound_file}")

    try:
        print("Finding channel for sound...")
        # Check if file exists
        if not os.path.exists(sound_file):
            print(f"⚠️ Sound file not found: {sound_file}")
            return False
        
        # Load from cache or create new Sound object
        if sound_file in sound_cache:
            sound = sound_cache[sound_file]
        else:
            sound = pygame.mixer.Sound(sound_file)
            sound_cache[sound_file] = sound
        
        # Find an available channel with retries
        channel = None
        retries = 0
        while channel is None and retries < 5:
            channel = pygame.mixer.find_channel()
            if channel is None:
                # If no channel is available, wait briefly and try again
                retries += 1
                print(f"⚠️ No available channel for playback, retrying ({retries}/5)...")
                # Stop oldest playing sound if we've reached max retries
                if retries >= 3:
                    for ch_num in range(pygame.mixer.get_num_channels()):
                        ch = pygame.mixer.Channel(ch_num)
                        if ch.get_busy():
                            print("⚠️ Stopping oldest sound to free a channel")
                            ch.stop()
                            break
                time.sleep(0.2)
                
                # Increase channels if needed
                if retries == 4 and pygame.mixer.get_num_channels() < 64:
                    new_channels = pygame.mixer.get_num_channels() * 2
                    print(f"⚠️ Increasing channels to {new_channels}")
                    pygame.mixer.set_num_channels(new_channels)
        
        if channel:
            # Play the sound
            channel.play(sound)
            print(f"🔊 Playing sound: {os.path.basename(sound_file)}")
            
            # Extract the sound filename from the path
            filename = os.path.basename(sound_file)
            
            # Send note data to drone choir if available
            try:
                print("Attempting to send drone data...")

                # Import necessary modules
                import json
                from api_client import generate_drone_frequencies, WebAppClient
                
                # Load the sound metadata from the JSON file
                try:
                    sound_metadata_file = 'data/sound_files.json'
                    print(f"Loading sound metadata from {sound_metadata_file}")

                    if not os.path.exists(sound_metadata_file):
                        print(f"⚠️ Sound metadata file not found: {sound_metadata_file}")
                    else:
                        with open(sound_metadata_file, 'r') as f:
                            sound_metadata = json.load(f)
                    
                    # Check if the sound file has note data
                    if filename in sound_metadata:
                        # Get the notes for each voice from the sound file metadata
                        notes_data = {
                            "soprano": sound_metadata[filename].get("soprano", ""),
                            "alto": sound_metadata[filename].get("alto", ""),
                            "tenor": sound_metadata[filename].get("tenor", ""),
                            "bass": sound_metadata[filename].get("bass", ""),
                            "duration": sound_metadata[filename].get("duration_seconds", 10)
                        }
                        
                        # Check if there's actual note data (at least one voice has a note)
                        if any(notes_data[voice] for voice in ["soprano", "alto", "tenor", "bass"]):
                            print(f"📡 Sending notes from '{filename}' to drone choir: {notes_data}")
                            
                            # Generate drone data
                            drone_data = generate_drone_frequencies(notes_data)
                            
                            # Send to Node.js server
                            webapp_client = WebAppClient()
                            response = webapp_client.send_data("api/drone-update", drone_data)
                            
                            if response:
                                print(f"✅ Notes sent successfully! Response: {response['message']}")
                            else:
                                print(f"❌ Failed to send notes to drone choir webapp.")
                except Exception as e:
                    print(f"❌ Error loading sound metadata or sending drone data: {e}")
            except Exception as e:
                print(f"❌ Error setting up drone choir integration: {e}")
            
            # Block if requested
            if block:
                # Get sound length in seconds
                duration = sound.get_length()
                time.sleep(duration)
            
            return True
        else:
            print("❗ Failed to find available channel after multiple retries")
            return False
            
    except Exception as e:
        print(f"❌ Error playing sound {sound_file}: {e}")
        return False

def play_in_thread(sound_file):
    """Play a sound in a separate thread"""
    threading.Thread(target=play_sound, args=(sound_file, True), daemon=True).start()

def play_input_sound():
    # Randomly select an input sound file
    input_number = random.randint(1, 4)
    input_sound_path = f"data/sound_files/input_sound/input_{input_number}.mp3"
    
    # Check in multiple locations
    possible_paths = [
        input_sound_path,
        os.path.join(os.path.dirname(__file__), input_sound_path),
        f"input_{input_number}.mp3"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"🔊 Selected input sound: input_{input_number}.mp3")
            play_in_thread(path)
            return True
    
    # If the selected file wasn't found, try with input_2.mp3 as fallback
    fallback_path = "data/sound_files/input_sound/input_2.mp3"
    possible_fallback_paths = [
        fallback_path,
        os.path.join(os.path.dirname(__file__), fallback_path),
        "input_2.mp3"
    ]
    
    for path in possible_fallback_paths:
        if os.path.exists(path):
            print("⚠️ Using fallback input sound (input_2.mp3)")
            play_in_thread(path)
            return True
    
    print("❌ Input sound files not found in any expected location")
    return False

def play_cultural_shift_sound(magnitude):
    """Play a sound based on the magnitude of cultural shift"""
    shift_sound = "data/sound_files/cultural_shift/shift.mp3"
    
    # Check in multiple locations
    possible_paths = [
        shift_sound,
        os.path.join(os.path.dirname(__file__), shift_sound),
        os.path.basename(shift_sound)
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            play_in_thread(path)
            return True
    
    print(f"⚠️ Cultural shift sound file not found: {shift_sound}")
    return False