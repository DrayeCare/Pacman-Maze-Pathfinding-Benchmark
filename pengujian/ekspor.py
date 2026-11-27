"""Ekspor hasil pengujian playback (Pac-Man bergerak) ke SATU file CSV.

Alurnya: tiap rekaman diputar dengan BFS dan A* (otomatis, rekaman yang sama
supaya adil). Hasilnya terkumpul di session.results. Tombol EXPORT CSV memanggil
ekspor_semua_csv() sehingga semua uji (mis. 9 uji x 2 algoritma = 18 baris)
tertulis sekaligus ke satu file di folder hasil_pengujian/.
"""

import csv
import datetime
import os

from core import config

FOLDER_HASIL = os.path.join(config.BASE_DIR, "hasil_pengujian")
TARGET_UJI = 9  # 3 uji per maze x 3 maze; ubah di sini kalau targetnya berbeda

# Format CSV untuk Excel berbahasa Indonesia: pemisah kolom ";" dan desimal ",".
# Baris pertama "sep=;" memaksa Excel memecah kolom (tanpa ini semua isi menumpuk
# di kolom A). Kalau Excel kamu memakai desimal titik, ganti DESIMAL = ".".
PEMISAH = ";"
DESIMAL = ","

KOLOM = [
    "No Uji", "Maze", "Uji ke- di Maze", "Rekaman", "Algoritma", "Status",
    "Pemenang", "Input Diterapkan", "Tick", "Waktu Pencarian (ms)",
    "Simpul Dieksplorasi", "Panjang Jalur (Langkah)", "Desync",
    "Posisi Awal Pac-Man", "Posisi Awal Ghost",
]

_NAMA_PEMENANG = {"pacman": "Pac-Man", "ghost": "Ghost"}
_NAMA_STATUS = {"ended": "Selesai", "completed": "Input habis"}


def _fmt_pos(pos):
    """[1, 1] -> '(1,1)' ; [[18, 19], [3, 4]] -> '(18,19) | (3,4)'."""
    try:
        if pos and isinstance(pos[0], (list, tuple)):
            return " | ".join("({0},{1})".format(p[0], p[1]) for p in pos)
        return "({0},{1})".format(pos[0], pos[1])
    except (TypeError, IndexError):
        return ""


def _fmt_desimal(angka, digit=3):
    return "{0:.{1}f}".format(float(angka), digit).replace(".", DESIMAL)


def _maze_id(hasil):
    maze_file = (hasil.get("initial_state") or {}).get("maze_file") or ""
    for kunci, path in config.MAZE_FILES.items():
        if os.path.basename(maze_file) == os.path.basename(path):
            return kunci
    return None


def nama_maze(hasil):
    return config.MAZE_TITLES.get(_maze_id(hasil), "Maze tidak diketahui")


def maze_id(hasil):
    return _maze_id(hasil)


def nama_algo(hasil):
    return _nama_algo(hasil)


def _kode_algo(hasil):
    return str(hasil.get("algorithm", "")).lower()


def _nama_algo(hasil):
    return {"bfs": "BFS", "astar": "A*"}.get(_kode_algo(hasil),
                                              str(hasil.get("algorithm", "")))


def _valid(results):
    """Playback yang dihentikan di tengah (STOP/ESC) bukan uji yang sah."""
    return [r for r in (results or []) if r.get("status") != "stopped"]


def _urut(hasil):
    mid = _maze_id(hasil)
    return (mid if mid is not None else 99, str(hasil.get("recording", "")),
            0 if _kode_algo(hasil) == "bfs" else 1)


def urutkan(results):
    """Hasil valid yang sudah berurutan + penomoran uji (sama dengan isi CSV).

    Mengembalikan list dict: {"no_uji", "uji_di_maze", "maze_id", "hasil"}.
    """
    daftar, no_uji, per_maze, sebelum = [], 0, {}, None
    for r in sorted(_valid(results), key=_urut):
        kunci = (_maze_id(r), r.get("recording"))
        if kunci != sebelum:
            no_uji += 1
            per_maze[kunci[0]] = per_maze.get(kunci[0], 0) + 1
            sebelum = kunci
        daftar.append({"no_uji": no_uji, "uji_di_maze": per_maze[kunci[0]],
                       "maze_id": kunci[0], "hasil": r})
    return daftar


def ringkasan(results):
    """Hitung uji (rekaman) dan hasil yang siap diekspor."""
    valid = _valid(results)
    grup = {}
    for r in valid:
        grup.setdefault((_maze_id(r), r.get("recording")), set()).add(_kode_algo(r))
    lengkap = sum(1 for algo in grup.values() if {"bfs", "astar"} <= algo)
    return {"uji": len(grup), "baris": len(valid),
            "belum_lengkap": len(grup) - lengkap}


def ekspor_semua_csv(results, folder=None):
    """Tulis semua hasil ke satu CSV baru (nama berstempel waktu, tidak menimpa).

    Mengembalikan dict: {"ok": True, "path", "baris", "uji", "belum_lengkap"}
    atau {"ok": False, "error": pesan}. Tidak pernah melempar error ke UI.
    """
    if not _valid(results):
        return {"ok": False, "error": "Belum ada hasil uji untuk diekspor."}

    baris = []
    for item in urutkan(results):
        r, no_uji = item["hasil"], item["no_uji"]
        stats = r.get("stats") or {}
        awal = r.get("initial_state") or {}
        pemenang = str(r.get("winner", ""))
        baris.append([
            no_uji, nama_maze(r), item["uji_di_maze"], r.get("recording", ""),
            _nama_algo(r),
            _NAMA_STATUS.get(r.get("status", ""), r.get("status", "")),
            _NAMA_PEMENANG.get(pemenang, pemenang.capitalize()),
            r.get("input_count", 0), r.get("ticks", 0),
            _fmt_desimal(stats.get("search_time_ms", 0.0)),
            int(stats.get("nodes_explored", 0)), int(stats.get("path_length", 0)),
            r.get("desync_count", 0),
            _fmt_pos(awal.get("player")), _fmt_pos(awal.get("ghosts")),
        ])

    folder = folder or FOLDER_HASIL
    cap = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        os.makedirs(folder, exist_ok=True)
        for i in range(100):
            suffix = "" if i == 0 else "_{0:02d}".format(i)
            path = os.path.join(folder, "hasil_pengujian_{0}{1}.csv".format(cap, suffix))
            try:
                f = open(path, "x", newline="", encoding="utf-8-sig")
            except FileExistsError:
                continue
            with f:
                f.write("sep={0}\n".format(PEMISAH))
                writer = csv.writer(f, delimiter=PEMISAH)
                writer.writerow(KOLOM)
                writer.writerows(baris)
            break
        else:
            return {"ok": False, "error": "Gagal membuat nama file yang unik."}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}

    info = ringkasan(results)
    return {"ok": True, "path": path, "baris": len(baris), "uji": info["uji"],
            "belum_lengkap": info["belum_lengkap"], "stempel": cap}
