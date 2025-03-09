import os
import numpy as np
import scipy.io.wavfile as wavfile
from ashari import Ashari  # Import Ashari system

# Initialize Ashari instance
ashari = Ashari()
ashari.load_state()  # Load Ashari's memory

def generate_sine_wave(frequencies, duration=2.0, sampling_rate=44100):
    """
    Generates a sine wave for multiple frequencies to create a chord.

    Args:
        frequencies (list): List of frequencies for the chord.
        duration (float): Duration of the sound in seconds.
        sampling_rate (int): Audio sampling rate.

    Returns:
        np.ndarray: Waveform as a NumPy array.
    """
    t = np.linspace(0, duration, int(sampling_rate * duration), endpoint=False)
    waveform = np.zeros_like(t)  # Start with silence

    # Add each frequency to the waveform
    for freq in frequencies:
        waveform += 0.5 * np.sin(2 * np.pi * freq * t)

    # Normalize waveform
    waveform /= np.max(np.abs(waveform))

    return waveform

def generate_vocal_score(word, duration=2.0):
    """
    Generates a jungle-inspired harmonic progression based on Ashari's sentiment score.

    Args:
        word (str): Input word to determine harmony.
        duration (float): Duration of the generated sound in seconds.

    Returns:
        str: Path to the generated vocal score audio file.
    """

    # Retrieve sentiment score from Ashari
    sentiment_data = ashari.process_word(word)
    sentiment_score = sentiment_data.get("sentiment_score", 0.0)

    # 🎵 Jungle-Inspired Harmonic Mapping
    if sentiment_score <= -0.5:
        frequencies = [196, 220, 247]  # Amazonian Shamanic (i → iv → v in A minor)
        chord_name = "Amazonian Shamanic (Am → Dm → Em)"
    elif -0.5 < sentiment_score <= 0.0:
        frequencies = [262, 330, 392, 440]  # Central African Pygmy (I → vi → IV → V in C Major)
        chord_name = "Central African Pygmy (C → Am → F → G)"
    elif 0.0 < sentiment_score <= 0.5:
        frequencies = [220, 294, 349, 392]  # Afro-Brazilian Jungle (ii → V → I → IV in G Major)
        chord_name = "Afro-Brazilian Jungle (Am → D → G → C)"
    else:
        frequencies = [196, 247, 294, 330]  # Peruvian Amazonian Folk (I → V7 → vi → IV in G Major)
        chord_name = "Peruvian Amazonian Folk (G → D7 → Em → C)"

    # ✅ Generate Chord as a Waveform
    waveform = generate_sine_wave(frequencies, duration)

    # ✅ Ensure the output directory exists
    output_dir = "generated_audio"
    os.makedirs(output_dir, exist_ok=True)

    # Save as WAV file
    output_filename = os.path.join(output_dir, f"vocal_score_{word}.wav")
    wavfile.write(output_filename, 44100, (waveform * 32767).astype(np.int16))

    print(f"Generated vocal score for '{word}' → {chord_name} ({frequencies} Hz).")

    os.system(f"afplay '{output_filename}'" if "darwin" in os.sys.platform else f"aplay '{output_filename}'")

    return output_filename

# Example Usage
word = "war"  # Change this to test different words
file_path = generate_vocal_score(word)
print(f"Download: {file_path}")
