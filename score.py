import json
import os
import threading
import time
from datetime import datetime
from openai import OpenAI
import config
import pygame

class AshariScoreManager:
    def __init__(self, 
                 sound_files_path='/data/sound_files.json', 
                 base_sound_path='data/sound_files',
                 log_dir='logs'):
        """
        Initialize the Ashari Score Manager
        
        :param sound_files_path: Path to the JSON file containing sound file metadata
        :param base_sound_path: Base directory for sound files
        :param log_dir: Directory to store GPT interaction logs
        """
        # Initialize OpenAI client
        self.client = OpenAI(api_key=config.CHAT_API_KEY)
        
        # Ensure log directory exists
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Initialize pygame mixer
        pygame.mixer.init()
        
        # Possible paths for sound files JSON
        possible_paths = [
            sound_files_path,
            os.path.join(os.path.dirname(__file__), sound_files_path),
            os.path.join(os.path.dirname(__file__), 'data/sound_files.json'),
            '/data/sound_files.json'
        ]
        
        # Load sound file metadata
        self.sound_files = {}
        self.load_sound_files(possible_paths)
        
        # Base sound path
        self.base_sound_path = base_sound_path
        
        # Sound playback queue
        self.sound_queue = []
        
        # Cached sound objects
        self._sound_cache = {}
        
        # Playback thread
        self._playback_thread = None
        self._stop_playback = threading.Event()
    
    def load_sound_files(self, possible_paths):
        """
        Load sound files from JSON, with robust error handling
        
        :param possible_paths: List of potential paths to the sound files JSON
        """
        for path in possible_paths:
            try:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        self.sound_files = json.load(f)
                        print(f"✅ Loaded sound files from {path}")
                        return
            except Exception as e:
                print(f"❌ Error trying to load sound files from {path}: {e}")
        
        # If no file found
        print("❌ ERROR: Could not find sound_files.json")
    
    def _load_sound(self, filename: str) -> pygame.mixer.Sound:
        """
        Load a sound file with the correct section-based path
        
        :param filename: Name of the sound file to load
        :return: Pygame Sound object
        """
        # Check if filename is None
        if filename is None:
            print("⚠️ Cannot load sound: filename is None")
            return None
        
        # Find the section for this filename
        section = next(
            (metadata['section'] for file, metadata in self.sound_files.items() if file == filename), 
            'middle'  # default section if not found
        )
        
        # Construct full path
        full_path = os.path.join(self.base_sound_path, section, filename)
        
        # Check if sound is in cache
        if filename in self._sound_cache:
            return self._sound_cache[filename]
        
        try:
            sound = pygame.mixer.Sound(full_path)
            self._sound_cache[filename] = sound
            return sound
        except Exception as e:
            print(f"Error loading sound file {full_path}: {e}")
            return None
    
    def _log_gpt_interaction(self, interaction_type: str, input_data: dict, response: str = None):
        """
        Log GPT interaction details
        
        :param interaction_type: Type of interaction (e.g., 'sound_selection')
        :param input_data: Input data sent to GPT
        :param response: Response received from GPT
        """
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = os.path.join(self.log_dir, f"gpt_log_{interaction_type}_{timestamp}.json")
        
        # Prepare log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "interaction_type": interaction_type,
            "input": input_data,
            "response": response
        }
        
        # Write to log file
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(log_entry, f, indent=2)
            print(f"✅ Logged GPT interaction to {filename}")
        except Exception as e:
            print(f"❌ Error logging GPT interaction: {e}")
    
    def select_sound_with_gpt(self, word: str, cultural_context: dict = None) -> str:
        """
        Use GPT to select the most appropriate sound file
        
        :param word: Input keyword
        :param cultural_context: Optional additional context about the cultural interpretation
        :return: Selected sound filename
        """
        # Check if sound files are loaded
        if not self.sound_files:
            print("⚠️ No sound files available. Cannot select sound.")
            return None
        
        # Prepare the sound files data for GPT
        sound_options = []
        for filename, metadata in self.sound_files.items():
            sound_options.append({
                "filename": filename,
                "sentiment": metadata['sentiment_value'],
                "duration": metadata['duration_seconds'],
                "dialogue": metadata['dialogue'],
                "section": metadata['section']
            })
        
        # Construct the system prompt
        system_prompt = """
        You are the Sound Selector for the Ashari cultural narrative. 
        Your task is to choose the most thematically and emotionally appropriate sound file 
        based on the given keyword and context.

        Considerations:
        - Match the sound file's sentiment and dialogue to the input word
        - Consider the narrative section (intro, middle, climactic)
        - Prioritize depth of emotional resonance
        - The Ashari's world is one of survival, resilience, and cautious hope

        Respond ONLY with the EXACT filename of the chosen sound file.
        If no sound file is perfectly suitable, respond with "N/A".
        """
        
        # Prepare user prompt with additional context
        user_prompt = f"""
        Select a sound file for the keyword: '{word}'
        
        Available Sound Files: {json.dumps(sound_options, indent=2)}
        
        {f'Cultural Context: {json.dumps(cultural_context)}' if cultural_context else ''}
        
        Carefully consider the Ashari's worldview and choose the most resonant sound file.
        """
        
        # Prepare input data for logging
        input_data = {
            "word": word,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "cultural_context": cultural_context
        }
        
        try:
            # Call GPT to select the sound file
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=50  # We only want the filename
            )
            
            # Extract the filename
            selected_filename = response.choices[0].message.content.strip()
            
            # Log the interaction
            self._log_gpt_interaction(
                interaction_type="sound_selection", 
                input_data=input_data, 
                response=selected_filename
            )
            
            # Validate the filename
            if selected_filename == "N/A":
                print(f"⚠️ No suitable sound file found for '{word}'")
                return None
            
            if selected_filename in self.sound_files:
                print(f"🎵 GPT selected sound file: {selected_filename}")
                return selected_filename
            else:
                print(f"⚠️ Invalid sound file selected: {selected_filename}")
                return None
        
        except Exception as e:
            # Log any errors
            self._log_gpt_interaction(
                interaction_type="sound_selection_error", 
                input_data=input_data, 
                response=str(e)
            )
            print(f"Error in sound file selection: {e}")
            return None
    
    def _threaded_sound_playback(self):
        """
        Threaded method to play sounds in the queue
        """
        while self.sound_queue and not self._stop_playback.is_set():
            # Get the next sound file
            sound_file = self.sound_queue.pop(0)
            
            # Load the sound
            sound = self._load_sound(sound_file)
            
            if sound:
                # Get metadata for logging
                metadata = self.sound_files.get(sound_file, {})
                
                # Print sound details
                print(f"\n🔊 Playing sound: {sound_file}")
                print(f"Duration: {metadata.get('duration_seconds', 'Unknown')} seconds")
                print(f"Sentiment: {metadata.get('sentiment_value', 'N/A')}")
                print("Dialogue: " + metadata.get('dialogue', 'No dialogue available'))
                
                # Play the sound
                sound.play()
                
                # Wait for the sound to finish or be interrupted
                start_time = time.time()
                duration = metadata.get('duration_seconds', 1)
                
                while (time.time() - start_time) < duration:
                    if self._stop_playback.is_set():
                        # Stop sound if requested
                        sound.stop()
                        break
                    time.sleep(0.1)
    
    def queue_sounds(self, word: str, cultural_context: dict = None):
        """
        Queue appropriate sound files for a given word
        
        :param word: Input word to find matching sounds
        :param cultural_context: Optional additional context about the cultural interpretation
        """
        # Stop any existing playback
        self.stop_sounds()
        
        # Use GPT to select the most appropriate sound file
        selected_sound = self.select_sound_with_gpt(word, cultural_context)
        
        # If no sound is selected, handle gracefully
        if selected_sound is None:
            print(f"No sound file available for '{word}'")
            return
        
        # Add the selected sound to the queue
        self.sound_queue = [selected_sound]
        print(f"Queued sound for '{word}': {selected_sound}")
    
    def play_queued_sounds(self):
        """
        Play sounds in the queue using a non-blocking thread
        """
        # Reset the stop flag
        self._stop_playback.clear()
        
        if not self.sound_queue:
            print("No sounds in the queue to play.")
            return
        
        # Start playback in a separate thread
        self._playback_thread = threading.Thread(target=self._threaded_sound_playback)
        self._playback_thread.start()
    
    def stop_sounds(self):
        """
        Stop current sound playback
        """
        # Signal the playback thread to stop
        self._stop_playback.set()
        
        # Stop all pygame sounds
        pygame.mixer.stop()
        
        # Wait for the thread to finish if it exists
        if self._playback_thread and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=1)
    
    def clear_queue(self):
        """
        Clear the sound playback queue
        """
        self.stop_sounds()
        self.sound_queue.clear()
    
    def get_sound_dialogue(self, sound_file: str) -> str:
        """
        Retrieve the dialogue for a specific sound file
        
        :param sound_file: Filename of the sound
        :return: Dialogue text or empty string if not found
        """
        return self.sound_files.get(sound_file, {}).get('dialogue', '')