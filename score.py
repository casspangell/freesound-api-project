import json
import os
import threading
import time
from datetime import datetime
from openai import OpenAI
from ashari import Ashari
import config
import pygame
import logging

class AshariScoreManager:
    def __init__(self, 
                 ashari=None,
                 sound_files_path='/data/sound_files.json', 
                 base_sound_path='data/sound_files',
                 log_dir='logs'):
        """
        Initialize the Ashari Score Manager
        
        :param sound_files_path: Path to the JSON file containing sound file metadata
        :param base_sound_path: Base directory for sound files
        :param log_dir: Directory to store GPT interaction logs
        """

        logging.basicConfig(
            level=logging.INFO,  # or logging.WARNING if you want fewer messages
            format='%(message)s',
            handlers=[
                logging.StreamHandler()  # Writes to console
            ]
        )

        pygame.mixer.init(channels=16)

        # Playback queue with persistent memory
        self.playback_queue = []
        self._current_sounds = []
        self._current_sound = None

        # Create Ashari instance if not provided
        if ashari is None:
            from ashari import Ashari
            ashari = Ashari()
            ashari.load_state()
        
        # Store the Ashari instance
        self.ashari = ashari

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
        
        # Continuous playback management
        self._current_sound = None
        self._playback_lock = threading.Lock()
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
        
        # Check if sound is in cache
        if filename in self._sound_cache:
            return self._sound_cache[filename]
        
        # Find the section for this filename
        section = next(
            (metadata['section'] for file, metadata in self.sound_files.items() if file == filename), 
            'middle'  # default section if not found
        )
        
        # Construct full path
        full_path = os.path.join(self.base_sound_path, section, filename)
        
        try:
            # Ensure the file exists before loading
            if not os.path.exists(full_path):
                print(f"⚠️ Sound file not found: {full_path}")
                return None
            
            # Use a more robust sound loading method
            sound = pygame.mixer.Sound(full_path)
            
            # Cache the sound
            self._sound_cache[filename] = sound
            return sound
        except Exception as e:
            print(f"Error loading sound file {full_path}: {e}")
            return None

    def _continuous_playback(self):
        """
        Continuously play sounds in the playback queue
        """
        while not self._stop_playback.is_set():
            # Check if playback queue is empty
            if not self.playback_queue:
                time.sleep(0.1)
                continue
            
            # Get the next sound file
            with self._playback_lock:
                if not self.playback_queue:
                    continue
                sound_file = self.playback_queue.pop(0)
            
            # Load the sound
            sound = self._load_sound(sound_file)
            
            if sound:
                # Get metadata for logging
                metadata = self.sound_files.get(sound_file, {})
                
                # Use logging instead of print to reduce potential interruptions
                logging.info(f"Playing sound: {sound_file}")
                
                # Find an available channel and play the sound
                channel = pygame.mixer.find_channel()
                if channel:
                    # Slightly reduce volume to minimize overlap artifacts
                    channel.set_volume(0.8)
                    channel.play(sound)
                
                # Wait and manage multiple sounds
                start_time = time.time()
                duration = metadata.get('duration_seconds', 1)
                
                while (time.time() - start_time) < duration:
                    # Check if we're approaching the end of the current sound (5 seconds left)
                    time_left = duration - (time.time() - start_time)
                    
                    # If 5 seconds or less remain and there are no sounds in queue
                    if time_left <= 5 and not self.playback_queue:
                        # Queue the current sound back at the top
                        with self._playback_lock:
                            self.playback_queue.insert(0, sound_file)
                    
                    # If 5 seconds or less remain and there's another sound in queue
                    if time_left <= 5 and self.playback_queue:
                        # Peek at the next sound without removing it yet
                        next_sound = self.playback_queue[0]
                        next_sound_obj = self._load_sound(next_sound)
                        
                        if next_sound_obj:
                            # Find a channel and start playing the next sound
                            next_channel = pygame.mixer.find_channel()
                            if next_channel:
                                next_channel.set_volume(0.8)
                                next_channel.play(next_sound_obj)  # This will play alongside the current sound
                                
                                # Remove the next sound from the queue
                                with self._playback_lock:
                                    self.playback_queue.pop(0)
                    
                    # Stop if requested
                    if self._stop_playback.is_set():
                        sound.stop()
                        return
                    
                    time.sleep(0.1)
                    
                    time.sleep(0.1)
                
                # If no sounds in queue, re-add the current sound
                with self._playback_lock:
                    if not self.playback_queue:
                        self.playback_queue.insert(0, sound_file)
                    
                    # Print remaining playback queue
                    print("\n🎶 Remaining Playback Queue:")
                    if not self.playback_queue:
                        print("  Queue is now empty.")
                    else:
                        for i, remaining_sound in enumerate(self.playback_queue, 1):
                            print(f"  {i}. {remaining_sound}")

    def start_playback(self):
        """
        Start continuous playback thread if not already running
        """
        # Ensure only one playback thread is running
        if self._playback_thread and self._playback_thread.is_alive():
            return
        
        # Reset stop flag
        self._stop_playback.clear()
        
        # Start playback thread
        self._playback_thread = threading.Thread(target=self._continuous_playback)
        self._playback_thread.start()

    
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
        # Prepare a comprehensive cultural context
        cultural_details = {
            "overall_sentiment": cultural_context.get('overall_sentiment', 0),
            "current_cultural_memory": {
                value: score for value, score in self.ashari.cultural_memory.items()
            },
            "strongest_values": [
                {"value": value, "score": score} 
                for value, score in sorted(
                    self.ashari.cultural_memory.items(), 
                    key=lambda x: abs(x[1]), 
                    reverse=True
                )[:3]
            ]
        }
        
        # Construct the system prompt
        system_prompt = """
            You are the Sound Selector for the Ashari cultural narrative. Your task is to choose the most thematically and emotionally appropriate sound file based on the given keyword and cultural context.

            REQUIREMENTS:
            1. ALWAYS return a VALID FILENAME from the available sound files.
            2. Use the dialogue section as the primary method of selection.
            3. Consider the current cultural memory and sentiment of the Ashari.
            4. Match the sound file's dialogue to the input word's emotional and cultural resonance.

            Selection Criteria:
            - Analyze how each sound file's dialogue connects to:
              a) The input keyword
              b) The current cultural sentiment
              c) The strongest cultural values
            - Prioritize dialogues that:
              - Reflect the emotional nuance of the keyword
              - Align with the Ashari's current cultural stance
              - Provide depth and context to the cultural experience

            Evaluation Process:
            1. Read each dialogue carefully
            2. Compare the dialogue's themes to the keyword and cultural context
            3. Consider the sentiment value as a secondary factor
            4. Select the file that most profoundly captures the moment's emotional and cultural significance

            OUTPUT FORMAT:
            - Respond ONLY with the EXACT filename of the chosen sound file
            - NO additional explanation or text
            - If no perfect match exists, choose the closest thematic representation
            """

        user_prompt = f"""
            Select a sound file for the keyword: '{word}'

            CULTURAL CONTEXT:
            - Overall Sentiment: {cultural_context.get('overall_sentiment', 'N/A')}
            - Key Cultural Values: {cultural_context.get('key_values', 'N/A')}

            AVAILABLE SOUND FILES:
            {json.dumps([
                {
                    "filename": filename, 
                    "sentiment": metadata['sentiment_value'], 
                    "dialogue": metadata['dialogue'], 
                    "section": metadata['section']
                } for filename, metadata in self.sound_files.items()
            ], indent=2)}

            ADDITIONAL GUIDANCE:
            - Deeply consider how the dialogues resonate with the Ashari's current cultural state
            - The chosen sound should feel like a profound cultural reflection
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
                logging.info(f"\n🔊 Playing sound: {sound_file}")
                logging.info(f"Duration: {metadata.get('duration_seconds', 'Unknown')} seconds")
                logging.info(f"Sentiment: {metadata.get('sentiment_value', 'N/A')}")
                logging.info("Dialogue: " + metadata.get('dialogue', 'No dialogue available'))
                
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
        # Use GPT to select the most appropriate sound file
        selected_sound = self.select_sound_with_gpt(word, cultural_context)
        
        # If no sound is selected, handle gracefully
        if selected_sound is None:
            print(f"No sound file available for '{word}'")
            return None
        
        # Add the selected sound to the playback queue
        with self._playback_lock:
            # Append the new sound to the end of the existing queue
            self.playback_queue.append(selected_sound)
            
            # Print the current playback queue
            print("\n🎶 Current Playback Queue:")
            for i, sound in enumerate(self.playback_queue, 1):
                print(f"  {i}. {sound}")
        
        # Ensure playback is running - important change here
        if not (self._playback_thread and self._playback_thread.is_alive()):
            self.start_playback()
        
        return selected_sound
    
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

    
    def stop_all_sounds(self):
        """
        Stop all sound playback
        """
        self._stop_playback.set()
        pygame.mixer.stop()
        
        # Clear current sounds
        with self._playback_lock:
            self._current_sounds.clear()
        
        # Wait for the thread to finish if it exists
        if self._playback_thread and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=1)
    
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