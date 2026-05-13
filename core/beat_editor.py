import numpy as np


# -----------------------------
# AUDIO ENERGY ANALYSIS
# -----------------------------
def analyze_audio_beats(audio_path, sample_rate=22050, frame_size=2048):
    """
    Extracts simple energy peaks from audio.
    Used to align cuts with speech emphasis.
    """

    try:
        import librosa
    except ImportError:
        raise ImportError("Install librosa: pip install librosa")

    y, sr = librosa.load(audio_path, sr=sample_rate)

    # energy curve
    energy = np.abs(librosa.stft(y, n_fft=frame_size))
    energy = np.mean(energy, axis=0)

    # normalize
    energy = (energy - np.min(energy)) / (np.max(energy) - np.min(energy) + 1e-6)

    # detect peaks
    peaks = []
    threshold = 0.6

    for i, e in enumerate(energy):
        if e > threshold:
            time = librosa.frames_to_time(i, sr=sr, hop_length=frame_size)
            peaks.append(round(float(time), 2))

    return peaks


# -----------------------------
# CUT POINT GENERATOR
# -----------------------------
def generate_cut_points(audio_path, min_gap=1.5):
    """
    Converts energy peaks into usable video cut points.
    """

    peaks = analyze_audio_beats(audio_path)

    cut_points = []
    last = 0

    for p in peaks:
        if p - last >= min_gap:
            cut_points.append(p)
            last = p

    return cut_points