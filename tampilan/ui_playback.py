"""tampilan/ui_playback.py — konfigurasi dan hasil PLAYBACK (di luar gameplay).

Semua pilihan (recording + algoritma) dibuat di sini, sebelum Game dibuat.
Backend tetap core/recorder.py dan core/game.py.
"""

import os

import pygame

from core import config
from core import audio
from core.recorder import recording_info
from pengujian import ekspor
from tampilan import gambar_jejak
from tampilan import theme

FPS = getattr(config, "FPS", 10)


class _Tombol:
    def __init__(self, rect, label, warna, font_size=18):
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
        pygame.draw.rect(screen, isi, self.rect, border_radius=10)
        pygame.draw.rect(screen, theme.BORDER if self.enabled else theme.TEXT_DIM,
                         self.rect, 2, border_radius=10)
        theme.fit_text(screen, self.label, self.rect.center,
                       self.rect.width - 12, self.font_size,
                       theme.TEXT if self.enabled else theme.TEXT_DIM, bold=True)


def metadata(path):
    """Baca metadata rekaman lewat backend; tidak pernah melempar exception ke UI."""
    info = recording_info(path)
    if not info["valid"]:
        return {"error": info["error"] or "rekaman tidak valid"}
    return {
        "name": info["name"], "count": info["count"], "ticks": info["duration"],
        "rate": info["tick_rate"], "algorithm": "-", "version": info["version"],
        "error": None,
    }


def _teks(screen, msg, size, color, center, bold=False):
    theme.text(screen, msg, size, color, center, bold=bold)


