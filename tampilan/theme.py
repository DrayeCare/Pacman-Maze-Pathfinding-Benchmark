"""
tampilan/theme.py — Design tokens "Modern Retro Arcade".

Satu sumber kebenaran untuk warna, tipografi, spacing, dan komponen dasar.
Modul UI lain mengimpor token ini agar palet/font tidak lagi diduplikasi.
Tidak mengandung logika game, algoritma, atau metrik.
"""

import pygame

FONT_NAME = "consolas"

# Permukaan (dark grey, bukan hitam murni — lihat Material dark theme)
BG_DEEP = (7, 10, 24)
BG = (11, 15, 34)
SURFACE = (18, 23, 48)
SURFACE_2 = (26, 32, 64)
BORDER = (70, 82, 140)

# Teks
TEXT = (238, 242, 255)
TEXT_MUTED = (160, 172, 210)
TEXT_DIM = (116, 128, 170)

# Karakter & maze
PACMAN = (255, 214, 40)
WALL = (48, 76, 216)
WALL_HI = (92, 124, 255)
PATH = (5, 7, 18)
EXIT = (46, 204, 113)
GHOST_RED = (240, 72, 84)
GHOST_PINK = (242, 150, 190)
GHOST_CYAN = (86, 200, 224)
GHOST_ORANGE = (242, 168, 86)

# Maze solid beveled (dipakai visual.gambar_maze)
WALL_SOLID = (58, 78, 142)
WALL_BEVEL_LIGHT = (88, 112, 184)
WALL_BEVEL_DARK = (34, 48, 94)

# Identitas algoritma — dipakai konsisten di semua layar
BFS = (72, 190, 255)
ASTAR = (255, 176, 72)

# Status & aksi
SUCCESS = (64, 200, 120)
DANGER = (235, 84, 96)
PRIMARY = PACMAN
SECONDARY = SURFACE_2

# Skala tipografi pada desain 1280x720
SIZE_DISPLAY = 58
SIZE_H1 = 34
SIZE_H2 = 22
SIZE_H3 = 16
SIZE_BODY = 15
SIZE_CAPTION = 12
SIZE_NUMBER = 28

# Skala spacing
XS, S, M, L, XL, XXL = 4, 8, 12, 16, 24, 32

_fonts = {}


def font(size, bold=False):
    """Font konsisten dengan cache, menggantikan _font di tiap file UI."""
    size = max(int(size), 8)
    key = (size, bool(bold))
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont(FONT_NAME, key[0], bold=key[1])
    return _fonts[key]


def text(surface, msg, size, color, center, bold=False):
    s = font(size, bold).render(str(msg), True, color)
    surface.blit(s, s.get_rect(center=center))
    return s


def fit_text(surface, msg, center, max_w, size, color, bold=False):
    size = max(int(size), 9)
    while size > 9 and font(size, bold).size(str(msg))[0] > max_w:
        size -= 1
    s = font(size, bold).render(str(msg), True, color)
    surface.blit(s, s.get_rect(center=center))
    return s


def panel(surface, rect, fill=SURFACE, border=BORDER, radius=14, width=2):
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    if width:
        pygame.draw.rect(surface, border, rect, width, border_radius=radius)


def lighten(color, amount=18):
    return tuple(min(255, int(v) + int(amount)) for v in color)


def warna_algoritma(nama):
    """BFS -> cyan, A* -> amber, selainnya -> netral."""
    n = str(nama or "").strip().lower()
    if n in ("bfs", "astar", "a*"):
        return BFS if n == "bfs" else ASTAR
    return TEXT_MUTED


def label_algoritma(nama):
    n = str(nama or "").strip().lower()
    if n == "bfs":
        return "BFS"
    if n in ("astar", "a*"):
        return "A*"
    return "—"


def badge_algoritma(surface, rect, nama, s=1.0):
    """Badge kecil dengan warna identitas algoritma."""
    warna = warna_algoritma(nama)
    panel(surface, rect, fill=SURFACE_2, border=warna, radius=max(4, int(8 * s)),
          width=max(1, int(2 * s)))
    fit_text(surface, label_algoritma(nama), rect.center,
             rect.width - int(8 * s), int(14 * s), warna, bold=True)
