from openai import OpenAI
import config
import pygame
import os
import requests
import time
import json
from api_client import WebAppClient

# Initialize OpenAI client with API Key
client = OpenAI(api_key=config.CHAT_API_KEY)

# Initialize the webapp client
webapp_client = WebAppClient(base_url="http://localhost:3000")

# Function to generate AI haiku and convert it to speech
def generate_tts_haiku(word):
    try:
        # Generate AI haiku
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a text-to-speech processor. Repeat back the text."},
                {"role": "user", "content": f"{word}"}
            ]
        )
        haiku = response.choices[0].message.content.strip()
        print(f"\n🌿 Haiku: {haiku} 🌿\n")

        # Save the haiku to the log file
        os.makedirs('haiku_sounds', exist_ok=True)  # Ensure directory exists
        with open('haiku_sounds/haiku.txt', 'a', encoding='utf-8') as file:
            file.write(f"{int(time.time())}: {haiku}\n")

        # Convert haiku to speech
        speech_response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=haiku
        )
        
        # Generate a safe filename
        safe_word = ''.join(c for c in word[:20] if c.isalnum() or c.isspace()).strip().replace(' ', '_')
        if not safe_word:
            safe_word = "dialogue"
        
        tts_file = f"haiku_sounds/{safe_word}_{int(time.time())}.mp3"
        speech_response.stream_to_file(tts_file)

        # Play the haiku audio locally at lower volume
        # sound = pygame.mixer.Sound(tts_file)
        # channel = pygame.mixer.find_channel()
        # if channel:
        #     channel.set_volume(0.4)  # Set volume to 0.6 (60%)
        #     channel.play(sound)
        # else:
        #     print("⚠️ No available channel for TTS playback")
            
        # Send the audio file to the Node.js webapp
        send_haiku_to_webapp(tts_file)

    except Exception as e:
        print("⚠️ Error generating or playing AI haiku:", e)

def generate_transmission_intro():
    try:
        intro_text = """
[dramatic tone, slow pace] Welcome. [long pause] You are entering a space shaped not by time,.. but by memory. [medium pause] This is,.. [medium pause] Transmission. [long pause] A living system—built from thought, carried by sound, guided by you... [medium pause] At its core lives an algorithm which is called The Ashari. [longer pause] Not a person, not a place. [short pause] But a culture— [short dramatic pause] invented, wounded, surviving. [medium pause] Each word you type alters them. [short pause] They remember... They shift... They become. [medium pause] The Ashari uses AI to feel. [short pause] To translate emotion into sound. [short pause] To echo what it means to remember... together. [medium pause] What you hear is not static. [short pause] It is alive. [short pause] Composed by many minds,.. becoming one. [longer pause] This,.. [longer pause] is,.................[longer pause]  [slow pace] Transmission.

""".strip()

#         intro_text = """
# Welcome. You are entering a space not bound by time, but by memory. This is Transmission—a living performance shaped by thought. Every sound, every movement you hear tonight emerges from a collective process—one that listens, remembers, and evolves.

# At the heart of this work is an algorithm. Its name is The Ashari. The Ashari is not a person, not a place—but a culture born from fiction, shaped by emotion, and guided by every word you type.

# They remember betrayal. They hold onto resilience. And with every letter entered, their worldview shifts.

# Behind this shifting memory is an AI—a system that interprets the emotional weight of your input, responding in real time with evolving sound, movement, and atmosphere.

# The Ashari do not simply store data. They feel its impact. The algorithm becomes their memory. Each new word, a ripple through their culture. Each typed thought, a change in how they see the world.

# This AI is not here to replace human expression. It is here to translate it—into presence, into experience.

# What you hear tonight is not static. It is alive. Each participant shapes the collective mind of many.

