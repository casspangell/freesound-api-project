import numpy as np
import scipy.io.wavfile as wavfile
import os
from ashari import Ashari  # Import Ashari system

# Initialize Ashari instance
ashari = Ashari()
ashari.load_state()  # Load Ashari's memory

def generate_sine_wave(frequency, duration=2.0, sampling_rate=44100):

    sampling_rate = 44100  # Hz
    duration = 2.0  # seconds
    frequency = 220  # Hz (A3)

    t = np.linspace(0, duration, int(sampling_rate * duration), endpoint=False)
    waveform = 0.5 * np.sin(2 * np.pi * frequency * t)  # Pure tone
    return waveform

def generate_sine_wave_chord(frequencies, duration=2.0, sampling_rate=44100):

    t = np.linspace(0, duration, int(sampling_rate * duration), endpoint=False)
    waveform = np.zeros_like(t)  # Start with silence

    # Add each frequency to the waveform
    for freq in frequencies:
        waveform += 0.5 * np.sin(2 * np.pi * freq * t)

    # Normalize waveform
    waveform /= np.max(np.abs(waveform))

    return waveform


# # Save as WAV file
# output_filename = "A3_sine.wav"
# wavfile.write(output_filename, sampling_rate, waveform_int16)
# os.system("afplay A3_sine.wav")

# print(f"Audio file saved as {output_filename}. Play it with any audio player.")

def generate_vocal_score(word, duration=2.0):

    # Retrieve sentiment score from Ashari
    sentiment_data = ashari.process_word(word)
    sentiment_score = sentiment_data.get("sentiment_score", 0.0)

    if sentiment_score <= -0.5:
        frequencies = [196, 233, 294]  # G Minor (G3, Bb3, D4)
        chord_name = "G Minor"
    elif -0.5 < sentiment_score <= 0.0:
        frequencies = [220, 294, 330]  # A Suspended (A3, D4, E4)
        chord_name = "A Suspended"
    elif 0.0 < sentiment_score <= 0.5:
        frequencies = [261, 330, 392]  # C Major (C4, E4, G4)
        chord_name = "C Major"
    else:
        frequencies = [175, 220, 261, 330]  # F Major 7th (F3, A3, C4, E4)
        chord_name = "F Major 7th"

    # Generate sine wave for the mapped pitch
    sampling_rate=44100
    waveform = generate_sine_wave_chord(frequencies, duration, sampling_rate)

    # ✅ Ensure the output directory exists
    output_dir = "generated_audio"
    os.makedirs(output_dir, exist_ok=True)

    # Save as WAV file
    output_filename = os.path.join(output_dir, f"vocal_score_{word}.wav")
    wavfile.write(output_filename, sampling_rate, (waveform * 32767).astype(np.int16))

    print(f"Generated vocal score for '{word}' with frequency {frequencies} Hz.")
    os.system(f"afplay '{output_filename}'")
    return output_filename

# Example Usage
word = "hope"  # Change this to test different words
file_path = generate_vocal_score(word)
print(f"Download: {file_path}")
