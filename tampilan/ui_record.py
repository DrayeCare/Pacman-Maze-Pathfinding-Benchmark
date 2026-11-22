"""tampilan/ui_record.py — UI minimal untuk mode RECORD.

Tidak ada panel permanen di atas maze. Selama rekaman hanya ada status bar
kecil dengan tombol STOP; setelah rekaman selesai ada halaman ringkasan.
Backend rekaman tetap milik core/recorder.py.
"""

import os

import pygame

from core import config
from tampilan import theme
from tampilan.visual import hitung_layout

FPS = getattr(config, "FPS", 10)


class RuntimeStatus:
    """Status bar ringkas di sudut kiri atas area maze (REC / PLAYBACK)."""

    def __init__(self):
        self.stop_rect = pygame.Rect(0, 0, 0, 0)

    def _rects(self, screen):
        play = hitung_layout(screen.get_size())["play_rect"]
        lebar = max(180, min(370, play.width - 16))
        rect = pygame.Rect(play.left + 8, play.top + 8, lebar, 34)
        stop = pygame.Rect(rect.right - 80, rect.top + 5, 72, 24)
        return rect, stop

    def handle(self, event, screen):
        """Kembalikan 'stop' bila tombol STOP diklik, selain itu None."""
        _, stop = self._rects(screen)
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and stop.collidepoint(event.pos)):
            return "stop"
        return None

    def draw(self, screen, session, mode, game, tick):
        rect, stop = self._rects(screen)
        self.stop_rect = stop
        if mode == "record":
            warna = theme.DANGER
            teks = "REC  {0} input  |  tick {1}".format(
                len(session.recorder.events), tick)
        else:
            warna = theme.warna_algoritma(session.algorithm)
            run = session.runner
            total = run.total_ticks if run else 0
            teks = "PLAYBACK {0}  {1}/{2} tick".format(
                session.algorithm.upper(), run.tick if run else 0, total)

        pygame.draw.rect(screen, theme.SURFACE, rect, border_radius=8)
        pygame.draw.rect(screen, warna, rect, 2, border_radius=8)
        theme.fit_text(screen, teks,
                       (rect.left + 8 + (rect.width - 96) / 2, rect.centery),
                       rect.width - 100, 13, warna, bold=True)
        hover = stop.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(screen, theme.lighten(theme.DANGER, 18) if hover
                         else theme.DANGER, stop, border_radius=5)
        theme.fit_text(screen, "STOP", stop.center, stop.width - 6, 12,
                       theme.BG_DEEP, bold=True)


class _Tombol:
    def __init__(self, rect, label, warna, font_size):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.warna = warna
        self.font_size = font_size

    def clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.rect.collidepoint(event.pos))

    def draw(self, screen):
        hover = self.rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(screen, theme.lighten(self.warna, 18) if hover
                         else self.warna, self.rect, border_radius=10)
        pygame.draw.rect(screen, theme.BORDER, self.rect, 2, border_radius=10)
        theme.fit_text(screen, self.label, self.rect.center,
                       self.rect.width - 12, self.font_size, theme.TEXT, bold=True)


def show_record_summary(screen, info):
    """Halaman setelah STOP RECORDING / akhir game pada mode RECORD."""
    pygame.display.set_caption("Pac-Man AI: Rekaman Tersimpan")
    w, h = screen.get_size()
    clock = pygame.time.Clock()
    s = min(h / 720.0, w / 1280.0)
    cx = w // 2
    info = info or {}

    lebar = min(int(620 * s), w - 40)
    tinggi = min(int(430 * s), h - 40)
    panel_rect = pygame.Rect(cx - lebar // 2, h // 2 - tinggi // 2,
                             lebar, tinggi)
    btn_w, btn_h = int(260 * s), int(56 * s)
    menu_btn = _Tombol((cx - btn_w - int(12 * s), panel_rect.bottom - int(78 * s),
                        btn_w, btn_h), "KEMBALI KE MENU", theme.SUCCESS, int(20 * s))
    quit_btn = _Tombol((cx + int(12 * s), panel_rect.bottom - int(78 * s),
                        btn_w, btn_h), "QUIT", theme.SURFACE_2, int(20 * s))

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN,
                                 pygame.K_KP_ENTER):
                    return "menu"
                if event.key == pygame.K_q:
                    return "quit"
            if menu_btn.clicked(event):
                return "menu"
            if quit_btn.clicked(event):
                return "quit"

        screen.fill(theme.BG_DEEP)
        theme.panel(screen, panel_rect, fill=theme.SURFACE, border=theme.BORDER,
                    radius=18, width=2)
        theme.text(screen, "REKAMAN SELESAI", int(38 * s), theme.DANGER,
                   (cx, panel_rect.top + int(64 * s)), bold=True)
        theme.text(screen, info.get("message", ""), int(16 * s), theme.TEXT_MUTED,
                   (cx, panel_rect.top + int(106 * s)))

        baris = [
            ("NAMA REKAMAN", info.get("name", "-")),
            ("FILE", os.path.basename(info["file"]) if info.get("file") else "-"),
            ("INPUT TEREKAM", str(info.get("count", 0))),
            ("DURASI (TICK)", str(info.get("ticks", 0))),
        ]
        for i, (label, nilai) in enumerate(baris):
            y = panel_rect.top + int(150 * s) + i * int(42 * s)
            theme.text(screen, label, int(14 * s), theme.TEXT_DIM,
                       (cx - int(190 * s), y), bold=True)
            theme.fit_text(screen, nilai, (cx + int(90 * s), y),
                           int(320 * s), int(18 * s), theme.TEXT, bold=True)

        menu_btn.draw(screen)
        quit_btn.draw(screen)
        theme.text(screen, "ENTER / ESC = menu utama", int(13 * s),
                   theme.TEXT_DIM, (cx, h - int(24 * s)))
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    pygame.init()
    layar = pygame.display.set_mode((1000, 700))
    print(show_record_summary(layar, {
        "name": "player_test_001", "file": "/tmp/player_test_001.json",
        "count": 12, "ticks": 34, "message": "Tersimpan: player_test_001.json",
    }))
    pygame.quit()
