import os
import threading
import time
import pygame
import logging
import json
from drone_note_utils import send_drone_notes

class SoundPlaybackManager:
    """
    Handles all sound playback functionality including queuing and crossfading between audio files.
    """
    
    def __init__(self, audio_manager=None):
        """
        Initialize the SoundPlaybackManager
        
        :param audio_manager: AudioFileManager instance to use for loading sounds
        """
        # Store the audio manager
        self.audio_manager = audio_manager
        
        # Initialize pygame mixer if not already initialized
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
        
        # Set up mixer with enough channels
        pygame.mixer.set_num_channels(64)
        
        # Playback queue
        self.playback_queue = []
        self._playback_lock = threading.Lock()
        
        # Playback thread
        self._playback_thread = None
        self._stop_event = threading.Event()
        
        # Playback state tracking
        self._current_sound = None
        self._current_channel = None
        self._current_sound_end_time = 0
        
        # Add performance ended flag
        self._performance_ended = False
        
        # Parent score manager reference
        self.parent_score_manager = None
        
        print("Sound Playback Manager initialized")
    
    def add_to_queue(self, sound_file, priority=False):
        """
        Add a sound file to the playback queue
        
        :param sound_file: Name of the sound file
        :param priority: If True, add to the front of the queue
        """
        with self._playback_lock:
            if priority:
                self.playback_queue.insert(0, sound_file)
                print(f"🔝 Added sound to front of queue: {sound_file}")
            else:
                self.playback_queue.append(sound_file)
                print(f"🎶 Added sound to queue: {sound_file}")
    
    def clear_queue(self):
        """Clear the playback queue"""
        with self._playback_lock:
            self.playback_queue.clear()
            print("🧹 Playback queue cleared")
    
    def get_queue(self):
        """Get a copy of the current playback queue"""
        with self._playback_lock:
            return list(self.playback_queue)
    
    def start_playback(self):
        """Start continuous playback"""
        # Ensure only one playback thread is running
        if self._playback_thread and self._playback_thread.is_alive():
            return
        
        # Reset stop flag
        self._stop_event.clear()
        
        # Start playback thread
        self._playback_thread = threading.Thread(target=self._continuous_playback)
        self._playback_thread.daemon = True
        self._playback_thread.start()
        
        print("🎵 Sound playback started")
    
    def stop_playback(self):
        """Stop playback"""
        # Signal the playback thread to stop
        self._stop_event.set()
        
        # Stop all sounds
        pygame.mixer.stop()
        
        # Wait for the thread to finish
        if self._playback_thread and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=1)
        
        print("⏹️ Sound playback stopped")

    def play_sound(self, channel, sound, filename):
        """Wrapper to play a sound with proper logging"""
        print(f"▶️ Playback manager Actually playing sound: {filename}")
        channel.play(sound)
    
    def _get_current_section_name(self):
        """
        Get the current section name from the audio manager or parent score manager
        
        This method provides a way for the sound playback manager to know
        what section of the performance we're in, which helps with deciding
        whether to continue looping sounds.
        
        Returns:
            str: The current section name, or None if it can't be determined
        """
        # First try to access through a parent score manager
        try:
            if hasattr(self, 'parent_score_manager') and self.parent_score_manager:
                # Get from score manager's current section
                current_section = self.parent_score_manager._current_section
                if current_section:
                    return current_section.get("section_name")
        except:
            pass
        
        # If no parent or access failed, return None
        return None
    
    def _continuous_playback(self):
        """Continuously play sounds from the queue with crossfading"""
        # Reserve specific channels for playback
        RESERVED_CHANNELS = 16
        channels = [pygame.mixer.Channel(i) for i in range(RESERVED_CHANNELS)]
        channel_index = 0
        
        # Tracking the current playing sound
        current_channel = None
        current_sound_file = None
        current_sound_end_time = 0
        crossfade_in_progress = False
        
        # Add a flag to track if we've already logged the empty queue
        empty_queue_logged = False
        
        # Simple crossfade settings
        CROSSFADE_START = 5.0  # Start crossfade 5 seconds before end
        FADE_DURATION = 0.5    # 500ms fade duration
        
        while not self._stop_event.is_set():
            try:
                current_time = time.time()
                
                # CASE 1: Nothing is playing, start a new sound
                if current_channel is None or not current_channel.get_busy():
                    crossfade_in_progress = False
                    
                    # Check if there's anything in the queue
                    with self._playback_lock:
                        if not self.playback_queue:
                            # Log when the queue is empty
                            if not empty_queue_logged:
                                print("🔄 Queue is now empty")
                                empty_queue_logged = True
                                
                            # Handle empty queue - but don't add to queue if we're in End section
                            current_section = self._get_current_section_name()
                            if current_sound_file and current_section != "Final" and not self._performance_ended:
                                self.playback_queue.append(current_sound_file)
                            elif current_section == "Final" or self._performance_ended:
                                continue
                                # Don't add to queue
                            time.sleep(0.1)
                            continue
                        else:
                            # Reset the empty queue logged flag when we have items again
                            empty_queue_logged = False
                        
                        # Get next sound from queue
                        sound_file = self.playback_queue.pop(0)
                    
                    # Update current sound tracking
                    current_sound_file = sound_file
                    self._current_sound = sound_file
                    
                    # Load and play the sound using audio manager
                    sound = self.audio_manager.get_sound(sound_file) if self.audio_manager else None
                    if not sound:
                        print(f"⚠️ Failed to load sound: {sound_file}")
                        continue
                    
                    # Get metadata for duration from audio manager
                    duration = 30  # Default duration
                    if self.audio_manager:
                        duration = self.audio_manager.get_sound_duration(sound_file)
                        
                        try:
                            print(f"Attempting to send drone notes SOUND FILE: ${sound_file}")
                            # Import the necessary functions
                            from api_client import generate_drone_frequencies, WebAppClient
                            
                            # Attempt to send drone notes for the current sound file
                            send_drone_notes(
                                sound_file, 
                                self.audio_manager.sound_metadata, 
                                WebAppClient(), 
                                generate_drone_frequencies
                            )
                        except Exception as e:
                            print(f"❌ Error in drone note sending: {e}")
                    
                    # Set up the channel
                    current_channel = channels[channel_index]
                    self._current_channel = current_channel
                    channel_index = (channel_index + 1) % RESERVED_CHANNELS
                    
                    # Play the sound
                    current_channel.set_volume(0.8)
                    current_channel.play(sound)
                    
                    # Calculate end time
                    current_sound_end_time = current_time + duration
                    self._current_sound_end_time = current_sound_end_time
                    
                    print(f"▶️ +++++ Playing: {sound_file} (duration: {duration:.1f}s)")
                    
                    # Print remaining queue
                    with self._playback_lock:
                        if self.playback_queue:
                            print(f"Queue: {', '.join(self.playback_queue)}")
                
                # CASE 2: Sound is playing, check if we need to start crossfade
                elif current_channel.get_busy() and not crossfade_in_progress:
                    time_remaining = current_sound_end_time - current_time
                    
                    if time_remaining <= CROSSFADE_START:
                        # Start crossfade process
                        crossfade_in_progress = True
                        
                        # Check if there's a next sound in the queue
                        with self._playback_lock:
                            # If queue is empty and we're not stopping, add current sound back for looping
                            # But don't add if we're in End section
                            current_section = self._get_current_section_name()
                            if not self.playback_queue and current_sound_file:
                                # Log when the queue is empty during crossfade check
                                if not empty_queue_logged:
                                    print("🔄 Queue is empty during crossfade check")
                                    empty_queue_logged = True
                                
                                # Only add back to queue if not in Final section
                                if current_section != "Final" and not self._performance_ended:
                                    self.playback_queue.append(current_sound_file)
                                else:
                                    continue
                                    # Don't add to queue
                            else:
                                # Reset the empty queue logged flag when we have items again
                                empty_queue_logged = False
                            
                            # Still nothing in queue? Skip crossfade
                            if not self.playback_queue:
                                crossfade_in_progress = False
                                continue
                            
                            # Get next sound filename
                            next_sound_file = self.playback_queue[0]
                        
                        # Load the next sound using audio manager
                        next_sound = self.audio_manager.get_sound(next_sound_file) if self.audio_manager else None
                        if not next_sound:
                            # Failed to load next sound, try again next cycle
                            crossfade_in_progress = False
                            continue
                        
                        # Choose the next channel
                        next_channel_index = (channel_index + 1) % RESERVED_CHANNELS
                        next_channel = channels[next_channel_index]
                        
                        # Stop any sound on the next channel
                        if next_channel.get_busy():
                            next_channel.stop()
                        
                        # Start crossfade
                        next_channel.set_volume(0.0)  # Start silent
                        next_channel.play(next_sound)
                        print(f"▶️ Playing: {next_sound_file} (duration: {duration:.1f}s)")
                        
                        # Create a separate thread for the fade
                        threading.Thread(
                            target=self._perform_crossfade,
                            args=(current_channel, next_channel, next_sound_file, next_channel_index, FADE_DURATION),
                            daemon=True
                        ).start()
                        
                        # Update channel index for next use
                        channel_index = (next_channel_index + 1) % RESERVED_CHANNELS
                
                # Sleep to avoid consuming too much CPU
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error in playback: {e}")
                time.sleep(0.5)
    
    def _perform_crossfade(self, current_channel, next_channel, next_sound_file, next_channel_index, fade_duration):
        """Perform crossfade in a separate thread to avoid audio hiccups"""
        try:
            print(f"🔀 Starting crossfade to: {next_sound_file}")
            # Start by making sure the new sound is playing silently
            # and wait a moment for it to stabilize
            next_channel.set_volume(0.0)
            time.sleep(0.05)  # Small buffer time
            
            # Define fewer steps for smoother transition
            steps = 10  # Using fewer, more spaced out steps
            step_time = fade_duration / steps
            
            # Pre-calculate all volume levels to minimize calculations during crossfade
            fade_out_volumes = [max(0, 0.8 * (1 - (i/steps))) for i in range(steps+1)]
            fade_in_volumes = [min(0.8, 0.8 * (i/steps)) for i in range(steps+1)]
            
            # Execute the crossfade with pre-calculated values
            for i in range(steps+1):
                if self._stop_event.is_set():
                    break
                    
                # Set volumes with pre-calculated values
                current_channel.set_volume(fade_out_volumes[i])
                next_channel.set_volume(fade_in_volumes[i])
                
                # Use a longer sleep between steps
                time.sleep(step_time)
            
            # Ensure final volumes are correct
            current_channel.set_volume(0)
            next_channel.set_volume(0.8)
            
            # Update tracking variables and clean up
            # Rest of the function remains the same...
        
        except Exception as e:
            print(f"Error during crossfade: {e}")
        finally:
            print(f"✅ Crossfade completed for: {next_sound_file}")
    
    def print_channel_status(self):
        """Print status of all audio channels for debugging"""
        print("\n🔊 CHANNEL STATUS REPORT:")
        print(f"Total channels: {pygame.mixer.get_num_channels()}")
        
        busy_channels = 0
        for i in range(pygame.mixer.get_num_channels()):
            channel = pygame.mixer.Channel(i)
            is_busy = channel.get_busy()
            volume = channel.get_volume()
            
            if is_busy:
                busy_channels += 1
                print(f"  Channel {i}: BUSY (vol={volume:.2f})")
        
        print(f"Busy channels: {busy_channels}/{pygame.mixer.get_num_channels()} ({busy_channels/pygame.mixer.get_num_channels()*100:.1f}%)")
        print(f"Current sound: {self._current_sound}")
        
        # Print remaining time if a sound is playing
        if self._current_sound_end_time > 0:
            remaining = self._current_sound_end_time - time.time()
            print(f"Remaining time: {remaining:.1f}s")
        
        # Print queue contents
        print("Queue contents:")
        with self._playback_lock:
            for i, sound in enumerate(self.playback_queue):
                print(f"  {i+1}. {sound}")
        
        print("-" * 40)