"""tampilan/ui_spawn.py — editor GUI posisi awal dan biaya petak.

Pemain bisa mengklik petak mana pun yang bisa dilewati untuk menempatkan
Pac-Man, Ghost BFS, Ghost A*, dan Exit, serta memberi biaya (cost) pada petak.
Mode duel bisa memakai satu titik ghost bersama atau dua titik terpisah.
Hasil dipakai langsung oleh Game dan disimpan ke settings.json.
"""

import json

import pygame

from core import audio
from core import config
from core.game import (muat_biaya, muat_mode_ghost, simpan_biaya,
                       simpan_pengaturan_spawn, tentukan_spawn)
from tampilan import theme
from tampilan import visual

FPS = getattr(config, "FPS", 60)


def _muat_grid(maze_path):
    with open(maze_path, "r", encoding="utf-8") as f:
        return json.load(f)["grid"]


def _bisa(grid, r, c):
    return (0 <= r < len(grid) and 0 <= c < len(grid[0])
            and grid[r][c] != 1)


def _sel_dari_piksel(layout, grid, mouse):
    if not layout["play_rect"].collidepoint(mouse):
        return None
    t = layout["tile"]
    c = (mouse[0] - layout["origin_x"]) // t
    r = (mouse[1] - layout["origin_y"]) // t
    if _bisa(grid, r, c):
        return (r, c)
    return None


class _Tombol:
    def __init__(self, rect, label, warna, value, font_size):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.warna = warna
        self.value = value
        self.font_size = font_size

    def clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.rect.collidepoint(event.pos))

    def draw(self, screen, aktif=False):
        hover = self.rect.collidepoint(pygame.mouse.get_pos())
        isi = theme.lighten(self.warna, 20) if hover else self.warna
        pygame.draw.rect(screen, isi, self.rect, border_radius=8)
        pygame.draw.rect(screen, theme.TEXT if aktif else theme.BORDER,
                         self.rect, 3 if aktif else 1, border_radius=8)
        terang = sum(self.warna[:3]) / 3 > 140
        theme.fit_text(screen, self.label, self.rect.center,
                       self.rect.width - 6, self.font_size,
                       theme.BG_DEEP if terang else theme.TEXT, bold=True)


