"""tampilan/main_ui.py — Main menu "Modern Retro Arcade".

Komposisi: hero maze di kiri, navigasi terstruktur di kanan; stack vertikal
pada layar sempit. Return value tombol tidak berubah.
"""

import json
import math

import pygame

from core import config
from tampilan import theme
from tampilan.ui_mulai import show_mulai
from tampilan.ui_setting import show_setting
from tampilan.ui_info import show_hasil
from tampilan.visual import gambar_ghost, gambar_pacman

MENU_FPS = 60
MENU_ITEMS = [
    ("mulai", "MULAI"),
    ("setting", "SETTING"),
    ("info", "INFO"),
    ("quit", "QUIT"),
]
AKSEN = {
    "mulai": theme.PACMAN,
    "setting": theme.SURFACE_2,
    "info": theme.BFS,
    "quit": theme.DANGER,
}

_bg_cache = {}
_preview_cache = {}


def _latar(size):
    if size in _bg_cache:
        return _bg_cache[size]
    surf = pygame.Surface(size)
    surf.fill(theme.BG_DEEP)
    langkah = max(28, min(size) // 18)
    for y in range(0, size[1], langkah):
        for x in range(0, size[0], langkah):
            if (x // langkah + y // langkah) % 3 == 0:
                pygame.draw.rect(surf, theme.BG,
                                 (x + 2, y + 2, langkah - 4, langkah - 4),
                                 border_radius=3)
    pygame.draw.rect(surf, theme.BORDER,
                     (10, 10, size[0] - 20, size[1] - 20), 1, border_radius=16)
    _bg_cache[size] = surf
    return surf


def _maze_preview(side):
    kunci = max(40, int(side))
    if kunci in _preview_cache:
        return _preview_cache[kunci]
    with open(config.MAZE_FILES[1], "r", encoding="utf-8") as f:
        data = json.load(f)
    grid = data["grid"]
    sel = max(3, kunci // len(grid))
    surf = pygame.Surface((sel * len(grid[0]), sel * len(grid)))
    surf.fill(theme.PATH)
    for r, baris in enumerate(grid):
        for c, nilai in enumerate(baris):
            if nilai == 1:
                pygame.draw.rect(surf, theme.WALL, (c * sel, r * sel, sel, sel))
                if sel >= 6:
                    pygame.draw.rect(surf, theme.WALL_HI,
                                     (c * sel + 1, r * sel + 1,
                                      max(2, sel // 4), max(2, sel // 4)))
            elif r % 2 == 0 and c % 2 == 0:
                pygame.draw.circle(surf, (58, 68, 108),
                                   (c * sel + sel // 2, r * sel + sel // 2),
                                   max(1, sel // 7))
    er, ec = data["exit"]
    pygame.draw.rect(surf, theme.EXIT,
                     (ec * sel + 1, er * sel + 1, sel - 2, sel - 2),
                     border_radius=max(1, sel // 4))
    _preview_cache[kunci] = surf
    return surf


class Button:
    def __init__(self, rect, label, value, font_size, s):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.value = value
        self.font_size = font_size
        self.s = s
        self.aksen = AKSEN.get(value, theme.SURFACE_2)

    def draw(self, screen, t=0):
        hover = self.rect.collidepoint(pygame.mouse.get_pos())
        denyut = (0.5 + 0.5 * math.sin(t / 280.0)) if hover else 0.0
        isi = theme.lighten(self.aksen, int(20 + 12 * denyut) if hover else 0)
        pinggir = theme.lighten(self.aksen, 55) if hover else theme.BORDER
        theme.panel(screen, self.rect, fill=isi, border=pinggir,
                    radius=max(8, int(12 * self.s)), width=2 + int(denyut))

        bar = pygame.Rect(self.rect.left + int(6 * self.s),
                          self.rect.top + int(8 * self.s),
                          max(2, int(4 * self.s)),
                          self.rect.height - int(16 * self.s))
        pygame.draw.rect(screen, theme.lighten(self.aksen, 60), bar,
                         border_radius=2)

        ikon_x = self.rect.left + int(26 * self.s)
        cy = self.rect.centery
        warna_ikon = (theme.BG_DEEP if self.value in ("mulai", "info", "quit")
                      else theme.TEXT)
        if self.value == "mulai":
            pygame.draw.polygon(screen, warna_ikon, [
                (ikon_x - int(4 * self.s), cy - int(7 * self.s)),
                (ikon_x - int(4 * self.s), cy + int(7 * self.s)),
                (ikon_x + int(8 * self.s), cy)])
        elif self.value == "setting":
            for i, ofs in enumerate((-6, 0, 6)):
                y = cy + int(ofs * self.s)
                pygame.draw.line(screen, warna_ikon,
                                 (ikon_x - int(8 * self.s), y),
                                 (ikon_x + int(8 * self.s), y),
                                 max(1, int(2 * self.s)))
                pygame.draw.circle(screen, warna_ikon,
                                   (ikon_x + int((-3 + i * 3) * self.s), y),
                                   max(2, int(3 * self.s)))
        elif self.value == "info":
            pygame.draw.circle(screen, warna_ikon, (ikon_x, cy),
                               max(4, int(8 * self.s)), 2)
            theme.text(screen, "i", max(11, int(13 * self.s)), warna_ikon,
                       (ikon_x, cy - self.s), bold=True)
        else:
            d = int(6 * self.s)
            pygame.draw.line(screen, warna_ikon,
                             (ikon_x - d, cy - d), (ikon_x + d, cy + d), 2)
            pygame.draw.line(screen, warna_ikon,
                             (ikon_x + d, cy - d), (ikon_x - d, cy + d), 2)

        theme.fit_text(screen, self.label,
                       (self.rect.centerx + int(12 * self.s), cy),
                       self.rect.width - int(52 * self.s), self.font_size,
                       warna_ikon, bold=True)

    def clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.rect.collidepoint(event.pos))


def _hero(screen, rect, s, t):
    theme.panel(screen, rect, fill=theme.SURFACE, border=theme.BORDER,
                radius=20, width=2)

    theme.text(screen, "PAC-MAN", int(theme.SIZE_DISPLAY * s), theme.PACMAN,
               (rect.centerx, rect.top + int(58 * s)), bold=True)
    theme.text(screen, "BFS  vs  A*", int(theme.SIZE_H1 * s), theme.BFS,
               (rect.centerx, rect.top + int(112 * s)), bold=True)
    theme.text(screen, "AI Pathfinding Benchmark", int(theme.SIZE_H3 * s),
               theme.TEXT_MUTED, (rect.centerx, rect.top + int(146 * s)))

    ruang = max(48, rect.height - int(190 * s) - int(34 * s))
    sisi = max(48, min(int(rect.width * 0.78), ruang))
    prev = _maze_preview(sisi)
    px = rect.centerx - prev.get_width() // 2
    py = min(rect.top + int(176 * s),
             rect.bottom - prev.get_height() - int(28 * s))
    py = max(rect.top + int(160 * s), py)
    screen.blit(prev, (px, py))

    r = max(5, int(prev.get_width() * 0.055))
    gambar_pacman(screen,
                  (px + int(prev.get_width() * 0.24),
                   py + int(prev.get_height() * 0.72)),
                  r, (1, 0),
                  mouth_deg=10 + 26 * (0.5 + 0.5 * math.sin(t / 150.0)),
                  bg=theme.PATH)
    for i, warna in enumerate((theme.GHOST_RED, theme.GHOST_PINK,
                               theme.GHOST_CYAN, theme.GHOST_ORANGE)):
        gambar_ghost(screen,
                     (px + int(prev.get_width() * (0.52 + i * 0.10)),
                      py + int(prev.get_height() * 0.34)),
                     max(4, int(r * 0.78)), (0, 1), color=warna,
                     bob=math.sin(t / 170.0 + i) * 2)

    theme.text(screen, "BFS = CYAN     A* = AMBER", int(theme.SIZE_CAPTION * s),
               theme.TEXT_DIM, (rect.centerx, rect.bottom - int(16 * s)))


def show_main_menu(screen=None):
    if screen is None:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_caption("Pac-Man AI: BFS vs A*")
    w, h = screen.get_size()
    clock = pygame.time.Clock()
    portrait = w / max(h, 1) < 1.25
    s = (max(0.75, min(h / 720.0, w / 900.0)) if portrait
         else max(0.45, min(h / 720.0, w / 1280.0)))
    margin = int(theme.XL * s)

    if not portrait:
        hero = pygame.Rect(margin, margin, int(w * 0.56) - margin,
                           h - 2 * margin)
        nav_x = hero.right + int(theme.S * s)
        nav = pygame.Rect(nav_x, margin, w - margin - nav_x, h - 2 * margin)
    else:
        hero = pygame.Rect(margin, margin, w - 2 * margin, int(h * 0.44))
        nav = pygame.Rect(margin, hero.bottom + int(theme.S * s),
                          w - 2 * margin, h - margin - hero.bottom - int(theme.S * s))

    gap = int(theme.S * s)
    btn_h = max(28, min(int(56 * s),
                        (nav.height - int(76 * s) - 3 * gap) // 4))
    btn_w = min(int(300 * s), nav.width - int(theme.L * s))
    buttons = [
        Button((nav.centerx - btn_w // 2,
                nav.top + int(52 * s) + i * (btn_h + gap),
                btn_w, btn_h),
               label, value, int(theme.SIZE_H3 * s), s)
        for i, (value, label) in enumerate(MENU_ITEMS)
    ]
    keymap = {pygame.K_1: "mulai", pygame.K_2: "setting",
              pygame.K_3: "info", pygame.K_4: "quit"}

    while True:
        t = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "quit"
                if event.key in keymap:
                    return keymap[event.key]
            for b in buttons:
                if b.clicked(event):
                    return b.value

        screen.blit(_latar((w, h)), (0, 0))
        _hero(screen, hero, s, t)
        theme.panel(screen, nav, fill=theme.SURFACE, border=theme.BORDER,
                    radius=20, width=2)
        theme.text(screen, "MENU", int(theme.SIZE_H2 * s), theme.TEXT_MUTED,
                   (nav.centerx, nav.top + int(28 * s)), bold=True)
        for b in buttons:
            b.draw(screen, t)
        theme.text(screen, "Klik atau tekan 1-4   |   ESC = keluar",
                   int(theme.SIZE_CAPTION * s), theme.TEXT_MUTED,
                   (nav.centerx, nav.bottom - int(18 * s)))

        pygame.display.flip()
        clock.tick(MENU_FPS)


def run():
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    data_hasil_percobaan = []

    while True:
        pilihan = show_main_menu(screen)
        if pilihan == "quit":
            break
        if pilihan == "mulai":
            hasil = show_mulai(screen)
            if hasil == "quit":
                break
            if hasil == "back":
                continue
            print("Pengaturan game:", hasil)
            continue
        if pilihan == "setting":
            if show_setting(screen) == "quit":
                break
            continue
        if pilihan == "info":
            show_hasil(screen, data_hasil_percobaan)
            continue

    pygame.quit()


if __name__ == "__main__":
    run()
