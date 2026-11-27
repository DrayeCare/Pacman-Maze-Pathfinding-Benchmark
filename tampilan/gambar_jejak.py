"""tampilan/gambar_jejak.py - gambar maze + jalur/jejak hantu untuk hasil akhir.

Hanya memakai pygame (tanpa PIL), jadi bisa dipakai di layar maupun disimpan PNG.

Dua jenis gambar (dipilih dari data["kondisi"]):
  * Pac-Man DIAM    : garis = jalur hantu dari awal ke Pac-Man,
                      petak redup = area yang dieksplorasi algoritma.
  * Pac-Man BERGERAK: garis putih = jejak Pac-Man, garis berwarna = jejak
                      hantu, petak pekat = petak yang dilewati hantu berulang.
Data berasal dari Game.data_jejak().
"""

import os
import re
from collections import Counter

import pygame

from tampilan import theme

PUTIH = (235, 235, 245)

LEGENDA_DIAM = "garis = jalur hantu (H ke P) | petak redup = area dieksplorasi"
LEGENDA_BERGERAK = ("putih = jejak Pac-Man | warna = jejak hantu | "
                    "petak pekat = dilewati hantu berulang")


def _pusat(p, cell):
    return (int(p[1] * cell + cell / 2), int(p[0] * cell + cell / 2))


def _garis(surf, titik, warna, tebal, cell):
    pts = [_pusat(p, cell) for p in titik]
    if len(pts) >= 2:
        pygame.draw.lines(surf, warna, False, pts, max(1, int(tebal)))
    elif len(pts) == 1:
        pygame.draw.circle(surf, warna, pts[0], max(1, int(tebal)))


def _sel_redup(surf, sel, warna, alpha, cell):
    if not sel:
        return
    lapisan = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for r, c in sel:
        pygame.draw.rect(lapisan, tuple(warna) + (alpha,),
                         (c * cell + 1, r * cell + 1, cell - 2, cell - 2))
    surf.blit(lapisan, (0, 0))


def _bulat(surf, pos, warna, huruf, cell):
    pusat = _pusat(pos, cell)
    radius = max(cell // 2, 3)
    pygame.draw.circle(surf, warna, pusat, radius)
    pygame.draw.circle(surf, PUTIH, pusat, radius, 1)
    if huruf and cell >= 9:
        teks = theme.font(max(9, int(cell * 0.8)), True).render(huruf, True, (0, 0, 0))
        surf.blit(teks, teks.get_rect(center=pusat))


def buat_gambar(data, ukuran):
    """Gambar maze + jalur/jejak sebagai Surface persegi (sisi ~ `ukuran` px)."""
    grid = data["grid"]
    n, m = len(grid), len(grid[0])
    cell = max(int(ukuran) // max(n, m), 3)
    surf = pygame.Surface((cell * m, cell * n))
    surf.fill(theme.PATH)
    for r, baris in enumerate(grid):
        for c, nilai in enumerate(baris):
            if nilai == 1:
                pygame.draw.rect(surf, theme.WALL, (c * cell, r * cell, cell, cell))

    warna = theme.warna_algoritma(data.get("algoritma", ""))
    er, ec = data["exit"]
    pad = max(cell // 5, 1)
    pygame.draw.rect(surf, theme.EXIT, (ec * cell + pad, er * cell + pad,
                                        cell - 2 * pad, cell - 2 * pad))

    if data.get("kondisi") != "bergerak":
        # Pac-Man DIAM: jalur rencana + area dieksplorasi.
        _sel_redup(surf, data.get("visited_awal"), warna, 70, cell)
        path = data.get("path_awal") or []
        _garis(surf, path, warna, cell // 3, cell)
        if path:
            _bulat(surf, path[-1], theme.PACMAN, "P", cell)
            _bulat(surf, path[0], theme.GHOST_RED, "H", cell)
    else:
        # Pac-Man BERGERAK: jejak nyata keduanya.
        jp = data.get("jejak_pacman") or []
        jh = data.get("jejak_hantu") or []
        ulang = [p for p, k in Counter(jh).items() if k > 1]
        _sel_redup(surf, ulang, warna, 95, cell)
        _garis(surf, jp, PUTIH, max(2, cell // 3), cell)
        _garis(surf, jh, warna, max(1, cell // 5), cell)
        if jh:
            _bulat(surf, jh[0], theme.GHOST_RED, "S", cell)
        if jp:
            _bulat(surf, jp[0], theme.PACMAN, "S", cell)
            if data.get("hasil") == "kalah":
                _bulat(surf, jp[-1], PUTIH, "X", cell)
    return surf


def legenda(data):
    return LEGENDA_BERGERAK if data.get("kondisi") == "bergerak" else LEGENDA_DIAM


def _bersih(nama):
    teks = str(nama).replace("*", "star")  # "A*" -> "Astar"
    return re.sub(r"[^A-Za-z0-9_-]+", "_", teks).strip("_") or "x"


def nama_file(*bagian):
    return "_".join(_bersih(b) for b in bagian) + ".png"


def simpan_png(data, path, judul, baris_info, ukuran=560):
    """Simpan gambar + judul + keterangan sebagai PNG. -> (True, path) / (False, pesan)."""
    try:
        gambar = buat_gambar(data, ukuran)
        margin, tinggi_judul = 16, 40
        baris = list(baris_info) + [legenda(data)]
        tinggi_info = 22 * len(baris) + 10
        kanvas = pygame.Surface((gambar.get_width() + 2 * margin,
                                 gambar.get_height() + tinggi_judul + tinggi_info))
        kanvas.fill(theme.BG_DEEP)
        teks = theme.font(18, True).render(str(judul), True, theme.TEXT)
        kanvas.blit(teks, (margin, 10))
        kanvas.blit(gambar, (margin, tinggi_judul))
        y = tinggi_judul + gambar.get_height() + 8
        for i, kalimat in enumerate(baris):
            warna = theme.TEXT_DIM if i == len(baris) - 1 else theme.TEXT_MUTED
            kanvas.blit(theme.font(13).render(str(kalimat), True, warna), (margin, y))
            y += 22
        os.makedirs(os.path.dirname(path), exist_ok=True)
        pygame.image.save(kanvas, path)
        return True, path
    except (OSError, pygame.error) as exc:
        return False, str(exc)


def simpan_banyak(daftar, folder):
    """daftar: [(nama_file, data, judul, baris_info)]. -> (jumlah_berhasil, pesan_error)."""
    ok, error = 0, ""
    for nama, data, judul, info in daftar:
        sukses, pesan = simpan_png(data, os.path.join(folder, nama), judul, info)
        if sukses:
            ok += 1
        elif not error:
            error = pesan
    return ok, error
