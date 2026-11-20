"""tampilan/sprites.py — sprite sheet karakter dari folder assets/sprites.

Memuat dua sheet sekali saja, memotong frame 32x32, mewarnai ulang ke warna
design token (theme), lalu menyimpan hasil diskalakan di cache. Dipakai oleh
visual.py; bila file tidak ada, visual.py otomatis memakai gambar prosedural.
Tidak menyentuh logika game, algoritma, atau metrik.
"""

import os

import pygame

from core import config

_FRAME = 32
_PACMAN_BODY = (255, 181, 112)
_PACMAN_EDGE = (186, 97, 86)
_GHOST_BODY = (235, 86, 75)
_GHOST_EDGE = (176, 48, 92)

_base = {}
_cache = {}
_diload = False


def _potong(sheet):
    hasil = []
    for r in range(sheet.get_height() // _FRAME):
        baris = []
        for c in range(sheet.get_width() // _FRAME):
            cell = pygame.Surface((_FRAME, _FRAME), pygame.SRCALPHA)
            cell.blit(sheet, (0, 0), (c * _FRAME, r * _FRAME, _FRAME, _FRAME))
            minx, miny, maxx, maxy = _FRAME, _FRAME, -1, -1
            for y in range(_FRAME):
                for x in range(_FRAME):
                    if cell.get_at((x, y)).a > 8:
                        minx = min(minx, x)
                        miny = min(miny, y)
                        maxx = max(maxx, x)
                        maxy = max(maxy, y)
            if maxx >= minx:
                cell = cell.subsurface((minx, miny, maxx - minx + 1, maxy - miny + 1)).copy()
            else:
                cell = pygame.Surface((1, 1), pygame.SRCALPHA)
            baris.append(cell)
        hasil.append(baris)
    return hasil


def _load():
    global _diload
    if _base:
        return True
    if _diload and not _base:
        return False
    _diload = True
    folder = os.path.join(config.BASE_DIR, "assets", "sprites")
    try:
        _base["pacman"] = _potong(pygame.image.load(
            os.path.join(folder, "PacManAssets-PacMan.png")).convert_alpha())
        _base["ghost"] = _potong(pygame.image.load(
            os.path.join(folder, "PacManAssets-Ghosts.png")).convert_alpha())
    except (pygame.error, OSError):
        _base.clear()
        return False
    return True


def _warnai(surf, sumber_body, sumber_edge, warna):
    out = surf.copy()
    badan = tuple(int(v) for v in warna[:3])
    tepi = tuple(max(0, int(v * 0.62)) for v in badan)
    for y in range(out.get_height()):
        for x in range(out.get_width()):
            p = out.get_at((x, y))
            if p.a == 0:
                continue
            if p[:3] == sumber_body:
                out.set_at((x, y), badan + (p.a,))
            elif p[:3] == sumber_edge:
                out.set_at((x, y), tepi + (p.a,))
    return out


def _skala(surf, size):
    size = max(1, int(size))
    faktor = size / max(surf.get_width(), surf.get_height())
    w = max(1, int(round(surf.get_width() * faktor)))
    h = max(1, int(round(surf.get_height() * faktor)))
    kecil = pygame.transform.smoothscale(surf, (w, h))
    if w == size and h == size:
        return kecil
    out = pygame.Surface((size, size), pygame.SRCALPHA)
    out.blit(kecil, ((size - w) // 2, (size - h) // 2))
    return out


def _ambil(kind, baris, kolom, warna, size, flip, sumber_body, sumber_edge):
    if not _load():
        return None
    try:
        frame = _base[kind][baris][kolom]
    except (IndexError, KeyError):
        return None
    warna = tuple(int(v) for v in warna[:3])
    key = (kind, baris, kolom, warna, int(size), bool(flip))
    if key not in _cache:
        surf = _skala(_warnai(frame, sumber_body, sumber_edge, warna), size)
        if flip:
            surf = pygame.transform.flip(surf, True, False)
        _cache[key] = surf
    return _cache[key]


def pacman_surface(direction, mouth_deg, warna, size):
    """Pilih frame mulut sesuai arah dan besar bukaan mulut."""
    dr, dc = direction if direction else (1, 0)
    buka = float(mouth_deg or 0)
    if dc:
        if buka >= 28:
            baris, kolom = 0, 2
        elif buka >= 14:
            baris, kolom = 1, 2
        else:
            baris, kolom = 1, 3
    else:
        baris, kolom = (0, 1) if buka >= 18 else (0, 0)
    return _ambil("pacman", baris, kolom, warna, size, dc < 0,
                  _PACMAN_BODY, _PACMAN_EDGE)


def ghost_surface(direction, warna, size):
    """Empat frame rok ghost, mengikuti ticks agar animasi tetap konsisten."""
    dr, dc = direction if direction else (1, 0)
    kolom = (pygame.time.get_ticks() // 130) % 4
    return _ambil("ghost", 0, kolom, warna, size, dc < 0,
                  _GHOST_BODY, _GHOST_EDGE)
