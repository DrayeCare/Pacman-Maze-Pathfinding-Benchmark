"""tampilan/ui_record_manager.py — kelola & hapus rekaman input pemain.

Semua penghapusan melewati core/recorder.py (validasi path + schema). UI hanya
memilih item dan meminta konfirmasi; tidak pernah menghapus file langsung.
"""

import pygame

from core import audio
from core import config
from core import recorder
from tampilan import theme

FPS = getattr(config, "FPS", 10)


class _Tombol:
    def __init__(self, rect, label, warna, font_size=17):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.warna = warna
        self.font_size = font_size
        self.enabled = True

    def clicked(self, event):
        return (self.enabled and event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1 and self.rect.collidepoint(event.pos))

    def draw(self, screen):
        isi = self.warna if self.enabled else theme.SURFACE
        if self.enabled and self.rect.collidepoint(pygame.mouse.get_pos()):
            isi = theme.lighten(self.warna, 18)
        pygame.draw.rect(screen, isi, self.rect, border_radius=9)
        pygame.draw.rect(screen, theme.BORDER if self.enabled else theme.TEXT_DIM,
                         self.rect, 2, border_radius=9)
        theme.fit_text(screen, self.label, self.rect.center,
                       self.rect.width - 10, self.font_size,
                       theme.TEXT if self.enabled else theme.TEXT_DIM, bold=True)


def _konfirmasi(screen, judul, pesan, setuju="HAPUS", warna=theme.DANGER):
    """Dialog konfirmasi sederhana. ENTER/Y = setuju, ESC/N = batal."""
    w, h = screen.get_size()
    clock = pygame.time.Clock()
    s = min(h / 720.0, w / 1280.0)
    cx = w // 2
    lebar, tinggi = min(int(560 * s), w - 40), min(int(280 * s), h - 40)
    panel = pygame.Rect(cx - lebar // 2, h // 2 - tinggi // 2, lebar, tinggi)
    bw, bh = int(190 * s), int(48 * s)
    oke = _Tombol((cx - bw - int(12 * s), panel.bottom - int(72 * s),
                   bw, bh), setuju, warna)
    batal = _Tombol((cx + int(12 * s), panel.bottom - int(72 * s),
                     bw, bh), "BATAL", theme.SURFACE_2)

    while True:
        for event in pygame.event.get():
            audio.handle_event(event)
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_y):
                    return True
                if event.key in (pygame.K_ESCAPE, pygame.K_n):
                    return False
            if oke.clicked(event):
                return True
            if batal.clicked(event):
                return False

        screen.fill(theme.BG_DEEP)
        theme.panel(screen, panel, fill=theme.SURFACE, border=warna,
                    radius=16, width=3)
        theme.text(screen, judul, int(28 * s), warna,
                   (cx, panel.top + int(58 * s)), bold=True)
        theme.fit_text(screen, pesan, (cx, panel.top + int(118 * s)),
                       lebar - int(40 * s), int(16 * s), theme.TEXT)
        oke.draw(screen)
        batal.draw(screen)
        theme.text(screen, "ENTER = konfirmasi | ESC = batal",
                   int(12 * s), theme.TEXT_DIM, (cx, h - int(24 * s)))
        pygame.display.flip()
        clock.tick(FPS)


