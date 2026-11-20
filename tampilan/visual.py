"""
tampilan/visual.py — Render helper untuk Pac-Man: BFS vs A*.

Tanggung jawab:
  - Satu transformasi grid -> piksel yang dipakai seluruh permainan.
  - Sprite prosedural (tanpa PNG / internet / dependency baru).
  - HUD terstruktur dan overlay path yang memakai data *nyata* dari Game.

TIDAK mengubah algoritma, pathfinding, state, atau metrik.
"""

import math

import pygame

from core import config
from tampilan import theme
from tampilan import sprites

# HUD desain 72 px (config.HUD_HEIGHT dipakai sebagai batas bawah, tidak diubah)
HUD_DESIGN_HEIGHT = 72


# ---------------------------------------------------------------------------
# LAYOUT
# ---------------------------------------------------------------------------
def hitung_layout(screen_size):
    """Viewport maze terpusat, tile persegi, derivatif dari ukuran surface."""
    w, h = int(screen_size[0]), int(screen_size[1])
    hud_h = max(int(getattr(config, "HUD_HEIGHT", 60)), HUD_DESIGN_HEIGHT)
    if hud_h > max(1, h // 3):
        hud_h = max(1, h // 3)

    play_h = max(h - hud_h, 1)
    cols = max(int(config.GRID_COLS), 1)
    rows = max(int(config.GRID_ROWS), 1)
    tile = max(1, min(w // cols, play_h // rows))
    maze_w, maze_h = tile * cols, tile * rows

    origin_x = (w - maze_w) // 2
    origin_y = (play_h - maze_h) // 2

    return {
        "w": w,
        "h": h,
        "tile": tile,
        "maze_w": maze_w,
        "maze_h": maze_h,
        "origin_x": origin_x,
        "origin_y": origin_y,
        "play_rect": pygame.Rect(origin_x, origin_y, maze_w, maze_h),
        "hud_rect": pygame.Rect(origin_x, origin_y + maze_h, maze_w, hud_h),
    }


def posisi_tile(layout, r, c):
    t = layout["tile"]
    return (layout["origin_x"] + int(c) * t, layout["origin_y"] + int(r) * t)


def pusat_tile(layout, r, c):
    x, y = posisi_tile(layout, r, c)
    half = layout["tile"] // 2
    return (x + half, y + half)


def _vektor(direction):
    if not direction:
        return (1.0, 0.0)
    dr, dc = direction
    vx, vy = float(dc), float(dr)
    panjang = math.hypot(vx, vy)
    if panjang == 0:
        return (1.0, 0.0)
    return (vx / panjang, vy / panjang)


# ---------------------------------------------------------------------------
# SPRITE
# ---------------------------------------------------------------------------
def gambar_pacman(surface, center, radius, direction=(1, 0), mouth_deg=28.0,
                  color=None, bg=None, eye=True):
    r = max(int(radius), 2)
    cx, cy = int(center[0]), int(center[1])
    warna = theme.PACMAN if color is None else color
    latar = theme.PATH if bg is None else bg
    sprite = sprites.pacman_surface(direction, mouth_deg, warna, int(r * 2.0))
    if sprite is not None:
        surface.blit(sprite, sprite.get_rect(center=(cx, cy)))
        return
    vx, vy = _vektor(direction)
    theta = math.atan2(vy, vx)

    pygame.draw.circle(surface, warna, (cx, cy), r)
    if mouth_deg > 0:
        sudut = math.radians(min(float(mouth_deg), 60.0))
        jauh = r + 2
        p2 = (cx + int(jauh * math.cos(theta - sudut)),
              cy + int(jauh * math.sin(theta - sudut)))
        p3 = (cx + int(jauh * math.cos(theta + sudut)),
              cy + int(jauh * math.sin(theta + sudut)))
        pygame.draw.polygon(surface, latar, [(cx, cy), p2, p3])
    if eye and r >= 5:
        ex = cx + int(-vy * r * 0.38)
        ey = cy + int(-vx * r * 0.38)
        pygame.draw.circle(surface, (15, 15, 25), (ex, ey), max(1, int(r * 0.12)))


def gambar_ghost(surface, center, radius, direction=(1, 0), color=None,
                 eye_color=(255, 255, 255), pupil_color=(20, 30, 100), bob=0.0):
    r = max(int(radius), 3)
    cx, cy = int(center[0]), int(center[1]) + int(bob)
    warna = theme.GHOST_RED if color is None else color
    sprite = sprites.ghost_surface(direction, warna, int(r * 2.0))
    if sprite is not None:
        surface.blit(sprite, sprite.get_rect(center=(cx, cy)))
        return

    pygame.draw.ellipse(surface, warna, (cx - r, cy - r, 2 * r, 2 * r))
    pygame.draw.rect(surface, warna, (cx - r, cy, 2 * r, max(1, int(r * 0.75))))
    bawah = cy + int(r * 0.75)
    rok = [
        (cx - r, bawah - int(r * 0.15)),
        (cx - r // 2, bawah + int(r * 0.12)),
        (cx, bawah - int(r * 0.15)),
        (cx + r // 2, bawah + int(r * 0.12)),
        (cx + r, bawah - int(r * 0.15)),
    ]
    pygame.draw.polygon(surface, warna, rok)

    vx, vy = _vektor(direction)
    for tanda in (-1, 1):
        ex = cx + tanda * int(r * 0.38)
        ey = cy - int(r * 0.18)
        erx, ery = max(2, int(r * 0.30)), max(3, int(r * 0.40))
        pygame.draw.ellipse(surface, eye_color,
                            (ex - erx, ey - ery, 2 * erx, 2 * ery))
        pygame.draw.circle(surface, pupil_color,
                           (ex + int(vx * r * 0.12), ey + int(vy * r * 0.12)),
                           max(1, int(r * 0.14)))


def gambar_exit(surface, layout, pos, color=None):
    t = layout["tile"]
    x, y = posisi_tile(layout, int(pos[0]), int(pos[1]))
    margin = max(2, t // 8)
    rect = pygame.Rect(x + margin, y + margin, t - 2 * margin, t - 2 * margin)
    pygame.draw.rect(surface, theme.EXIT if color is None else color, rect,
                     border_radius=max(2, t // 6))
    if t >= 12:
        pygame.draw.rect(surface, (16, 120, 72),
                         rect.inflate(-max(2, t // 5), -max(2, t // 5)), 1,
                         border_radius=max(1, t // 8))


def gambar_maze(surface, layout, grid):
    """Maze solid beveled: dinding slate-blue padat dengan depth ringan.

    Geometri dan ukuran tile tidak diubah, sehingga overlay jalur BFS/A*
    tetap sejajar persis dengan sel maze. Bevel hanya pada sisi yang
    berbatasan dengan koridor atau tepi luar, agar tekstur tetap bersih.
    """
    t = layout["tile"]
    if t <= 0:
        return
    ox, oy = layout["origin_x"], layout["origin_y"]
    baris, kolom = len(grid), len(grid[0])

    # Koridor gelap: satu bidang datar tanpa grid dekoratif.
    pygame.draw.rect(surface, theme.PATH, layout["play_rect"])

    # Isi dinding sebagai satu massa solid.
    for r in range(baris):
        for c in range(kolom):
            if grid[r][c] == 1:
                pygame.draw.rect(surface, theme.WALL_SOLID,
                                 (ox + c * t, oy + r * t, t, t))

    # Bevel pada tepi yang terlihat saja. Cahaya dari kiri-atas.
    tebal = max(1, min(4, t // 8))
    for r in range(baris):
        for c in range(kolom):
            if grid[r][c] != 1:
                continue
            x, y = ox + c * t, oy + r * t
            if r == 0 or grid[r - 1][c] != 1:
                pygame.draw.rect(surface, theme.WALL_BEVEL_LIGHT,
                                 (x, y, t, tebal))
            if c == 0 or grid[r][c - 1] != 1:
                pygame.draw.rect(surface, theme.WALL_BEVEL_LIGHT,
                                 (x, y, tebal, t))
            if r == baris - 1 or grid[r + 1][c] != 1:
                pygame.draw.rect(surface, theme.WALL_BEVEL_DARK,
                                 (x, y + t - tebal, t, tebal))
            if c == kolom - 1 or grid[r][c + 1] != 1:
                pygame.draw.rect(surface, theme.WALL_BEVEL_DARK,
                                 (x + t - tebal, y, tebal, t))


# ---------------------------------------------------------------------------
# VISUALISASI PATH — data nyata dari Game.current_path, tanpa data baru
# ---------------------------------------------------------------------------
def gambar_path_aktif(surface, layout, path, warna, alpha=105):
    """Overlay jalur yang sedang dieksekusi Ghost (bukan frontier/visited)."""
    if not path:
        return
    t = layout["tile"]
    lapis = pygame.Surface((layout["maze_w"], layout["maze_h"]), pygame.SRCALPHA)
    w = tuple(list(warna)[:3]) + (alpha,)
    w_terang = tuple(min(255, v + 45) for v in warna[:3]) + (min(255, alpha + 90),)
    titik = [pusat_tile(layout, r, c) for r, c in path]
    rel = [(x - layout["origin_x"], y - layout["origin_y"]) for x, y in titik]

    if len(rel) > 1:
        pygame.draw.lines(lapis, w, False, rel, max(1, t // 14))
    for x, y in rel[:-1]:
        pygame.draw.circle(lapis, w, (x, y), max(2, t // 7))
    if rel:
        x, y = rel[0]
        pygame.draw.circle(lapis, w_terang, (x, y), max(2, t // 5))

    surface.blit(lapis, (layout["origin_x"], layout["origin_y"]))


# ---------------------------------------------------------------------------
# HUD
# ---------------------------------------------------------------------------
def _stat_tile(surface, rect, label, nilai, warna, s=1.0):
    theme.panel(surface, rect, fill=theme.SURFACE_2, border=theme.BORDER,
                radius=max(5, int(10 * s)), width=1)
    theme.fit_text(surface, label, (rect.centerx, rect.top + rect.height * 0.30),
                   rect.width - int(6 * s), int(10 * s), theme.TEXT_DIM, bold=True)
    theme.fit_text(surface, nilai, (rect.centerx, rect.centery + rect.height * 0.12),
                   rect.width - int(6 * s), int(18 * s), warna, bold=True)


def gambar_hud(surface, layout, game):
    rect = layout["hud_rect"]
    if rect.height <= 0 or rect.width <= 0:
        return

    pygame.draw.rect(surface, theme.BG_DEEP, rect)
    pygame.draw.line(surface, theme.BORDER,
                     (rect.left, rect.top), (rect.right, rect.top), 2)

    stats = game.get_stats()
    nama = game.maze_data.get("name", "")
    kondisi = "PAC-MAN BERGERAK" if game.condition == "bergerak" else "PAC-MAN DIAM"
    s = max(0.55, min(rect.height / HUD_DESIGN_HEIGHT, rect.width / 630.0))

    if rect.height < 56:
        theme.fit_text(surface,
                       "{0} | {1} | S {2} | {3:.3f}ms | P {4}".format(
                           theme.label_algoritma(game.algorithm), kondisi,
                           int(stats["nodes_explored"]), float(stats["search_time_ms"]),
                           int(stats["path_length"])),
                       rect.center, rect.width - 10, 11, theme.TEXT, bold=True)
        return

    pad = int(theme.M * s)
    badge_w = int(72 * s)
    badge = pygame.Rect(rect.left + pad, rect.centery - int(15 * s),
                        badge_w, int(30 * s))
    theme.badge_algoritma(surface, badge, game.algorithm, s)

    teks_x = badge.right + int(theme.M * s)
    theme.fit_text(surface, nama,
                   (teks_x + (rect.width * 0.42) // 2, rect.top + rect.height * 0.32),
                   int(rect.width * 0.40), int(13 * s), theme.TEXT, bold=True)
    theme.fit_text(surface, kondisi,
                   (teks_x + (rect.width * 0.42) // 2, rect.top + rect.height * 0.70),
                   int(rect.width * 0.40), int(13 * s), theme.TEXT)

    kanan_x = rect.left + int(rect.width * 0.55)
    tersedia = rect.right - kanan_x - pad
    celah = int(theme.S * s)
    lebar = max(40, (tersedia - 2 * celah) // 3)
    tinggi = int(rect.height * 0.62)
    atas = rect.centery - tinggi // 2
    warna_algo = theme.warna_algoritma(game.algorithm)

    data = [
        ("NODES", str(int(stats["nodes_explored"])), warna_algo),
        ("WAKTU", "{0:.2f} ms".format(float(stats["search_time_ms"])), theme.SUCCESS),
        ("PATH", str(int(stats["path_length"])), theme.TEXT),
    ]
    for i, (label, nilai, warna) in enumerate(data):
        _stat_tile(surface,
                   pygame.Rect(kanan_x + i * (lebar + celah), atas, lebar, tinggi),
                   label, nilai, warna, s)