# Many minds. Composing consciousness........... This is Transmission.
# """.strip()

        # Generate TTS from the full introduction
        speech_response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=intro_text
        )

        # Save the file
        filename = f"haiku_sounds/transmission_intro_{int(time.time())}.mp3"
        speech_response.stream_to_file(filename)
        print(f"✅ Transmission intro saved to: {filename}")

        # Optionally upload
        send_haiku_to_webapp(filename, "Welcome")

    except Exception as e:
        print("⚠️ Error generating or playing Transmission intro:", e)


# Add this to your haiku.py file

# def generate_transmission_intro(completion_callback=None):
#     """
#     Generate and play the transmission intro audio.
    
#     Args:
#         completion_callback (callable, optional): Function to call when audio upload is complete
#     """
#     try:
#         intro_text = """
# [dramatic tone, slow pace] Welcome. [long pause] You are entering a space shaped not by time,.. but by memory. [medium pause] This is,.. [medium pause] Transmission. [long pause] A living system—built from thought, carried by sound, guided by you... [medium pause] At its core lives an algorithm which is called The Ashari. [longer pause] Not a person, not a place. [short pause] But a culture— [short dramatic pause] invented, wounded, surviving. [medium pause] Each word you type alters them. [short pause] They remember... They shift... They become. [medium pause] The Ashari uses AI to feel. [short pause] To translate emotion into sound. [short pause] To echo what it means to remember... together. [medium pause] What you hear is not static. [short pause] It is alive. [short pause] Composed by many minds,.. becoming one. [longer pause] This,.. [longer pause] is,.................[longer pause]  [slow pace] Transmission.
# """.strip()

#         # Generate TTS from the full introduction
#         speech_response = client.audio.speech.create(
#             model="tts-1",
#             voice="alloy",
#             input=intro_text
#         )

#         # Save the file
#         filename = f"haiku_sounds/transmission_intro_{int(time.time())}.mp3"
#         speech_response.stream_to_file(filename)
#         print(f"✅ Transmission intro saved to: {filename}")

#         # Send to webapp and call the completion callback when done
#         send_haiku_to_webapp(filename, "Welcome", completion_callback)

#     except Exception as e:
#         print("⚠️ Error generating or playing Transmission intro:", e)
#         # Call the callback even if there's an error
#         if completion_callback:
#             completion_callback()

def send_haiku_to_webapp(audio_file, title, completion_callback=None):
    """
    Send the generated haiku MP3 to the webapp
    
    Args:
        audio_file (str): Path to the MP3 file
        title (str): Title for the audio file
        completion_callback (callable, optional): Function to call when upload is complete
    """
    try:
        if not os.path.exists(audio_file):
            print("haiku_sounds directory not found")
            if completion_callback:
                completion_callback()
            return
        
        metadata = {
            'title': title,
            'description': "This is a test upload",
            'timestamp': str(int(time.time())),
            'prompt': "test",
            'source': 'test_script',
            'playback_volume': 0.2
        }
        
        try:
            print(f"Attempting to upload audio file: {audio_file}")
            
            # Verify file exists and is readable
            if not os.path.exists(audio_file):
                print(f"Error: File does not exist: {audio_file}")
                if completion_callback:
                    completion_callback()
                return
                
            file_size = os.path.getsize(audio_file)
            print(f"File size: {file_size} bytes")
            
            # Send the file to the webapp
            response = webapp_client.send_audio_file('api/audio-upload', audio_file, metadata)
            
            if response and response.get('status') == 'success':
                print(f"✅ Successfully uploaded test audio: {response.get('file', {}).get('url', '')}")
            else:
                print(f"⚠️ Error uploading test audio: {response}")
            
            # After upload is complete, call the completion callback if provided
            if completion_callback:
                completion_callback()
                
        except Exception as e:
            print(f"⚠️ Exception during test: {e}")
            import traceback
            traceback.print_exc()
            # Call the callback even if there's an error
            if completion_callback:
                completion_callback()
            
    except Exception as e:
        print(f"⚠️ Error sending haiku to webapp: {e}")
        # Call the callback even if there's an error
        if completion_callback:
            completion_callback()