def show_playback_config(screen, session):
    """Kembalikan dict {path, algorithm} atau 'back' / 'quit'."""
    pygame.display.set_caption("Pac-Man AI: Playback")
    w, h = screen.get_size()
    clock = pygame.time.Clock()
    s = min(h / 720.0, w / 1280.0)
    cx = w // 2
    session.refresh()
    indeks = [session.selected_index]
    algoritma = [str(session.algorithm).lower()]
    if algoritma[0] not in ("bfs", "astar"):
        algoritma[0] = "bfs"
    cache = {}

    lebar = min(int(760 * s), w - 40)
    tinggi = min(int(600 * s), h - 40)
    panel = pygame.Rect(cx - lebar // 2, h // 2 - tinggi // 2, lebar, tinggi)
    list_rects = [pygame.Rect(panel.left + int(40 * s),
                              panel.top + int(150 * s) + i * int(44 * s),
                              panel.width - int(80 * s), int(36 * s))
                  for i in range(5)]
    btn_w, btn_h = int(200 * s), int(50 * s)
    algo_w = int(150 * s)
    algo_y = panel.bottom - int(150 * s)
    bfs = _Tombol((cx - algo_w - int(8 * s), algo_y, algo_w, btn_h),
                  "BFS", theme.BFS)
    astar = _Tombol((cx + int(8 * s), algo_y, algo_w, btn_h),
                    "A*", theme.ASTAR)
    play = _Tombol((cx - btn_w - int(10 * s), panel.bottom - int(82 * s),
                    btn_w, btn_h), "PLAY", theme.SUCCESS)
    back = _Tombol((cx + int(10 * s), panel.bottom - int(82 * s),
                    btn_w, btn_h), "BACK", theme.SURFACE_2)

    def info(path):
        if path not in cache:
            cache[path] = metadata(path)
        return cache[path]

    def hasil():
        if not session.paths:
            return None
        return {"path": session.paths[indeks[0]], "algorithm": algoritma[0]}

    while True:
        sesi_paths = session.paths
        if sesi_paths:
            indeks[0] = max(0, min(indeks[0], len(sesi_paths) - 1))
        play.enabled = bool(sesi_paths)
        for event in pygame.event.get():
            audio.handle_event(event)
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    return "back"
                if event.key == pygame.K_q:
                    return "quit"
                if event.key in (pygame.K_UP, pygame.K_DOWN):
                    if sesi_paths:
                        arah = -1 if event.key == pygame.K_UP else 1
                        indeks[0] = (indeks[0] + arah) % len(sesi_paths)
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    algoritma[0] = "astar" if algoritma[0] == "bfs" else "bfs"
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if play.enabled:
                        return hasil()
            for i, r in enumerate(list_rects):
                if (sesi_paths and event.type == pygame.MOUSEBUTTONDOWN
                        and event.button == 1 and r.collidepoint(event.pos)):
                    idx = max(0, indeks[0] - 2) + i
                    if 0 <= idx < len(sesi_paths):
                        indeks[0] = idx
            if bfs.clicked(event):
                algoritma[0] = "bfs"
            if astar.clicked(event):
                algoritma[0] = "astar"
            if play.clicked(event):
                return hasil()
            if back.clicked(event):
                return "back"

        screen.fill(theme.BG_DEEP)
        theme.panel(screen, panel, fill=theme.SURFACE, border=theme.BORDER,
                    radius=18, width=2)
        _teks(screen, "INPUT PLAYBACK", int(34 * s), theme.BFS,
              (cx, panel.top + int(44 * s)), bold=True)
        _teks(screen, "Pilih rekaman + algoritma pertama; algoritma lainnya otomatis menyusul",
              int(14 * s), theme.TEXT_MUTED, (cx, panel.top + int(76 * s)))

        if not sesi_paths:
            _teks(screen, "Belum ada rekaman. Gunakan RECORD MODE dulu.",
                  int(17 * s), theme.ASTAR, (cx, panel.top + int(220 * s)))
        mul = max(0, indeks[0] - 2)
        for i, r in enumerate(list_rects):
            idx = mul + i
            if idx >= len(sesi_paths):
                continue
            nama = os.path.basename(sesi_paths[idx])
            aktif = idx == indeks[0]
            warna = theme.SURFACE_2 if aktif else theme.BG_DEEP
            pygame.draw.rect(screen, warna, r, border_radius=8)
            pygame.draw.rect(screen, theme.BFS if aktif else theme.BORDER, r,
                             2 if aktif else 1, border_radius=8)
            theme.fit_text(screen, ("\u25b6 " if aktif else "  ") + nama,
                           r.center, r.width - 12, int(15 * s),
                           theme.TEXT if aktif else theme.TEXT_MUTED)

        if sesi_paths:
            meta = info(sesi_paths[indeks[0]])
            if meta.get("error"):
                isi = "File rusak: {0}".format(meta["error"][:60])
            else:
                isi = ("NAMA: {0}   |   INPUT: {1}   |   DURASI: {2} tick"
                       "   |   TICK RATE: {3}   |   SCHEMA v{4}").format(
                           meta["name"], meta["count"], meta["ticks"],
                           meta["rate"], meta["version"])
            theme.fit_text(screen, isi, (cx, panel.bottom - int(178 * s)),
                           lebar - int(40 * s), int(14 * s), theme.TEXT_DIM)

        bfs.draw(screen)
        astar.draw(screen)
        pygame.draw.rect(screen, theme.warna_algoritma(algoritma[0]),
                         (bfs.rect.left - 4, algo_y - 4,
                          astar.rect.right - bfs.rect.left + 8, btn_h + 8), 2,
                         border_radius=12)
        play.draw(screen)
        back.draw(screen)
        _teks(screen, "\u2191/\u2193 rekaman   \u2190/\u2192 algoritma   ENTER play   ESC back",
              int(13 * s), theme.TEXT_DIM, (cx, h - int(22 * s)))
        pygame.display.flip()
        clock.tick(FPS)


def show_playback_result(screen, result):
    """Halaman hasil playback, terpisah dari gameplay."""
    pygame.display.set_caption("Pac-Man AI: Hasil Playback")
    result = result or {}
    w, h = screen.get_size()
    clock = pygame.time.Clock()
    s = min(h / 720.0, w / 1280.0)
    cx = w // 2
    algo = str(result.get("algorithm", "bfs")).lower()
    warna = theme.warna_algoritma(algo)
    lain = "A*" if algo == "bfs" else "BFS"

    lebar = min(int(720 * s), w - 40)
    tinggi = min(int(560 * s), h - 40)
    panel = pygame.Rect(cx - lebar // 2, h // 2 - tinggi // 2, lebar, tinggi)
    btn_w, btn_h = int(205 * s), int(52 * s)
    gap = int(12 * s)
    x0 = cx - (3 * btn_w + 2 * gap) // 2
    tombol = [
        (_Tombol((x0, panel.bottom - int(78 * s), btn_w, btn_h),
                 "PLAY AGAIN", theme.SUCCESS), "play_again"),
        (_Tombol((x0 + btn_w + gap, panel.bottom - int(78 * s), btn_w, btn_h),
                 "GANTI KE " + lain, warna), "change_algo"),
        (_Tombol((x0 + 2 * (btn_w + gap), panel.bottom - int(78 * s),
                  btn_w, btn_h), "KE MENU", theme.SURFACE_2), "menu"),
    ]

    while True:
        for event in pygame.event.get():
            audio.handle_event(event)
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    return "menu"
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_r):
                    return "play_again"
                if event.key == pygame.K_c:
                    return "change_algo"
            for btn, nilai in tombol:
                if btn.clicked(event):
                    return nilai

        screen.fill(theme.BG_DEEP)
        theme.panel(screen, panel, fill=theme.SURFACE, border=theme.BORDER,
                    radius=18, width=2)
        _teks(screen, "HASIL PLAYBACK", int(34 * s), warna,
              (cx, panel.top + int(48 * s)), bold=True)

        stats = result.get("stats", {})
        baris = [
            ("RECORDING", str(result.get("recording", "-"))),
            ("ALGORITMA GHOST", theme.label_algoritma(algo)),
            ("STATUS", str(result.get("status", "-")).upper()),
            ("KONDISI GAME", str(result.get("winner", "-")).upper()),
            ("INPUT DITERAPKAN", str(result.get("input_count", 0))),
            ("TICK", str(result.get("ticks", 0))),
            ("WAKTU PENCARIAN", "{0:.3f} ms".format(
                float(stats.get("search_time_ms", 0.0)))),
            ("SIMPUL EKSPLORASI", str(stats.get("nodes_explored", 0))),
            ("PANJANG JALUR", str(stats.get("path_length", 0))),
        ]
        for i, (label, nilai) in enumerate(baris):
            y = panel.top + int(104 * s) + i * int(38 * s)
            font_label = theme.font(max(9, int(14 * s)), bold=True)
            surf = font_label.render(label, True, theme.TEXT_DIM)
            screen.blit(surf, (panel.left + int(34 * s),
                               y - surf.get_height() / 2))
            theme.fit_text(screen, nilai,
                           (panel.left + int(400 * s), y),
                           int(280 * s), int(17 * s), warna if i in (1, 2, 3)
                           else theme.TEXT, bold=True)

        if result.get("csv_info"):
            _teks(screen, str(result["csv_info"]), max(9, int(12 * s)),
                  theme.TEXT_DIM, (cx, panel.bottom - int(100 * s)))
        for btn, _ in tombol:
            btn.draw(screen)
        _teks(screen, "ENTER play lagi   C ganti algoritma   ESC menu",
              int(13 * s), theme.TEXT_DIM, (cx, h - int(22 * s)))
        pygame.display.flip()
        clock.tick(FPS)


def show_playback_pair_result(screen, session, hasil_list):
    """Hasil satu uji: BFS dan A* pada rekaman yang sama + tombol EXPORT CSV.

    Mengembalikan 'again' (uji rekaman lain), 'menu', atau 'quit'. EXPORT CSV
    menulis SEMUA hasil sesi ini (semua uji) ke satu file CSV.
    """
    pygame.display.set_caption("Pac-Man AI: Hasil Uji BFS vs A*")
    w, h = screen.get_size()
    clock = pygame.time.Clock()
    s = min(h / 720.0, w / 1280.0)
    cx = w // 2
    hasil_list = [r for r in (hasil_list or []) if r]
    per_algo = {str(r.get("algorithm", "")).lower(): r for r in hasil_list}
    contoh = hasil_list[0] if hasil_list else {}

    lebar = min(int(780 * s), w - 40)
    tinggi = min(int(600 * s), h - 40)
    panel = pygame.Rect(cx - lebar // 2, h // 2 - tinggi // 2, lebar, tinggi)
    btn_w, btn_h = int(178 * s), int(52 * s)
    gap = int(10 * s)
    x0 = cx - (4 * btn_w + 3 * gap) // 2
    y_btn = panel.bottom - int(78 * s)
    tombol = [
        (_Tombol((x0, y_btn, btn_w, btn_h), "EXPORT CSV", theme.SUCCESS), "export"),
        (_Tombol((x0 + (btn_w + gap), y_btn, btn_w, btn_h), "GAMBAR",
                 theme.WALL), "gambar"),
        (_Tombol((x0 + 2 * (btn_w + gap), y_btn, btn_w, btn_h), "UJI LAGI",
                 theme.warna_algoritma("bfs")), "again"),
        (_Tombol((x0 + 3 * (btn_w + gap), y_btn, btn_w, btn_h), "KE MENU",
                 theme.SURFACE_2), "menu"),
    ]
    tampil_gambar = False
    game_per_algo = {kode: r.get("_game") for kode, r in per_algo.items()}
    cache_gambar = {}

    def gambar_algo(kode, sisi):
        game = game_per_algo.get(kode)
        if game is None:
            return None, None
        if kode not in cache_gambar:
            data = game.data_jejak(0)
            cache_gambar[kode] = (data, gambar_jejak.buat_gambar(data, sisi))
        return cache_gambar[kode]

    kolom_x = {"label": panel.left + int(34 * s),
               "bfs": panel.left + int(470 * s),
               "astar": panel.left + int(640 * s)}
    baris = [
        ("PEMENANG", lambda r: str(r.get("winner", "-")).upper()),
        ("INPUT DITERAPKAN", lambda r: str(r.get("input_count", 0))),
        ("TICK", lambda r: str(r.get("ticks", 0))),
        ("WAKTU PENCARIAN", lambda r: "{0:.3f} ms".format(
            float((r.get("stats") or {}).get("search_time_ms", 0.0)))),
        ("SIMPUL EKSPLORASI", lambda r: str((r.get("stats") or {}).get("nodes_explored", 0))),
        ("PANJANG JALUR", lambda r: str((r.get("stats") or {}).get("path_length", 0))),
    ]

    pesan, pesan_err, jalur_info = "", False, ""

    def lakukan_ekspor():
        hasil = ekspor.ekspor_semua_csv(session.results)
        if not hasil["ok"]:
            return "CSV gagal: " + hasil["error"], True, ""
        teks = "CSV tersimpan: {0} ({1} hasil, {2} uji)".format(
            os.path.basename(hasil["path"]), hasil["baris"], hasil["uji"])
        if hasil["belum_lengkap"]:
            teks += " | {0} uji belum punya BFS dan A*".format(hasil["belum_lengkap"])
        # Gambar jalur/jejak tiap hasil ikut disimpan sebagai PNG.
        daftar = []
        for item in ekspor.urutkan(session.results):
            r = item["hasil"]
            game = r.get("_game")
            if game is None:
                continue
            st = r.get("stats") or {}
            daftar.append((
                gambar_jejak.nama_file("uji{0:02d}".format(item["no_uji"]),
                                       "maze{0}".format(item["maze_id"]),
                                       r.get("recording", ""), ekspor.nama_algo(r)),
                game.data_jejak(0),
                "{0} | rekaman: {1}".format(ekspor.nama_maze(r), r.get("recording", "")),
                ["{0} | Pemenang: {1}".format(ekspor.nama_algo(r),
                                              str(r.get("winner", "-")).capitalize()),
                 "Waktu {0:.3f} ms | Simpul {1} | Jalur {2} langkah".format(
                     float(st.get("search_time_ms", 0.0)), st.get("nodes_explored", 0),
                     st.get("path_length", 0))]))
        if daftar:
            folder = os.path.join(os.path.dirname(hasil["path"]),
                                  "gambar_" + hasil["stempel"])
            n, err = gambar_jejak.simpan_banyak(daftar, folder)
            teks += " | {0} gambar PNG di {1}".format(n, os.path.basename(folder)) if n \
                else " | gambar gagal: {0}".format(err)
        return teks, False, hasil["path"]

    while True:
        for event in pygame.event.get():
            audio.handle_event(event)
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    return "menu"
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_r):
                    return "again"
                if event.key == pygame.K_e:
                    pesan, pesan_err, jalur_info = lakukan_ekspor()
                if event.key == pygame.K_g:
                    tampil_gambar = not tampil_gambar
            for btn, nilai in tombol:
                if btn.clicked(event):
                    if nilai == "export":
                        pesan, pesan_err, jalur_info = lakukan_ekspor()
                    elif nilai == "gambar":
                        tampil_gambar = not tampil_gambar
                    else:
                        return nilai
        tombol[1][0].label = "ANGKA" if tampil_gambar else "GAMBAR"

        screen.fill(theme.BG_DEEP)
        theme.panel(screen, panel, fill=theme.SURFACE, border=theme.BORDER,
                    radius=18, width=2)
        _teks(screen, "HASIL UJI  BFS vs A*", int(30 * s), theme.TEXT,
              (cx, panel.top + int(40 * s)), bold=True)
        theme.fit_text(screen, "{0}   |   rekaman: {1}".format(
            ekspor.nama_maze(contoh), contoh.get("recording", "-")),
            (cx, panel.top + int(78 * s)), lebar - int(40 * s), int(15 * s),
            theme.TEXT_MUTED)

        y_head = panel.top + int(118 * s)
        if tampil_gambar:
            sisi = min((lebar - int(90 * s)) // 2, int(290 * s))
            atas = panel.top + int(100 * s)
            pusat_x = {"bfs": cx - sisi // 2 - int(14 * s),
                       "astar": cx + sisi // 2 + int(14 * s)}
            data_contoh = None
            for kode, label in (("bfs", "BFS"), ("astar", "A*")):
                data, surf_gambar = gambar_algo(kode, sisi)
                if surf_gambar is None:
                    _teks(screen, label + ": belum ada gambar", int(14 * s),
                          theme.TEXT_DIM, (pusat_x[kode], atas + sisi // 2))
                    continue
                data_contoh = data
                screen.blit(surf_gambar, surf_gambar.get_rect(
                    midtop=(pusat_x[kode], atas)))
                bawah = atas + surf_gambar.get_height()
                if data["kondisi"] == "bergerak":
                    ket = "hantu {0} langkah".format(len(data["jejak_hantu"]) - 1)
                else:
                    ket = "jalur {0} langkah".format(len(data["path_awal"]) - 1)
                _teks(screen, "{0}: {1}".format(label, ket), int(15 * s),
                      theme.warna_algoritma(kode), (pusat_x[kode], bawah + int(14 * s)),
                      bold=True)
                _teks(screen, "Pemenang: " + str(per_algo[kode].get("winner", "-")).capitalize(),
                      int(13 * s), theme.TEXT_MUTED, (pusat_x[kode], bawah + int(32 * s)))
            if data_contoh is not None:
                theme.fit_text(screen, gambar_jejak.legenda(data_contoh),
                               (cx, atas + sisi + int(50 * s)), lebar - int(30 * s),
                               int(12 * s), theme.TEXT_DIM)
        else:
            for kode, label in (("bfs", "BFS"), ("astar", "A*")):
                _teks(screen, label, int(20 * s), theme.warna_algoritma(kode),
                      (kolom_x[kode], y_head), bold=True)
            for i, (label, ambil) in enumerate(baris):
                y = y_head + int(38 * s) + i * int(38 * s)
                surf = theme.font(max(9, int(14 * s)), bold=True).render(
                    label, True, theme.TEXT_DIM)
                screen.blit(surf, (kolom_x["label"], y - surf.get_height() / 2))
                for kode in ("bfs", "astar"):
                    r = per_algo.get(kode)
                    theme.fit_text(screen, ambil(r) if r else "-", (kolom_x[kode], y),
                                   int(150 * s), int(17 * s), theme.TEXT, bold=True)

        info = ekspor.ringkasan(session.results)
        _teks(screen, "Uji tercatat: {0} / {1}   |   {2} hasil".format(
            info["uji"], ekspor.TARGET_UJI, info["baris"]),
            int(15 * s), theme.TEXT_MUTED, (cx, y_btn - int(62 * s)), bold=True)
        if pesan:
            theme.fit_text(screen, pesan, (cx, y_btn - int(38 * s)),
                           lebar - int(30 * s), int(13 * s),
                           theme.DANGER if pesan_err else theme.SUCCESS)
        if jalur_info:
            theme.fit_text(screen, jalur_info, (cx, y_btn - int(18 * s)),
                           lebar - int(30 * s), int(11 * s), theme.TEXT_DIM)

        for btn, _ in tombol:
            btn.draw(screen)
        _teks(screen, "E export CSV   G gambar/angka   ENTER uji lagi   ESC menu",
              int(13 * s), theme.TEXT_DIM, (cx, h - int(22 * s)))
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    pygame.init()
    layar = pygame.display.set_mode((1000, 700))
    print(show_playback_result(layar, {
        "recording": "contoh", "algorithm": "bfs", "status": "completed",
        "winner": "pacman", "input_count": 6, "ticks": 16,
        "stats": {"search_time_ms": 0.42, "nodes_explored": 120,
                  "path_length": 18},
    }))
    pygame.quit()
