"""core/audio.py — pengelola musik latar (BGM) terpusat.

Prinsip:
  - Mixer disiapkan sekali, file dimuat sekali, musik diputar sekali dengan loops=-1.
  - Dipanggil sekali dari main(); layar lain hanya meneruskan event ke handle_event().
  - Tidak pernah mengukur waktu: waktu algoritma tetap diukur di modul algoritma.
  - File tidak ada / gagal dimuat = BGM diam, game tetap berjalan normal.
"""

import os

import pygame

from core import config

_initialized = False
_available = False
_enabled = True
_paused = False
_volume = float(config.AUDIO_VOLUME)


def _amankan(fungsi, *args, **kwargs):
    """Jalankan panggilan mixer; kembalikan False bila perangkat/file bermasalah."""
    try:
        fungsi(*args, **kwargs)
        return True
    except (pygame.error, OSError):
        return False


def init_music():
    """Siapkan mixer dan mulai BGM sekali saja. Aman dipanggil berulang."""
    global _initialized, _available, _paused
    if _initialized:
        return _available
    _initialized = True

    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
    except (pygame.error, OSError):
        return False

    for path in config.AUDIO_FILES:
        if not os.path.isfile(path):
            continue
        if _amankan(pygame.mixer.music.load, path):
            _available = True
            break

    _amankan(pygame.mixer.music.set_volume, _volume)
    if _available and _enabled:
        _paused = not _amankan(pygame.mixer.music.play, -1, 0.0)
    return _available


def is_available():
    return _available


def is_enabled():
    return _enabled


def get_volume():
    return _volume


def status_text():
    if not _available:
        return "MUSIK: TIDAK ADA"
    return "MUSIK: " + ("ON" if _enabled else "OFF")


def set_volume(value):
    """Atur volume 0.0 - 1.0. Berlaku langsung, tidak memutar ulang musik."""
    global _volume
    try:
        _volume = max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return _volume
    if pygame.mixer.get_init():
        _amankan(pygame.mixer.music.set_volume, _volume)
    return _volume


def change_volume(delta):
    return set_volume(_volume + float(delta))


def set_enabled(value):
    """Aktifkan/nonaktifkan tanpa memuat ulang atau memutar dari awal."""
    global _enabled, _paused
    _enabled = bool(value)
    if not _available or not pygame.mixer.get_init():
        return _enabled
    if _enabled:
        if _paused:
            if _amankan(pygame.mixer.music.unpause):
                _paused = False
        elif not pygame.mixer.music.get_busy():
            _paused = not _amankan(pygame.mixer.music.play, -1, 0.0)
    else:
        if _amankan(pygame.mixer.music.pause):
            _paused = True
    return _enabled


def toggle():
    return set_enabled(not _enabled)


def handle_event(event):
    """Shortcut global. Mengembalikan True bila event dikonsumsi modul ini."""
    if getattr(event, "type", None) != pygame.KEYDOWN:
        return False
    if getattr(event, "repeat", 0):
        return False
    key = getattr(event, "key", None)
    if key == pygame.K_m:
        toggle()
        return True
    if key == pygame.K_MINUS:
        change_volume(-config.AUDIO_VOLUME_STEP)
        return True
    if key == pygame.K_EQUALS:
        change_volume(config.AUDIO_VOLUME_STEP)
        return True
    return False


def shutdown():
    """Hentikan musik saat aplikasi keluar."""
    global _enabled, _paused
    if pygame.mixer.get_init():
        _amankan(pygame.mixer.music.stop)
    _enabled = False
    _paused = False
