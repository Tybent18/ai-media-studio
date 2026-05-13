import numpy as np


# -----------------------------
# MUSIC ENERGY ANALYSIS
# -----------------------------
def analyze_music_energy(audio_path):

    try:
        import librosa
    except:
        raise ImportError("pip install librosa")

    y, sr = librosa.load(audio_path)

    # energy curve
    energy = np.abs(librosa.stft(y))
    energy = np.mean(energy, axis=0)

    energy = (energy - np.min(energy)) / (np.max(energy) + 1e-6)

    return energy


# -----------------------------
# BEAT CUT POINTS
# -----------------------------
def generate_music_cut_points(audio_path, threshold=0.65):

    try:
        import librosa
    except:
        raise ImportError("pip install librosa")

    y, sr = librosa.load(audio_path)

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    peaks = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)

    times = librosa.frames_to_time(peaks, sr=sr)

    return [round(t, 2) for t in times]


# -----------------------------
# PACE MAPPER (VERY IMPORTANT)
# -----------------------------
def map_music_to_pacing(audio_path):

    energy = analyze_music_energy(audio_path)
    avg = float(np.mean(energy))

    if avg > 0.6:
        return "fast"
    elif avg < 0.3:
        return "slow"
    return "medium"