import os
import numpy as np
import scipy.io.wavfile as wavfile
from ashari import Ashari  # Import Ashari system

# Initialize Ashari instance
ashari = Ashari()
ashari.load_state()  # Load Ashari's memory

def generate_rhythm(word, duration=8.0, loop_count=2, sampling_rate=44100):
    """
    Generates a looping rhythmic drum pattern using 'shaman-drum.wav' based on Ashari's sentiment score.

    Args:
        word (str): Input word to determine rhythm.
        duration (float): Duration of the rhythm in seconds (per loop).
        loop_count (int): Number of times to loop the rhythm.
        sampling_rate (int): Audio sampling rate.

    Returns:
        str: Path to the generated looping drum rhythm audio file.
    """

    # Load the shaman drum sample
    drum_sample_path = "rhythms/shaman-drum.wav"
    if not os.path.exists(drum_sample_path):
        raise FileNotFoundError(f"Drum sample '{drum_sample_path}' not found!")

    # Read drum sample
    drum_sr, drum_sample = wavfile.read(drum_sample_path)

    # Ensure the drum sample is stereo-compatible
    if len(drum_sample.shape) == 1:  # Mono
        drum_sample = np.expand_dims(drum_sample, axis=1)

    # Retrieve sentiment score from Ashari
    sentiment_data = ashari.process_word(word)
    sentiment_score = sentiment_data.get("sentiment_score", 0.0)

    # 🎵 Rhythm Mapping 🎵
    if sentiment_score <= -0.5:
        rhythm_pattern = [1, 0, 0, 0, 1] 
    elif -0.5 < sentiment_score <= 0.0:
        rhythm_pattern = [1, 0, 0, 1, 0, 0]
    elif 0.0 < sentiment_score <= 0.5:
        rhythm_pattern = [1, 1, 1, 1]
    else:
        rhythm_pattern = [1, 1, 1, 1]

    # Determine beat spacing based on pattern length
    beats_per_second = len(rhythm_pattern) / duration
    beat_spacing = int(sampling_rate / beats_per_second)

    # Create silence for the full duration including loops
    total_samples = int(sampling_rate * duration * loop_count)
    rhythm_waveform = np.zeros((total_samples, drum_sample.shape[1]))

    # Place drum hits according to the rhythm pattern, looping it
    for loop in range(loop_count):  # Loop multiple times
        for i, hit in enumerate(rhythm_pattern):
            if hit == 1:
                start_idx = loop * int(sampling_rate * duration) + i * beat_spacing
                end_idx = start_idx + len(drum_sample)
                if end_idx < total_samples:
                    rhythm_waveform[start_idx:end_idx] += drum_sample[: end_idx - start_idx]

    # Normalize waveform to avoid clipping
    rhythm_waveform /= np.max(np.abs(rhythm_waveform))

    # ✅ Ensure the output directory exists
    output_dir = "generated_rhythms"
    os.makedirs(output_dir, exist_ok=True)

    # Save as WAV file
    output_filename = os.path.join(output_dir, f"rhythm_{word}_loop.wav")
    wavfile.write(output_filename, sampling_rate, (rhythm_waveform * 32767).astype(np.int16))

    print(f"Generated looping rhythm for '{word}' → {rhythm_pattern}.")

    # ✅ Play the file immediately
    os.system(f"afplay '{output_filename}'" if "darwin" in os.sys.platform else f"aplay '{output_filename}'")

    return output_filename  # Return file path

# Example Usage
word = "joy"  # Change this to test different words
file_path = generate_rhythm(word, loop_count=3)  # Looping the rhythm 3 times
print(f"Download: {file_path}")
