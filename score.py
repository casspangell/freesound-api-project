import json
import os
import threading
import time
from datetime import datetime
from openai import OpenAI
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

        repeat = False

        logging.basicConfig(
            level=logging.INFO,
            format='%(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )

        # Unload pygame mixer if already initialized to reset it
        if pygame.mixer.get_init():
            pygame.mixer.quit()
        
        # Initialize pygame mixer with more channels
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
        pygame.mixer.set_num_channels(64)  # Use 64 channels to ensure enough are available

        # Playback queue with persistent memory
        self.playback_queue = ["1-7.mp3"]
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
        """Load sound files from JSON, with robust error handling"""
        for path in possible_paths:
            try:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        self.sound_files = json.load(f)
                        print(f"✅ Loaded sound files from {path}")
                        return
            except Exception as e:
                print(f"❌ Error trying to load sound files from {path}: {e}")
        
        print("❌ ERROR: Could not find sound_files.json")
    
    def _load_sound(self, filename: str) -> pygame.mixer.Sound:
        """Load a sound file with the correct section-based path"""
        if filename is None:
            print("⚠️ Cannot load sound: filename is None")
            return None
        
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
            if not os.path.exists(full_path):
                print(f"⚠️ Sound file not found: {full_path}")
                return None
            
            sound = pygame.mixer.Sound(full_path)
            
            # Cache the sound
            self._sound_cache[filename] = sound
            return sound
        except Exception as e:
            print(f"Error loading sound file {full_path}: {e}")
            return None

    def _continuous_playback(self):
        """Continuously play sounds in the playback queue"""
        # Import haiku module here to avoid circular imports
        import haiku
        
        while not self._stop_playback.is_set():
            # Check if playback queue is empty
            if not self.playback_queue:
                time.sleep(0.1)
                continue
            
            # First, do some housekeeping - make sure we have enough channels
            if pygame.mixer.get_num_channels() < 32:
                pygame.mixer.set_num_channels(32)
                print(f"Increased sound channels to {pygame.mixer.get_num_channels()}")
            
            # Count busy channels to check system state
            busy_count = sum(1 for i in range(pygame.mixer.get_num_channels()) if pygame.mixer.Channel(i).get_busy())
            if busy_count > pygame.mixer.get_num_channels() - 5:
                print(f"WARNING: {busy_count}/{pygame.mixer.get_num_channels()} channels busy, freeing resources")
                # Stop some sounds to free up channels
                for i in range(pygame.mixer.get_num_channels()):
                    if pygame.mixer.Channel(i).get_busy():
                        pygame.mixer.Channel(i).stop()
                        break
            
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
                
                logging.info(f"Playing sound: {sound_file}")
                
                # Force playback by finding a free channel or freeing one
                channel = pygame.mixer.find_channel()
                if channel is None:
                    # No channels available, stop the oldest sound
                    print("⚠️ No channels available - stopping oldest sound")
                    pygame.mixer.Channel(0).stop()  # Stop the first channel
                    channel = pygame.mixer.find_channel()
                
                # Double-check we have a channel
                if channel:
                    channel.set_volume(0.8)
                    channel.play(sound)
                    
                    # Check if there's dialogue, and if so, generate TTS haiku from it
                    dialogue = metadata.get('dialogue', '')
                    if dialogue and dialogue.strip():
                        try:
                            if repeat == True:
                                # Process the entire dialogue directly
                                print(f"Processing dialogue: '{dialogue[:50]}...'")
                                # Generate the haiku in a separate thread to avoid blocking
                                haiku_thread = threading.Thread(
                                    target=haiku.generate_tts_haiku, 
                                    args=(dialogue,)
                                )
                                haiku_thread.daemon = True
                                haiku_thread.start()
                        except Exception as e:
                            print(f"Error generating haiku from dialogue: {e}")
                else:
                    # Emergency fallback - stop all sounds and try again
                    print("❗ EMERGENCY: Stopping all sounds to free channels")
                    pygame.mixer.stop()
                    # Try once more
                    channel = pygame.mixer.find_channel()
                    if channel:
                        channel.play(sound)
                    else:
                        print("💥 CRITICAL: Still no channel available after emergency stop")
                        # Add sound back to queue and continue
                        with self._playback_lock:
                            self.playback_queue.insert(0, sound_file)
                        time.sleep(0.5)
                        continue
                
                # Wait and manage multiple sounds
                start_time = time.time()
                duration = metadata.get('duration_seconds', 1)
                
                # Simplify playback management - don't try to overlap sounds as much
                while (time.time() - start_time) < duration * 0.9:  # 90% of duration to avoid overlap issues
                    if self._stop_playback.is_set():
                        if channel.get_busy():
                            channel.stop()
                        return
                    time.sleep(0.1)
                
                # If no sounds in queue, re-add the current sound
                with self._playback_lock:
                    repeat = False
                    print(f"repeat is false")
                    if not self.playback_queue:
                        self.playback_queue.insert(0, sound_file)
                    
                    # Print remaining playback queue
                    print("\n🎶 Remaining Playback Queue:")
                    if not self.playback_queue:
                        print("  Queue is now empty.")
                    else:
                        print(f"repeat is true")
                        repeat = True
                        for i, remaining_sound in enumerate(self.playback_queue, 1):
                            print(f"  {i}. {remaining_sound}")

    def start_playback(self):
        """Start continuous playback thread if not already running"""
        # Ensure only one playback thread is running
        if self._playback_thread and self._playback_thread.is_alive():
            return
        
        # Reset stop flag
        self._stop_playback.clear()
        
        # Start playback thread
        self._playback_thread = threading.Thread(target=self._continuous_playback)
        self._playback_thread.daemon = True  # Make thread exit when main program exits
        self._playback_thread.start()
    
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
        """Threaded method to play sounds in the queue"""
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
                logging.info("Dialogue: " + metadata.get('dialogue', ''))

                dialog = metadata.get('dialogue', '')
                if (dialog != ''):
                    generate_tts_haiku()
                
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
                
                if channel:
                    # Play the sound
                    channel.play(sound)
                else:
                    print("❗ Could not find an available channel after retries")
                    # Add sound back to queue for later playback
                    self.sound_queue.insert(0, sound_file)
                    time.sleep(0.5)
                    continue
                
                # Wait for the sound to finish or be interrupted
                start_time = time.time()
                duration = metadata.get('duration_seconds', 1)
                
                while (time.time() - start_time) < duration:
                    if self._stop_playback.is_set():
                        # Stop sound if requested
                        channel.stop()
                        break
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
        """Start continuous playback thread if not already running"""
        # Ensure only one playback thread is running
        if self._playback_thread and self._playback_thread.is_alive():
            return
        
        # Reset stop flag
        self._stop_playback.clear()
        
        # Start playback thread
        self._playback_thread = threading.Thread(target=self._continuous_playback)
        self._playback_thread.daemon = True  # Make thread exit when main program exits
        self._playback_thread.start()

    def _log_gpt_interaction(self, interaction_type: str, input_data: dict, response: str = None):
        """Log GPT interaction details"""
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