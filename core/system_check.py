import subprocess
import sys
import os
import importlib


# =========================================================
# 🔧 SELF-HEALING UTILITIES
# =========================================================

def _run_pip_install(package):
    """
    Installs missing Python packages automatically.
    """
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", package],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except Exception:
        return False


def _ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        return True
    return True


def _safe_import(module_name, pip_name=None):
    """
    Try import, auto-install if missing.
    """
    try:
        importlib.import_module(module_name)
        return True

    except ImportError:
        if pip_name:
            print(f"⚠️ Missing {module_name}, installing {pip_name}...")
            if _run_pip_install(pip_name):
                try:
                    importlib.import_module(module_name)
                    return True
                except:
                    return False

        return False


# =========================================================
# 🧠 CORE CHECKS
# =========================================================

def check_python():
    return sys.version_info >= (3, 9)


def check_ffmpeg():
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.returncode == 0 and "ffmpeg" in result.stdout.lower()
    except FileNotFoundError:
        return False


def check_moviepy():
    return _safe_import("moviepy.editor", "moviepy")


def check_edge_tts():
    return _safe_import("edge_tts", "edge-tts")


def check_audio_libs():
    ok1 = _safe_import("librosa", "librosa")
    ok2 = _safe_import("numpy", "numpy")
    return ok1 and ok2


def check_requests():
    return _safe_import("requests", "requests")


# =========================================================
# 📁 FILE SYSTEM HEALER
# =========================================================

def check_file_system():

    required_dirs = [
        "assets",
        "assets/audio",
        "assets/broll",
        "assets/avatars",
        "output",
        "memory",
        "images"
    ]

    for d in required_dirs:
        _ensure_dir(d)

    # test write
    try:
        test_path = "output/_write_test.txt"
        with open(test_path, "w") as f:
            f.write("ok")
        os.remove(test_path)
        return True

    except Exception as e:
        print("❌ File system write error:", e)
        return False


# =========================================================
# 🧪 FFmpeg AUTO-RECOVERY HINT
# =========================================================

def check_ffmpeg():
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ FFmpeg missing.")
        print("👉 Install: https://ffmpeg.org/download.html")
        return False


# =========================================================
# 🚀 SELF-HEALING ENGINE
# =========================================================

def run_system_check(auto_heal=True):

    print("\n🧠 SELF-HEALING AI VIDEO ENGINE CHECK v4\n")

    checks = {
        "Python >= 3.9": check_python(),
        "FFmpeg": check_ffmpeg(),
        "MoviePy": check_moviepy(),
        "Edge-TTS": check_edge_tts(),
        "Audio libs": check_audio_libs(),
        "Requests": check_requests(),
        "File system": check_file_system(),
    }

    passed = 0
    total = len(checks)

    for name, result in checks.items():
        status = "✅ OK" if result else "❌ FAIL"
        print(f"{name}: {status}")

        if result:
            passed += 1

    score = (passed / total) * 100

    print(f"\n📊 System Readiness: {score:.0f}%")

    # =====================================================
    # 🧠 AUTO-HEALING LOOP
    # =====================================================
    if score < 100 and auto_heal:

        print("\n🛠️ Attempting self-healing...\n")

        # re-run checks after healing attempts
        checks["MoviePy"] = check_moviepy()
        checks["Edge-TTS"] = check_edge_tts()
        checks["Audio libs"] = check_audio_libs()
        checks["Requests"] = check_requests()
        checks["File system"] = check_file_system()

        passed = sum(1 for v in checks.values() if v)
        score = (passed / total) * 100

        print(f"\n🔄 Post-heal readiness: {score:.0f}%")

    # =====================================================
    # FINAL DECISION
    # =====================================================
    if score < 100:
        print("\n❌ SYSTEM NOT READY")
        print("👉 Manual fixes required (FFmpeg or Python environment issue)\n")
        return False

    print("\n🚀 SYSTEM READY — FULLY SELF-HEALED\n")
    return True