def pilih_spawn(screen, maze_path, duel=False):
    """Tampilkan editor spawn. Return dict pengaturan atau 'back'/'quit'."""
    pygame.display.set_caption("Pac-Man AI: BFS vs A* - Atur Posisi Awal")
    grid = _muat_grid(maze_path)
    layout = visual.hitung_layout(screen.get_size())
    clock = pygame.time.Clock()

    pisah = bool(duel and muat_mode_ghost() == "pisah")
    jumlah_ghost = 2 if pisah else 1
    p, gs, e = tentukan_spawn(grid, jumlah_ghost, None)
    pos = {"pacman": list(p), "bfs": list(gs[0]),
           "astar": list(gs[1] if pisah and len(gs) > 1 else gs[0]),
           "exit": list(e)}
    biaya = dict(muat_biaya())
    nilai_biaya = 2
    pilih = "pacman"

    hud = layout["hud_rect"]
    pad = max(3, hud.width // 90)
    gap = max(2, hud.width // 150)
    tinggi = max(22, int(hud.height * 0.50))
    atas = max(hud.top + 2, hud.bottom - tinggi - max(2, hud.height // 10))

    def bangun_tombol():
        if duel and pisah:
            data = [
                ("PAC-MAN", theme.PACMAN, "pacman"),
                ("BFS", theme.BFS, "bfs"),
                ("A*", theme.ASTAR, "astar"),
                ("EXIT", theme.EXIT, "exit"),
                ("COST", theme.ASTAR, "cost"),
                ("PISAH", theme.SURFACE_2, "toggle"),
                ("RESET", theme.SURFACE_2, "reset"),
                ("ACAK", theme.SURFACE_2, "acak"),
                ("MULAI", theme.SUCCESS, "mulai"),
            ]
        else:
            data = [
                ("PAC-MAN", theme.PACMAN, "pacman"),
                ("GHOST BFS/A*" if duel else "GHOST",
                 theme.ASTAR if duel else theme.GHOST_RED, "bfs"),
                ("EXIT", theme.EXIT, "exit"),
                ("COST", theme.ASTAR, "cost"),
            ]
            if duel:
                data.append(("GABUNG", theme.SURFACE_2, "toggle"))
            data += [("RESET", theme.SURFACE_2, "reset"),
                     ("ACAK", theme.SURFACE_2, "acak"),
                     ("MULAI", theme.SUCCESS, "mulai")]
        jumlah = len(data)
        lebar = max(24, (hud.width - 2 * pad - (jumlah - 1) * gap) // jumlah)
        font = max(7, min(13, int(lebar * 0.24), int(tinggi * 0.55)))
        return [_Tombol((hud.left + pad + i * (lebar + gap), atas, lebar, tinggi),
                        label, warna, value, font)
                for i, (label, warna, value) in enumerate(data)]

    tombol = bangun_tombol()

    def hasil():
        if duel and pisah:
            ghosts = [list(pos["bfs"]), list(pos["astar"])]
        else:
            ghosts = [list(pos["bfs"])]
            if duel:
                ghosts.append(list(pos["bfs"]))
        return {"mode": "manual", "pacman": list(pos["pacman"]),
                "ghosts": ghosts, "exit": list(pos["exit"]),
                "ghost_mode": "pisah" if (duel and pisah) else "sama",
                "costs": [[r, c, v] for (r, c), v in sorted(biaya.items())]}

    def simpan():
        simpan_pengaturan_spawn(hasil())
        simpan_biaya(biaya)

    def set_pisah(baru):
        nonlocal pisah, tombol, pilih
        if not duel:
            return
        pisah = bool(baru)
        if pisah:
            cadangan = ((r, c) for r in range(len(grid))
                        for c in range(len(grid[0])) if _bisa(grid, r, c))
            calon = next((t for t in cadangan
                          if list(t) != pos["bfs"] and list(t) != pos["pacman"]
                          and list(t) != pos["exit"]), None)
            pos["astar"] = list(calon) if calon else list(pos["bfs"])
            if pilih == "bfs":
                pilih = "astar"
        else:
            pos["astar"] = list(pos["bfs"])
            if pilih == "astar":
                pilih = "bfs"
        tombol = bangun_tombol()

    def atur_ulang(mode):
        nonlocal pos
        jumlah = 2 if (duel and pisah) else 1
        p, gs, e = tentukan_spawn(grid, jumlah, {"mode": mode})
        pos = {"pacman": list(p), "bfs": list(gs[0]),
               "astar": list(gs[1] if jumlah > 1 else gs[0]), "exit": list(e)}

    while True:
        for event in pygame.event.get():
            audio.handle_event(event)
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "back"
                if event.key == pygame.K_RETURN:
                    simpan()
                    return hasil()
                if pilih == "cost" and pygame.K_2 <= event.key <= pygame.K_9:
                    # Di mode cost, angka 2-9 = nilai cost, bukan pindah alat.
                    nilai_biaya = event.key - pygame.K_0
                elif event.key == pygame.K_1:
                    pilih = "pacman"
                elif event.key == pygame.K_2:
                    pilih = "bfs"
                elif event.key == pygame.K_3:
                    pilih = "exit"
                elif event.key == pygame.K_4 and duel:
                    if not pisah:
                        set_pisah(True)
                    pilih = "astar"
                elif event.key == pygame.K_g:
                    set_pisah(not pisah)
                elif event.key == pygame.K_c:
                    pilih = "pacman" if pilih == "cost" else "cost"
                elif event.key == pygame.K_h:
                    biaya.clear()
                elif event.key == pygame.K_r:
                    atur_ulang("auto")
                elif event.key == pygame.K_a:
                    atur_ulang("random")
                if pilih == "cost":
                    if event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                        nilai_biaya = min(99, nilai_biaya + 1)
                    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        nilai_biaya = max(1, nilai_biaya - 1)
            for b in tombol:
                if not b.clicked(event):
                    continue
                if b.value == "mulai":
                    simpan()
                    return hasil()
                if b.value == "toggle":
                    set_pisah(not pisah)
                elif b.value == "reset":
                    atur_ulang("auto")
                elif b.value == "acak":
                    atur_ulang("random")
                else:
                    pilih = b.value
            if event.type == pygame.MOUSEBUTTONDOWN:
                sel = _sel_dari_piksel(layout, grid, event.pos)
                if sel is not None:
                    kunci = (sel[0], sel[1])
                    if pilih == "cost":
                        if event.button == 3:
                            biaya.pop(kunci, None)
                        elif event.button == 1:
                            if nilai_biaya > 1:
                                biaya[kunci] = nilai_biaya
                            else:
                                biaya.pop(kunci, None)
                    elif event.button == 1:
                        target = ("bfs", "astar") if (duel and not pisah
                                                     and pilih in ("bfs", "astar")) else (pilih,)
                        lama = next((e for e in ("pacman", "bfs", "astar", "exit")
                                     if list(pos[e]) == [sel[0], sel[1]]
                                     and e not in target), None)
                        if lama is not None:
                            pos[lama] = list(pos[target[0]])
                        for k in target:
                            pos[k] = [sel[0], sel[1]]

        screen.fill(theme.BG_DEEP)
        visual.gambar_maze(screen, layout, grid)
        visual.gambar_biaya(screen, layout, biaya)

        mouse = pygame.mouse.get_pos()
        sel = _sel_dari_piksel(layout, grid, mouse)
        if sel is not None:
            t = layout["tile"]
            x, y = visual.posisi_tile(layout, sel[0], sel[1])
            if pilih == "bfs":
                warna = theme.BFS
            elif pilih == "astar" or pilih == "cost":
                warna = theme.ASTAR
            elif pilih in ("pacman", "exit"):
                warna = theme.SUCCESS
            else:
                warna = theme.DANGER
            pygame.draw.rect(screen, warna, (x, y, t, t), 2)

        radius = max(4, int(layout["tile"] * 0.40))
        px, py = visual.pusat_tile(layout, pos["pacman"][0], pos["pacman"][1])
        visual.gambar_pacman(screen, (px, py), radius, (1, 0), mouth_deg=24,
                             color=theme.PACMAN, bg=theme.PATH, eye=True)

        skala = max(0.8, min(1.4, layout["tile"] / 30.0))
        if duel and pisah:
            for k, warna, label in (("bfs", theme.BFS, "BFS"),
                                    ("astar", theme.ASTAR, "A*")):
                gx, gy = visual.pusat_tile(layout, pos[k][0], pos[k][1])
                visual.gambar_ghost(screen, (gx, gy), radius, (1, 0), color=warna)
                visual.gambar_label_algoritma(
                    screen, (gx, gy - radius - 12), label, warna, skala)
        else:
            gx, gy = visual.pusat_tile(layout, pos["bfs"][0], pos["bfs"][1])
            warna = theme.ASTAR if duel else theme.GHOST_RED
            visual.gambar_ghost(screen, (gx, gy), radius, (1, 0), color=warna)
            if duel:
                pygame.draw.circle(screen, theme.BFS, (gx, gy), radius + 3, 2)
                visual.gambar_label_algoritma_gabungan(
                    screen, (gx, gy - radius - 14), skala)

        ex, ey = visual.pusat_tile(layout, pos["exit"][0], pos["exit"][1])
        visual.gambar_exit(screen, layout, pos["exit"])

        pygame.draw.rect(screen, theme.BG_DEEP, hud)
        pygame.draw.line(screen, theme.BORDER, (hud.left, hud.top),
                         (hud.right, hud.top), 2)
        if pilih == "cost":
            petunjuk = ("MODE COST: 2-9 nilai ({0}) | +/- atur | klik petak pasang | "
                        "klik kanan hapus | H hapus semua | C keluar | ENTER mulai").format(nilai_biaya)
        elif duel:
            petunjuk = ("1 Pac-Man | 2 BFS | 3 Exit | 4 A* | C cost | G "
                        "{0} | R reset | A acak | ENTER mulai").format(
                            "PISAH" if pisah else "GABUNG")
        else:
            petunjuk = ("1 Pac-Man | 2 Ghost | 3 Exit | C cost | "
                        "R reset | A acak | ENTER mulai | ESC kembali")
        theme.fit_text(screen, petunjuk, (hud.centerx, hud.top + max(7, hud.height // 5)),
                       hud.width - 10, max(9, int(hud.height * 0.18)),
                       theme.TEXT_DIM, bold=True)
        for b in tombol:
            b.draw(screen, aktif=(b.value == pilih))

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    pygame.init()
    layar = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    print("Hasil:", pilih_spawn(layar, config.MAZE_FILES[1], True))
    pygame.quit()
