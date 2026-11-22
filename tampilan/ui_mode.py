"""tampilan/ui_mode.py — pilih MANUAL / RECORD / PLAYBACK sebelum game dibuat."""

import pygame

from core import config
from core import audio
from tampilan import theme

FPS = getattr(config, "FPS", 10)

PILIHAN = [
    ("manual", "MANUAL MODE", "Main seperti biasa, tanpa rekaman.",
     theme.PACMAN),
    ("record", "RECORD MODE", "Rekam otomatis. STOP untuk simpan.",
     theme.DANGER),
    ("playback", "PLAYBACK MODE", "Pilih rekaman & algo, lalu PLAY.",
     theme.BFS),
]


class _Kartu:
    def __init__(self, rect, nilai, judul, keterangan, warna, s):
        self.rect = pygame.Rect(rect)
        self.nilai = nilai
        self.judul = judul
        self.keterangan = keterangan
        self.warna = warna
        self.s = s

    def clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.rect.collidepoint(event.pos))

    def draw(self, screen, aktif):
        isi = theme.lighten(self.warna, 18) if aktif else theme.SURFACE_2
        if self.rect.collidepoint(pygame.mouse.get_pos()):
            isi = theme.lighten(isi, 14)
        pygame.draw.rect(screen, isi, self.rect, border_radius=14)
        pygame.draw.rect(screen, self.warna if aktif else theme.BORDER,
                         self.rect, 3 if aktif else 2, border_radius=14)
        cx = self.rect.centerx
        theme.text(screen, self.judul, int(24 * self.s), self.warna,
                   (cx, self.rect.top + int(52 * self.s)), bold=True)
        theme.fit_text(screen, self.keterangan,
                       (cx, self.rect.top + int(104 * self.s)),
                       self.rect.width - int(20 * self.s), int(14 * self.s),
                       theme.TEXT_MUTED)
        theme.text(screen, self.nilai.upper(), int(12 * self.s), theme.TEXT_DIM,
                   (cx, self.rect.bottom - int(26 * self.s)), bold=True)


def show_mode(screen=None):
    """Kembalikan 'manual' | 'record' | 'playback' | 'back' | 'quit'."""
    if screen is None:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_caption("Pac-Man AI: Pilih Mode")
    w, h = screen.get_size()
    clock = pygame.time.Clock()
    s = min(h / 720.0, w / 1280.0)
    cx = w // 2

    lebar = min(int(330 * s), (w - 80) // 3)
    tinggi = min(int(320 * s), h // 2)
    jarak = int(24 * s)
    total = 3 * lebar + 2 * jarak
    x0 = cx - total // 2
    y0 = h // 2 - tinggi // 2 - int(30 * s)
    kartu = [_Kartu((x0 + i * (lebar + jarak), y0, lebar, tinggi),
                    nilai, judul, ket, warna, s)
             for i, (nilai, judul, ket, warna) in enumerate(PILIHAN)]

    while True:
        for event in pygame.event.get():
            audio.handle_event(event)
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "back"
                if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    return PILIHAN[event.key - pygame.K_1][0]
            for k in kartu:
                if k.clicked(event):
                    return k.nilai

        screen.fill(theme.BG_DEEP)
        theme.text(screen, "PILIH MODE", int(46 * s), theme.TEXT,
                   (cx, int(96 * s)), bold=True)
        theme.text(screen, "Mode dipilih sebelum game dimulai", int(18 * s),
                   theme.TEXT_MUTED, (cx, int(142 * s)))
        for i, k in enumerate(kartu):
            k.draw(screen, aktif=False)
            theme.text(screen, str(i + 1), int(20 * s), k.warna,
                       (k.rect.left + int(24 * s), k.rect.top + int(22 * s)),
                       bold=True)
        theme.text(screen, "1 / 2 / 3 pilih mode   |   ESC kembali",
                   int(14 * s), theme.TEXT_DIM, (cx, h - int(28 * s)))
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    pygame.init()
    layar = pygame.display.set_mode((1000, 700))
    print(show_mode(layar))
    pygame.quit()
