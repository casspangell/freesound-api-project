import os
import json
import time
import pygame
import logging
import threading

class AudioFileManager:
    """
    Manages audio files, including loading, caching, and metadata handling.
    Responsible for the filesystem interactions of the audio system.
    """
    
    def __init__(self, base_sound_path='data/sound_files', metadata_path='data/sound_files.json'):
        """
        Initialize the AudioFileManager
        
        :param base_sound_path: Base directory for sound files
        :param metadata_path: Path to the JSON file containing sound file metadata
        """
        # Initialize sound cache
        self._sound_cache = {}
        
        # Base path for sound files
        self.base_sound_path = base_sound_path
        
        # Sound metadata
        self.sound_metadata = {}
        self._load_sound_metadata(metadata_path)
        
        # Initialize pygame mixer if not already initialized
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
        
        # Background loading queue and thread
        self._load_sound_queue = []
        self._load_sound_lock = threading.Lock()
        self._load_sound_thread = None
        self._load_sound_stop_event = threading.Event()
        
        # Start the background sound loading thread
        self._start_sound_loader_thread()
        
        print(f"Audio File Manager initialized with {len(self.sound_metadata)} sound files")
    
    def _load_sound_metadata(self, metadata_path):
        """Load sound files metadata from JSON"""
        # Possible paths for sound files JSON
        possible_paths = [
            metadata_path,
            os.path.join(os.path.dirname(__file__), metadata_path),
            os.path.join(os.path.dirname(__file__), 'data/sound_files.json'),
            '/data/sound_files.json',
            'sound_files.json'
        ]
        
        for path in possible_paths:
            try:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        self.sound_metadata = json.load(f)
                        print(f"✅ Loaded sound files metadata from {path}")
                        return
            except Exception as e:
                print(f"❌ Error trying to load sound files from {path}: {e}")
        
        print("❌ ERROR: Could not find sound_files.json")
    
    def _start_sound_loader_thread(self):
        """Start the background sound loading thread"""
        if self._load_sound_thread and self._load_sound_thread.is_alive():
            return
        
        self._load_sound_stop_event.clear()
        self._load_sound_thread = threading.Thread(target=self._background_sound_loader)
        self._load_sound_thread.daemon = True
        self._load_sound_thread.start()
        print("🎵 Background sound loader thread started")
    
    def _background_sound_loader(self):
        """Background thread that loads sounds without blocking audio playback"""
        while not self._load_sound_stop_event.is_set():
            try:
                # Get a sound filename to load, if any
                filename = None
                with self._load_sound_lock:
                    if self._load_sound_queue:
                        filename = self._load_sound_queue.pop(0)
                
                # If no sound to load, sleep and continue
                if not filename:
                    time.sleep(0.1)
                    continue
                
                # Check if already in cache
                with self._load_sound_lock:
                    if filename in self._sound_cache:
                        # Already loaded
                        continue
                
                # Get path for the sound
                path = self._get_sound_path(filename)
                
                # Load the sound if path exists
                if path and os.path.exists(path):
                    try:
                        sound = pygame.mixer.Sound(path)
                        with self._load_sound_lock:
                            self._sound_cache[filename] = sound
                    except Exception:
                        # Silent error handling to avoid interrupting audio
                        pass
            
            except Exception:
                # Silent error handling
                time.sleep(0.2)

    
    def stop_background_loader(self):
        """Stop the background sound loading thread"""
        if self._load_sound_thread and self._load_sound_thread.is_alive():
            self._load_sound_stop_event.set()
            self._load_sound_thread.join(timeout=1)
            print("Background sound loader stopped")
    
    def preload_all_sounds(self):
        """Preload all sound files into the cache"""
        total_sounds = len(self.sound_metadata)
        loaded_count = 0
        failed_count = 0
        
        print(f"🔄 Preloading {total_sounds} sound files...")
        
        # Track preloading progress
        start_time = time.time()
        
        for filename in self.sound_metadata.keys():
            try:
                # Add to the loading queue with highest priority
                with self._load_sound_lock:
                    if filename not in self._sound_cache and filename not in self._load_sound_queue:
                        self._load_sound_queue.insert(0, filename)
                        loaded_count += 1
                
                # Print progress occasionally
                if loaded_count % 20 == 0 or loaded_count == total_sounds:
                    print(f"⏳ Queued {loaded_count}/{total_sounds} sounds for loading...")
            except Exception as e:
                print(f"❌ Error queueing {filename}: {e}")
                failed_count += 1
        
        # Report queuing results
        print(f"✅ All sounds queued for loading ({loaded_count} sounds)")
        
        # Wait for some critical sounds to be fully loaded before returning
        critical_sounds = ["intro.mp3", "end_transition.mp3", "end_1.mp3"]
        
        # Wait up to 5 seconds for critical sounds to load
        wait_start = time.time()
        while time.time() - wait_start < 5.0:
            # Check if all critical sounds are loaded
            with self._load_sound_lock:
                missing = [s for s in critical_sounds if s not in self._sound_cache]
                if not missing:
                    break
            
            # Wait a bit before checking again
            time.sleep(0.1)
        
        # Report loading status
        with self._load_sound_lock:
            current_loaded = len(self._sound_cache)
            remaining = len(self._load_sound_queue)
        
        print(f"💿 Initial loading complete: {current_loaded} loaded, {remaining} queued")
        
        # Return immediately - loading will continue in background
        return {
            "total": total_sounds,
            "loaded": current_loaded,
            "queued": remaining
        }
    
    def get_sound(self, filename):
        """
        Get a sound from the cache or load it if not cached
        
        :param filename: Name of the sound file
        :return: pygame.mixer.Sound object or None if not found
        """
        if filename is None:
            return None
        
        # Check cache first - with proper locking
        with self._load_sound_lock:
            if filename in self._sound_cache:
                return self._sound_cache[filename]
            
            # If not in cache, add to the background loading queue
            if filename not in self._load_sound_queue:
                self._load_sound_queue.append(filename)
        
        # Check cache again, maybe the background thread loaded it
        with self._load_sound_lock:
            if filename in self._sound_cache:
                return self._sound_cache[filename]
        
        # If we get here, the sound isn't loaded yet
        # Try to load it directly as a last resort
        path = self._get_sound_path(filename)
        if path and os.path.exists(path):
            try:
                sound = pygame.mixer.Sound(path)
                with self._load_sound_lock:
                    self._sound_cache[filename] = sound
                return sound
            except Exception:
                pass
                
        return None
    
    def _get_sound_path(self, filename):
        """
        Get the file path for a sound file
        
        :param filename: Name of the sound file
        :return: Full path to the sound file or None if not found
        """
        # Determine section from metadata
        section = None
        if filename in self.sound_metadata:
            section = self.sound_metadata[filename].get('section')
        
        # If section not found, use default mappings
        if not section:
            if filename.startswith("1-"):
                section = "Rising Action"
            elif filename.startswith("2-"):
                section = "Middle"
            elif filename.startswith("3-"):
                section = "Climactic"
            elif filename.startswith("bridge_"):
                section = "Bridge"
            elif filename.startswith("falling"):
                section = "Falling Voices"
            elif filename.startswith("end-"):
                section = "End"
            elif filename == "end_transition.mp3":
                section = "End"
            else:
                section = "Intro"
        
        # Use a single, consistent path format
        path = os.path.join(self.base_sound_path, section, filename)
        print(f"Soundfile path: {path}")
        # Check if file exists
        if os.path.exists(path):
            return path
        
        # If not found, try a few common alternatives
        alternatives = [
            os.path.join(self.base_sound_path, "End", filename),
            os.path.join(self.base_sound_path, "Intro", filename),
            os.path.join(self.base_sound_path, filename)
        ]
        
        for alt_path in alternatives:
            if os.path.exists(alt_path):
                print(f"⚠️ Found sound in alternative location: {alt_path}")
                return alt_path
        
        # Not found anywhere
        return None
    
    def get_sound_metadata(self, filename):
        """
        Get metadata for a sound file
        
        :param filename: Name of the sound file
        :return: Dictionary of metadata or empty dict if not found
        """
        return self.sound_metadata.get(filename, {})
    
    def get_sound_section(self, filename):
        """
        Get the section for a sound file
        
        :param filename: Name of the sound file
        :return: Section name or None if not found
        """
        # Check metadata first
        if filename in self.sound_metadata:
            return self.sound_metadata[filename].get('section')
        
        # If not in metadata, use default mappings
        if filename.startswith("1-"):
            return "Rising Action"
        elif filename.startswith("2-"):
            return "Middle"
        elif filename.startswith("3-"):
            return "Climactic"
        elif filename.startswith("bridge"):
            return "Bridge"
        elif filename.startswith("falling"):
            return "Falling Voices"
        elif filename.startswith("end_"):
            return "Falling Action"
        elif filename == "end_transition.mp3":
            return "End"
        elif filename == "end_1.mp3":
            return "Falling Action"
        else:
            return "Intro"
    
    def get_sound_duration(self, filename):
        """
        Get the duration of a sound file
        
        :param filename: Name of the sound file
        :return: Duration in seconds or default 30 seconds if not found
        """
        # Check metadata first
        if filename in self.sound_metadata:
            return self.sound_metadata[filename].get('duration_seconds', 30)
        
        # If not in metadata, try to get from the sound object
        sound = self.get_sound(filename)
        if sound:
            try:
                return sound.get_length()
            except:
                pass
        
        # Default duration if all else fails
        return 30
    
    def get_all_sounds_by_section(self, section):
        """
        Get all sound files in a specific section
        
        :param section: Section name
        :return: List of sound filenames
        """
        return [
            filename for filename, metadata in self.sound_metadata.items()
            if metadata.get('section') == section
        ]
    
    def clear_cache(self):
        """Clear the sound cache to free memory"""
        with self._load_sound_lock:
            self._sound_cache.clear()
        print("🧹 Sound cache cleared")