def show_record_manager(screen, session):
    """Halaman RECORDING MANAGER. Kembalikan 'back' atau 'quit'."""
    pygame.display.set_caption("Pac-Man AI: Recording Manager")
    w, h = screen.get_size()
    clock = pygame.time.Clock()
    s = min(h / 720.0, w / 1280.0)
    cx = w // 2
    indeks = [0]

    lebar = min(int(800 * s), w - 40)
    tinggi = min(int(620 * s), h - 40)
    panel = pygame.Rect(cx - lebar // 2, h // 2 - tinggi // 2, lebar, tinggi)
    baris_rects = [pygame.Rect(panel.left + int(34 * s),
                               panel.top + int(112 * s) + i * int(58 * s),
                               panel.width - int(68 * s), int(50 * s))
                   for i in range(7)]
    bw, bh = int(190 * s), int(46 * s)
    y_btn = panel.bottom - int(66 * s)

    def tombol(i, label, warna):
        return _Tombol((panel.left + int(34 * s) + i * (bw + int(12 * s)),
                        y_btn, bw, bh), label, warna)

    hapus = tombol(0, "DELETE", theme.DANGER)
    hapus_semua = tombol(1, "DELETE ALL", theme.ASTAR)
    kembali = tombol(2, "BACK", theme.SURFACE_2)

    while True:
        sesi = recorder.list_recording_infos(session.directory)
        if indeks[0] >= len(sesi):
            indeks[0] = max(0, len(sesi) - 1)
        hapus.enabled = bool(sesi and sesi[indeks[0]]["valid"])
        hapus_semua.enabled = bool(sesi)

        for event in pygame.event.get():
            audio.handle_event(event)
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "back"
                if event.key in (pygame.K_UP, pygame.K_DOWN):
                    if sesi:
                        arah = -1 if event.key == pygame.K_UP else 1
                        indeks[0] = (indeks[0] + arah) % len(sesi)
                if event.key == pygame.K_d and hapus.enabled:
                    info = sesi[indeks[0]]
                    if _konfirmasi(screen, "HAPUS REKAMAN",
                                   "Hapus rekaman '{0}'?".format(info["name"])):
                        session.hapus_rekaman(info["path"])
                if event.key == pygame.K_a and hapus_semua.enabled:
                    if _konfirmasi(screen, "HAPUS SEMUA REKAMAN",
                                   "Hapus {0} rekaman?".format(len(sesi)),
                                   setuju="LANJUT"):
                        if _konfirmasi(screen, "KONFIRMASI KEDUA",
                                       "Hapus permanen SEMUA rekaman valid?",
                                       setuju="HAPUS SEMUA"):
                            session.hapus_semua_rekaman()
            for i, r in enumerate(baris_rects):
                if (i < len(sesi) and event.type == pygame.MOUSEBUTTONDOWN
                        and event.button == 1 and r.collidepoint(event.pos)):
                    indeks[0] = i
            if hapus.clicked(event):
                info = sesi[indeks[0]]
                if _konfirmasi(screen, "HAPUS REKAMAN",
                               "Hapus rekaman '{0}'?".format(info["name"])):
                    session.hapus_rekaman(info["path"])
            if hapus_semua.clicked(event):
                if _konfirmasi(screen, "HAPUS SEMUA REKAMAN",
                               "Hapus {0} rekaman?".format(len(sesi)),
                               setuju="LANJUT"):
                    if _konfirmasi(screen, "KONFIRMASI KEDUA",
                                   "Hapus permanen SEMUA rekaman valid?",
                                   setuju="HAPUS SEMUA"):
                        session.hapus_semua_rekaman()
            if kembali.clicked(event):
                return "back"

        screen.fill(theme.BG_DEEP)
        theme.panel(screen, panel, fill=theme.SURFACE, border=theme.BORDER,
                    radius=18, width=2)
        theme.text(screen, "RECORDING MANAGER", int(30 * s), theme.PACMAN,
                   (cx, panel.top + int(44 * s)), bold=True)
        theme.text(screen, "{0} rekaman di direktori input_recordings/".format(
            len(sesi)), int(14 * s), theme.TEXT_MUTED,
            (cx, panel.top + int(76 * s)))

        if not sesi:
            theme.text(screen, "Belum ada rekaman.", int(17 * s),
                       theme.TEXT_DIM, (cx, panel.top + int(250 * s)))

        for i, info in enumerate(sesi[:len(baris_rects)]):
            r = baris_rects[i]
            aktif = i == indeks[0]
            warna = theme.SURFACE_2 if aktif else theme.BG_DEEP
            pygame.draw.rect(screen, warna, r, border_radius=8)
            pygame.draw.rect(screen, theme.PACMAN if aktif else theme.BORDER,
                             r, 2 if aktif else 1, border_radius=8)
            if info["valid"]:
                judul = "{0}  {1}".format("\u25b6" if aktif else " ",
                                          info["name"])
                detail = "{0} | {1} input | {2} tick | {3}".format(
                    info["file"], info["count"], info["duration"],
                    info["created_at"])
                warna_teks = theme.TEXT if aktif else theme.TEXT_MUTED
            else:
                judul = "RUSAK  {0}".format(info["file"])
                detail = str(info["error"])[:80]
                warna_teks = theme.DANGER
            theme.fit_text(screen, judul, (r.left + r.width // 2,
                                           r.top + int(16 * s)),
                           r.width - 16, int(14 * s), warna_teks, bold=True)
            theme.fit_text(screen, detail, (r.left + r.width // 2,
                                            r.bottom - int(14 * s)),
                           r.width - 16, int(11 * s), theme.TEXT_DIM)

        warna_pesan = {"err": theme.DANGER, "ok": theme.SUCCESS}.get(
            session.message_kind, theme.TEXT_MUTED)
        theme.fit_text(screen, session.message[:90],
                       (cx, panel.bottom - int(94 * s)),
                       lebar - int(60 * s), int(12 * s), warna_pesan)

        hapus.draw(screen)
        hapus_semua.draw(screen)
        kembali.draw(screen)
        theme.text(screen, "\u2191/\u2193 pilih   D delete   A delete all   ESC back",
                   int(12 * s), theme.TEXT_DIM, (cx, h - int(18 * s)))
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    pygame.init()
    layar = pygame.display.set_mode((1000, 700))
    print(show_record_manager(layar, recorder.ExperimentSession()))
    pygame.quit()
