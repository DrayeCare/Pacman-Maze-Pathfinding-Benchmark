import copy
import json
import math
import os
import random
from collections import deque

import pygame

from algoritma.astar import cari_jalur_astar
from algoritma.bfs import cari_jalur_bfs
from core import config
from core import audio
from tampilan import theme
from tampilan.ui_setting import get_movement_keys
from tampilan.visual import (gambar_biaya, gambar_exit, gambar_ghost,
                             gambar_hud, gambar_label_algoritma,
                             gambar_label_algoritma_gabungan, gambar_maze,
                             gambar_pacman, gambar_path_aktif, gambar_visited,
                             hitung_layout, pusat_tile)

SEARCH = {"bfs": cari_jalur_bfs, "astar": cari_jalur_astar}
PACMAN_PATHFINDER = cari_jalur_bfs

# Penempatan spawn deterministik: lihat _pilih_spawn(). Jarak diukur melalui
# jalur walkable dengan BFS lokal, bukan Manhattan/Euclidean, dan tidak
# mengubah file maze JSON.
SPAWN_MIN_TARGET = 30
SPAWN_MIN_INTERSECTIONS = 5


def _peta_spawn(grid, start):
    """BFS lokal: (jarak, induk) untuk validasi spawn; tidak memakai SEARCH."""
    if grid[start[0]][start[1]] == 1:
        return {}, {}
    baris, kolom = len(grid), len(grid[0])
    jarak = {start: 0}
    induk = {start: None}
    antrean = deque([start])
    while antrean:
        r, c = antrean.popleft()
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if (0 <= nr < baris and 0 <= nc < kolom and grid[nr][nc] != 1
                    and (nr, nc) not in jarak):
                jarak[(nr, nc)] = jarak[(r, c)] + 1
                induk[(nr, nc)] = (r, c)
                antrean.append((nr, nc))
    return jarak, induk


def _derajat(grid, r, c):
    """Jumlah tetangga walkable; >=3 menandakan titik keputusan/persimpangan."""
    return sum(1 for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
               if 0 <= r + dr < len(grid) and 0 <= c + dc < len(grid[0])
               and grid[r + dr][c + dc] != 1)


def _persimpangan(grid, induk, target):
    """Hitung titik keputusan pada shortest-path dari start ke target."""
    jalur = []
    titik = target
    while titik is not None:
        jalur.append(titik)
        titik = induk.get(titik)
    jalur.reverse()
    return sum(1 for r, c in jalur[1:-1] if _derajat(grid, r, c) >= 3)


def _terdekat_manhattan(target, tersedia):
    """Sel walkable terdekat ke sudut; tie-break deterministik berdasarkan koordinat."""
    return min(tersedia, key=lambda t: (abs(t[0] - target[0]) + abs(t[1] - target[1]), t))


def _pilih_spawn(grid, jumlah_hantu=1):
    """Pilih Player, daftar Ghost, dan Exit secara deterministik memakai BFS.

    Player dan Exit memakai pasangan sudut dengan jarak jalur terjauh. Ghost
    pertama dipilih dari sel walkable yang memaksimalkan jarak shortest-path
    ke Player, lalu jumlah persimpangan pada rute, lalu jarak ke Exit. Ghost
    berikutnya dijauhkan secara BFS dari Player maupun ghost lainnya.
    Tie-break selalu berdasarkan koordinat agar reproducible.
    """
    jumlah_hantu = max(1, int(jumlah_hantu))
    baris, kolom = len(grid), len(grid[0])
    valid = [(r, c) for r in range(baris) for c in range(kolom)
             if grid[r][c] != 1]
    if not valid:
        return [0, 0], [[0, 0] for _ in range(jumlah_hantu)], [0, 0]

    sudut = [(0, 0), (0, kolom - 1), (baris - 1, 0), (baris - 1, kolom - 1)]
    jangkar = []
    for titik in sudut:
        calon = _terdekat_manhattan(titik, valid)
        if calon not in jangkar:
            jangkar.append(calon)
    for titik in valid:
        if len(jangkar) >= 4:
            break
        if titik not in jangkar:
            jangkar.append(titik)

    peta = [_peta_spawn(grid, a) for a in jangkar]
    jarak_jangkar = [item[0] for item in peta]
    pasangan = []
    for i in range(len(jangkar)):
        for j in range(i + 1, len(jangkar)):
            jarak = jarak_jangkar[i].get(jangkar[j])
            if jarak is not None:
                pasangan.append((jarak, i, j))

    if pasangan:
        pasangan.sort(key=lambda item: (-item[0], item[1], item[2]))
        _, i_p, i_e = pasangan[0]
    else:
        i_p, i_e = 0, min(1, len(jangkar) - 1)

    p, e = jangkar[i_p], jangkar[i_e]
    dp, induk_p = peta[i_p]
    de = peta[i_e][0]

    kumpulan = [t for t in valid if t != p and t != e and t in dp and t in de]
    if not kumpulan:
        kumpulan = [t for t in valid if t != p and t != e]
    if not kumpulan:
        cadangan = valid[0] if valid[0] != p else (valid[1] if len(valid) > 1 else p)
        return list(p), [list(cadangan) for _ in range(jumlah_hantu)], list(e)

    jauh = [t for t in kumpulan if dp[t] >= SPAWN_MIN_TARGET]
    if jauh:
        kumpulan = jauh
    maks = max(dp[t] for t in kumpulan)
    terbaik = [t for t in kumpulan if dp[t] == maks]
    penuh = [t for t in terbaik
             if _persimpangan(grid, induk_p, t) >= SPAWN_MIN_INTERSECTIONS]
    if penuh:
        terbaik = penuh

    def skor(t):
        return (-_persimpangan(grid, induk_p, t), -de.get(t, 0), t[0], t[1])

    h = min(terbaik, key=skor)
    daftar_hantu = [list(h)]

    for _ in range(jumlah_hantu - 1):
        peta_hantu = [_peta_spawn(grid, tuple(g))[0] for g in daftar_hantu]
        calon = [t for t in kumpulan
                 if t not in (p, e) and t not in daftar_hantu
                 and t in dp and all(t in ph for ph in peta_hantu)]
        if not calon:
            calon = [t for t in valid
                     if t not in (p, e) and t not in daftar_hantu]
        if not calon:
            calon = [t for t in valid if t not in daftar_hantu]
        if not calon:
            calon = list(valid)

        def skor_berikutnya(t):
            jarak_min = min(ph.get(t, 0) for ph in peta_hantu)
            return (-jarak_min, -_derajat(grid, t[0], t[1]), t[0], t[1])

        daftar_hantu.append(list(min(calon, key=skor_berikutnya)))

    return list(p), daftar_hantu, list(e)


# ---------------------------------------------------------------------------
# Pengaturan spawn: mode "auto" (deterministik), "random", atau "manual".
# Dibaca dari settings.json blok "spawn" tanpa mengubah kunci "controls".
# ---------------------------------------------------------------------------
SETTINGS_PATH = os.path.join(config.BASE_DIR, "settings.json")


def _baca_pengaturan_spawn():
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            isi = json.load(f)
        val = isi.get("spawn", {})
        return val if isinstance(val, dict) else {}
    except (OSError, ValueError, AttributeError):
        return {}


def _koordinat_valid(grid, nilai):
    if not isinstance(nilai, (list, tuple)) or len(nilai) < 2:
        return None
    try:
        r, c = int(nilai[0]), int(nilai[1])
    except (TypeError, ValueError):
        return None
    if (0 <= r < len(grid) and 0 <= c < len(grid[0])
            and grid[r][c] != 1):
        return (r, c)
    return None


def _spawn_acak(grid, jumlah, rng=None):
    """Spawn acak yang tetap valid, saling terjangkau, dan tidak berdekatan."""
    rng = rng or random.Random()
    valid = [(r, c) for r in range(len(grid))
             for c in range(len(grid[0])) if grid[r][c] != 1]
    if len(valid) < jumlah + 2:
        return None

    for _ in range(200):
        pilihan = rng.sample(valid, jumlah + 2)
        p, e = pilihan[0], pilihan[-1]
        daftar = pilihan[1:-1]
        dp = _peta_spawn(grid, p)[0]
        if e not in dp or any(g not in dp for g in daftar):
            continue
        if dp[e] < 10 or min(dp[g] for g in daftar) < 8:
            continue
        if any(_peta_spawn(grid, g)[0].get(h, 0) < 4
               for g in daftar for h in daftar if g != h):
            continue
        return list(p), [list(g) for g in daftar], list(e)
    return None


def _spawn_manual(grid, jumlah, pengaturan):
    """Pakai koordinat settings.json; bagian invalid jatuh ke spawn otomatis."""
    p, hantu_otomatis, e = _pilih_spawn(grid, jumlah)
    p_manual = _koordinat_valid(grid, pengaturan.get("pacman"))
    e_manual = _koordinat_valid(grid, pengaturan.get("exit"))
    if p_manual is not None and p_manual == e_manual:
        print("[spawn] pacman dan exit sama; Pac-Man memakai posisi otomatis.")
        p_manual = None
    if p_manual is not None:
        p = list(p_manual)
    if e_manual is not None:
        e = list(e_manual)

    ghosts_manual = pengaturan.get("ghosts", [])
    if not isinstance(ghosts_manual, (list, tuple)):
        ghosts_manual = []
    terpakai = {tuple(p), tuple(e)}
    cadangan = [(r, c) for r in range(len(grid))
                for c in range(len(grid[0])) if grid[r][c] != 1]
    daftar = []
    for i in range(jumlah):
        calon = (_koordinat_valid(grid, ghosts_manual[i])
                 if i < len(ghosts_manual) else None)
        if calon is None or calon in terpakai:
            calon = (_koordinat_valid(grid, hantu_otomatis[i])
                     if i < len(hantu_otomatis) else None)
        if calon is None or calon in terpakai:
            calon = next((t for t in cadangan if t not in terpakai), None)
        if calon is None:
            calon = tuple(p)
        daftar.append(list(calon))
        terpakai.add(calon)
    return p, daftar, e


def tentukan_spawn(grid, jumlah_hantu=1, pengaturan=None):
    """Entrypoint spawn: auto / random / manual dari settings.json."""
    jumlah = max(1, int(jumlah_hantu))
    pengaturan = pengaturan if isinstance(pengaturan, dict) else _baca_pengaturan_spawn()
    mode = str(pengaturan.get("mode", "auto")).strip().lower()
    if mode == "manual":
        return _spawn_manual(grid, jumlah, pengaturan)
    if mode == "random":
        hasil = _spawn_acak(grid, jumlah)
        if hasil is not None:
            return hasil
        print("[spawn] Gagal membuat spawn acak; memakai spawn otomatis.")
    return _pilih_spawn(grid, jumlah)


def simpan_pengaturan_spawn(pengaturan):
    """Simpan blok spawn ke settings.json tanpa menghapus kunci lain."""
    if not isinstance(pengaturan, dict):
        return False
    isi = {}
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            isi = json.load(f)
        if not isinstance(isi, dict):
            isi = {}
    except (OSError, ValueError):
        isi = {}
    isi["spawn"] = pengaturan
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(isi, f)
        return True
    except OSError:
        return False


def muat_mode_ghost():
    """Mode spawn ghost duel: 'sama' (default) atau 'pisah'."""
    pengaturan = _baca_pengaturan_spawn()
    mode = str(pengaturan.get("ghost_mode", "sama")).strip().lower()
    return "pisah" if mode in ("pisah", "separate", "terpisah", "dua") else "sama"


def _normalisasi_biaya(nilai):
    """Terima dict {(r,c):v} atau list [[r,c,v], ...]; buang biaya <= 1."""
    hasil = {}
    if isinstance(nilai, dict):
        for kunci, v in nilai.items():
            try:
                if isinstance(kunci, (list, tuple)) and len(kunci) >= 2:
                    r, c = int(kunci[0]), int(kunci[1])
                else:
                    continue
                v = int(v)
            except (TypeError, ValueError):
                continue
            if v > 1:
                hasil[(r, c)] = v
    elif isinstance(nilai, (list, tuple)):
        for item in nilai:
            try:
                if not isinstance(item, (list, tuple)) or len(item) < 3:
                    continue
                r, c, v = int(item[0]), int(item[1]), int(item[2])
            except (TypeError, ValueError):
                continue
            if v > 1:
                hasil[(r, c)] = v
    return hasil


def muat_biaya():
    """Baca biaya petak dari settings.json (blok 'costs')."""
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            isi = json.load(f)
        if not isinstance(isi, dict):
            return {}
        return _normalisasi_biaya(isi.get("costs"))
    except (OSError, ValueError):
        return {}


def simpan_biaya(biaya):
    """Simpan biaya petak tanpa menghapus kunci settings lain."""
    isi = {}
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            isi = json.load(f)
        if not isinstance(isi, dict):
            isi = {}
    except (OSError, ValueError):
        isi = {}
    isi["costs"] = [[r, c, v] for (r, c), v in sorted(_normalisasi_biaya(biaya).items())]
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(isi, f)
        return True
    except OSError:
        return False


class GhostAgent:
    """Satu ghost dengan algoritma, posisi, jalur, dan metriknya sendiri."""

    def __init__(self, algorithm, pos, last_move_time=0.0):
        self.algorithm = algorithm
        self.pos = list(pos)
        self.search_func = SEARCH.get(algorithm, cari_jalur_astar)
        self.path = []
        self.visited = []
        self.total_nodes = 0
        self.total_time = 0.0
        self.search_count = 0
        self.last_path_length = 0
        self.last_move_time = float(last_move_time)
        # Untuk gambar hasil: jejak nyata + rencana/area pencarian pertama.
        self.jejak = [tuple(pos)]
        self.visited_awal = []
        self.path_awal = []

    @property
    def stats(self):
        n = max(self.search_count, 1)
        return {
            "search_time_ms": (self.total_time / n) * 1000,
            "nodes_explored": int(self.total_nodes / n),
            "path_length": self.last_path_length,
        }


class Game:
    def __init__(self, maze_path, algorithm="astar", condition="diam",
                 spawn_settings=None, start_delay=None, costs=None, maze_data=None):
        self.algorithm = str(algorithm).lower()
        self.maze_path = maze_path
        self.spawn_settings = copy.deepcopy(spawn_settings) if isinstance(spawn_settings, dict) else {}
        self.playback_mode = False  # true hanya saat input berasal dari rekaman
        self._held_override = None  # arah virtual untuk playback (KEYUP -> None)
        self.is_duel = self.algorithm in ("duel", "both", "keduanya", "bfs+astar", "bfs+astar+search")
        self.algorithms = ("bfs", "astar") if self.is_duel else (self.algorithm,)
        self.condition = condition
        self.search_func = SEARCH.get(self.algorithms[0], cari_jalur_astar)

        if maze_data is not None:
            self.maze_data = copy.deepcopy(maze_data)
        else:
            with open(maze_path, "r") as f:
                self.maze_data = json.load(f)

        self.grid = self.maze_data["grid"]
        if costs is None:
            if isinstance(spawn_settings, dict) and "costs" in spawn_settings:
                costs = spawn_settings.get("costs")
            else:
                costs = muat_biaya()
        self.costs = _normalisasi_biaya(costs)
        now = pygame.time.get_ticks()
        # Satu titik saat mode "sama", dua titik saat mode "pisah".
        mode_ghost = "sama"
        if isinstance(spawn_settings, dict):
            mode_ghost = str(spawn_settings.get("ghost_mode", "sama")).strip().lower()
        self.ghost_mode = ("pisah" if mode_ghost in ("pisah", "separate", "terpisah", "dua")
                           else "sama")
        jumlah_spawn = 2 if (self.is_duel and self.ghost_mode == "pisah") else 1
        (self.pacman_pos, posisi_hantu,
         self.exit_pos) = tentukan_spawn(self.grid, jumlah_spawn, spawn_settings)
        if jumlah_spawn == 1:
            posisi_hantu = [posisi_hantu[0]] * len(self.algorithms)
        self.ghosts = [GhostAgent(algo, pos, now)
                       for algo, pos in zip(self.algorithms, posisi_hantu)]

        self.state = config.STATE_PLAYING
        self.ghost_last_move_time = now
        self.pacman_last_move_time = now
        self.pacman_move_delay = config.PACMAN_MOVE_DELAY
        self.pacman_interval_aktif = self.pacman_move_delay * 1000

        self.start_delay = float(config.START_DELAY_SECONDS if start_delay is None
                                 else start_delay)
        self.started_at = now
        self.jeda_selesai = self.start_delay <= 0

        self.pacman_total_nodes = 0
        self.pacman_total_time = 0.0
        self.pacman_search_count = 0
        self.exit_path = []
        self.buffered_dir = None
        self.current_dir = None

        # Setup Kontrol (WASD & Panah)
        self.key_dir = {
            pygame.K_UP: (-1, 0), pygame.K_DOWN: (1, 0), pygame.K_LEFT: (0, -1), pygame.K_RIGHT: (0, 1),
            pygame.K_w: (-1, 0), pygame.K_s: (1, 0), pygame.K_a: (0, -1), pygame.K_d: (0, 1)
        }

        try:
            keys = get_movement_keys()
            if isinstance(keys, dict) and "up" in keys:
                self.key_dir = {}
                for k in keys["up"]: self.key_dir[k] = (-1, 0)
                for k in keys["down"]: self.key_dir[k] = (1, 0)
                for k in keys["left"]: self.key_dir[k] = (0, -1)
                for k in keys["right"]: self.key_dir[k] = (0, 1)
        except Exception:
            pass

        self.update_ghost_path()
        self._catat_awal()

    def _catat_awal(self):
        """Reset jejak untuk gambar hasil (dipanggil saat game/playback dimulai)."""
        self.jejak_pacman = [tuple(self.pacman_pos)]
        for ghost in self.ghosts:
            ghost.jejak = [tuple(ghost.pos)]
            ghost.visited_awal = [tuple(p) for p in ghost.visited]
            ghost.path_awal = [tuple(ghost.pos)] + [tuple(p) for p in ghost.path]

    def data_jejak(self, index=0):
        """Data untuk menggambar hasil (lihat tampilan/gambar_jejak.py)."""
        ghost = self.ghosts[index]
        if self.state == config.STATE_WIN:
            hasil = "menang"
        elif self.state == config.STATE_LOSE:
            hasil = "kalah"
        else:
            hasil = "berhenti"
        return {
            "grid": self.grid, "exit": tuple(self.exit_pos),
            "algoritma": ghost.algorithm, "kondisi": self.condition,
            "hasil": hasil, "jejak_pacman": list(self.jejak_pacman),
            "jejak_hantu": list(ghost.jejak),
            "visited_awal": list(ghost.visited_awal),
            "path_awal": list(ghost.path_awal),
        }

    # Kompatibilitas dengan pemanggil lama yang memakai ghost tunggal.
    @property
    def ghost_pos(self):
        return self.ghosts[0].pos

    @property
    def current_path(self):
        return self.ghosts[0].path

    @property
    def total_nodes(self):
        return sum(g.total_nodes for g in self.ghosts)

    @property
    def total_time(self):
        return sum(g.total_time for g in self.ghosts)

    @property
    def search_count(self):
        return sum(g.search_count for g in self.ghosts)

    @property
    def last_path_length(self):
        return self.ghosts[0].last_path_length

    def _hitung_path(self, ghost):
        start = tuple(ghost.pos)
        target = tuple(self.pacman_pos)
        hasil = ghost.search_func(self.grid, start, target, self.costs,
                                  with_visited=True)
        path, nodes, elapsed = hasil[0], hasil[1], hasil[2]
        if len(hasil) > 3:
            ghost.visited = list(hasil[3])

        ghost.total_nodes += nodes
        ghost.total_time += elapsed
        ghost.search_count += 1
        ghost.last_path_length = max(len(path) - 1, 0)
        ghost.path = list(path[1:]) if len(path) > 1 else []

    def update_ghost_path(self):
        """Hitung ulang rute semua ghost setelah Pac-Man bergerak."""
        for ghost in self.ghosts:
            self._hitung_path(ghost)

    def get_stats(self):
        """Statistik ghost utama (kompatibel dengan pemanggil lama)."""
        return dict(self.ghosts[0].stats)

    def get_stats_by_algo(self):
        """Statistik per algoritma; dipakai mode duel BFS vs A*."""
        return {g.algorithm: dict(g.stats) for g in self.ghosts}

    def get_all_stats(self):
        """Daftar statistik lengkap dengan identitas algoritma."""
        return [dict(g.stats, algorithm=g.algorithm) for g in self.ghosts]

    @property
    def winner(self):
        return "pacman" if self.state == config.STATE_WIN else "ghost"

    def handle_input(self, event, recorder=None, tick=0):
        """Keyboard -> command controller. Satu jalur dengan playback (submit_input)."""
        if self.state != config.STATE_PLAYING or self.condition != "bergerak":
            return
        if event.type == pygame.KEYDOWN and event.key in self.key_dir:
            arah = self.key_dir[event.key]
            self.submit_input("PRESS", arah, record=True, recorder=recorder,
                              tick=tick, key=event.key)
        elif event.type == pygame.KEYUP and event.key in self.key_dir:
            arah = self.key_dir[event.key]
            self.submit_input("RELEASE", arah, record=True, recorder=recorder,
                              tick=tick, key=event.key)

    def submit_input(self, event_type, direction, record=False,
                     recorder=None, tick=0, key=None):
        """Satu titik masuk perintah: dipakai keyboard manual DAN playback.

        Playback memanggil dengan record=False sehingga tidak pernah membuat
        rekaman baru. PRESS mengisi buffer sekaligus arah tahan virtual; RELEASE
        menghapus arah tahan virtual (manual tetap memakai pygame.key.get_pressed).
        """
        if self.state != config.STATE_PLAYING or self.condition != "bergerak":
            return
        if direction is None or direction not in config.DIRECTION_NAMES:
            return
        if record and recorder is not None:
            recorder.capture(tick, event_type,
                             config.DIRECTION_NAMES[direction], key=key)
        if str(event_type).upper() == "PRESS":
            self.buffered_dir = direction
            self._held_override = direction
        elif str(event_type).upper() == "RELEASE":
            if self._held_override == direction:
                self._held_override = None

    def held_direction(self):
        """Arah tahan: virtual saat playback, keyboard fisik saat manual."""
        if self.playback_mode:
            return self._held_override
        keys = pygame.key.get_pressed()
        for key, arah in self.key_dir.items():
            if keys[key]:
                return arah
        return None

    def key_bindings(self):
        """Pemetaan nama arah -> kunci, untuk disimpan dalam rekaman."""
        hasil = {nama: [] for nama in config.DIRECTION_BY_NAME}
        for key, arah in self.key_dir.items():
            hasil[config.DIRECTION_NAMES[arah]].append(int(key))
        for nama in hasil:
            hasil[nama].sort()
        return hasil

    def is_valid_move(self, r, c):
        return (0 <= r < len(self.grid) and 0 <= c < len(self.grid[0]) and self.grid[r][c] != 1)

    def _faktor_kecepatan(self, pos):
        """Cost petak tujuan = berapa kali jeda gerak dasar (minimal 1)."""
        try:
            return max(1, int(self.costs.get((int(pos[0]), int(pos[1])), 1)))
        except (TypeError, ValueError):
            return 1

    def update(self):
        if self.state != config.STATE_PLAYING:
            return
        now = pygame.time.get_ticks()

        # Jeda awal: karakter belum bergerak agar posisi awal bisa dilihat.
        if not self.jeda_selesai:
            if now - self.started_at < self.start_delay * 1000:
                return
            self.jeda_selesai = True
            self.pacman_last_move_time = now
            for ghost in self.ghosts:
                ghost.last_move_time = now
            return

        # 1. PERGERAKAN PAC-MAN: arah dipilih dulu supaya cost petak tujuan
        #    ikut menentukan jeda sebelum langkah pertama dieksekusi.
        if self.condition == "bergerak":
            def bisa(arah):
                return (arah is not None
                        and self.is_valid_move(self.pacman_pos[0] + arah[0],
                                               self.pacman_pos[1] + arah[1]))

            held_dir = self.held_direction()
            if held_dir is not None and not bisa(held_dir):
                held_dir = None

            arah = None
            pakai_buffer = False
            if self.buffered_dir is not None:
                if bisa(self.buffered_dir):
                    arah = self.buffered_dir
                    pakai_buffer = True
                elif bisa(held_dir):
                    arah = held_dir
                elif bisa(self.current_dir):
                    arah = self.current_dir
            elif bisa(held_dir):
                arah = held_dir

            if arah is not None:
                tujuan = (self.pacman_pos[0] + arah[0],
                          self.pacman_pos[1] + arah[1])
                faktor = self._faktor_kecepatan(tujuan)
                interval_ms = self.pacman_move_delay * faktor * 1000
                self.pacman_interval_aktif = interval_ms
                if now - self.pacman_last_move_time >= interval_ms:
                    if pakai_buffer:
                        self.buffered_dir = None
                    self.pacman_pos = [tujuan[0], tujuan[1]]
                    self.current_dir = arah
                    if now - self.pacman_last_move_time >= 2 * interval_ms:
                        self.pacman_last_move_time = now
                    else:
                        self.pacman_last_move_time += interval_ms
                    self.jejak_pacman.append(tuple(self.pacman_pos))
                    self.update_ghost_path()
                    self.check_game_conditions()

        # 2. PERGERAKAN SETIAP GHOST (BFS dan/atau A* memakai timer sendiri)
        for ghost in self.ghosts:
            # Jeda mengikuti cost petak yang akan dimasuki ghost ini.
            langkah = ghost.path[0] if ghost.path else None
            faktor = self._faktor_kecepatan(langkah) if langkah else 1
            interval_ms = config.GHOST_MOVE_DELAY * faktor * 1000
            if now - ghost.last_move_time < interval_ms:
                continue
            if now - ghost.last_move_time >= 2 * interval_ms:
                ghost.last_move_time = now
            else:
                ghost.last_move_time += interval_ms
            if ghost.path:
                ghost.pos = list(ghost.path.pop(0))
            else:
                self._hitung_path(ghost)  # target sudah tercapai: cari ulang
                if ghost.path:
                    ghost.pos = list(ghost.path.pop(0))
            if tuple(ghost.pos) != ghost.jejak[-1]:
                ghost.jejak.append(tuple(ghost.pos))
            self.check_game_conditions()
            if self.state != config.STATE_PLAYING:
                break

    def check_game_conditions(self):
        if self.pacman_pos == self.exit_pos:
            self.state = config.STATE_WIN
        elif any(list(g.pos) == self.pacman_pos for g in self.ghosts):
            self.state = config.STATE_LOSE

    def apply_initial_state(self, initial):
        """Pasang kondisi awal dari rekaman pada object Game yang sudah dibuat.

        Hanya dipakai SEBELUM playback dimulai; tidak pernah dipanggil selama
        game berjalan. Pergerakan tetap lewat update() dan collision asli.
        """
        cfg = initial.get("game_config", {})
        now = pygame.time.get_ticks()
        self.pacman_pos = list(initial["player"])
        self.exit_pos = list(initial["exit"])
        self.costs = _normalisasi_biaya(cfg.get("costs"))
        self.pacman_move_delay = float(cfg.get(
            "pacman_move_delay", config.PACMAN_MOVE_DELAY))
        self.pacman_interval_aktif = self.pacman_move_delay * 1000
        self.start_delay = float(cfg.get(
            "start_delay_seconds", config.START_DELAY_SECONDS))
        self.started_at = now
        self.jeda_selesai = self.start_delay <= 0
        self.pacman_last_move_time = now
        self.ghost_last_move_time = now
        self.buffered_dir = None
        self.current_dir = None
        self.state = config.STATE_PLAYING
        self.exit_path = []
        self.pacman_total_nodes = 0
        self.pacman_total_time = 0.0
        self.pacman_search_count = 0
        # Input replay mensyaratkan Pac-Man bisa dikendalikan.
        self.condition = "bergerak"
        for ghost, saved in zip(self.ghosts, initial["ghosts"]):
            ghost.pos = list(saved["pos"])
            ghost.path = []
            ghost.visited = []
            ghost.last_move_time = now
        self.update_ghost_path()  # rute awal dihitung dengan algoritma pilihan UI
        for ghost in self.ghosts:  # statistik mulai dari nol saat playback dimulai
            ghost.total_nodes = 0
            ghost.total_time = 0.0
            ghost.search_count = 0
            ghost.last_path_length = max(len(ghost.path), 0)
        self._catat_awal()



    def _gambar_jeda(self, screen, layout, sisa):
        """Penanda jeda di area HUD; maze tetap terlihat penuh."""
        rect = layout["hud_rect"]
        if rect.width <= 0 or rect.height <= 0:
            return
        lapis = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        lapis.fill((7, 10, 24, 220))
        screen.blit(lapis, rect.topleft)
        pygame.draw.rect(screen, theme.BORDER, rect, 2)
        theme.fit_text(screen, "MULAI DALAM {0:.1f} DETIK".format(sisa),
                       rect.center, rect.width - 12,
                       max(11, min(18, rect.height // 3)), theme.TEXT, bold=True)

    def render(self, screen):
        """Render murni visual. Tidak mengubah posisi, state, atau metrik."""
        layout = hitung_layout(screen.get_size())
        screen.fill(config.COLOR_BG)

        gambar_maze(screen, layout, self.grid)
        # Biru = semua sel yang dieksplorasi (termasuk cabang jalan buntu).
        # Kuning = jalur solusi akhir dari ghost ke Pac-Man.
        for ghost in self.ghosts:
            gambar_visited(screen, layout, ghost.visited, theme.BFS)
        for ghost in self.ghosts:
            path_tampil = ([list(ghost.pos)] + ghost.path) if ghost.path else []
            gambar_path_aktif(screen, layout, path_tampil, theme.PACMAN)
        gambar_biaya(screen, layout, self.costs)
        gambar_exit(screen, layout, self.exit_pos)

        now = pygame.time.get_ticks()
        bergerak = self.condition == "bergerak"

        # Pac-Man: mulut membuka-menututup saat bergerak, menghadap arah terakhir.
        arah_pacman = self.current_dir if (bergerak and self.current_dir) else (1, 0)
        if bergerak:
            mulut = 8 + 27 * (0.5 + 0.5 * math.sin(now / 90.0))
        else:
            mulut = 20
        px, py = pusat_tile(layout, self.pacman_pos[0], self.pacman_pos[1])
        radius = max(3, int(layout["tile"] * 0.40))
        gambar_pacman(screen, (px, py), radius, arah_pacman,
                      mouth_deg=int(mulut), color=theme.PACMAN,
                      bg=theme.PATH, eye=True)

        # Ghost: arah diambil dari langkah berikutnya pada path masing-masing.
        for ghost in self.ghosts:
            if ghost.path:
                nr, nc = ghost.path[0]
                arah_ghost = (nr - ghost.pos[0], nc - ghost.pos[1])
            else:
                arah_ghost = (self.pacman_pos[0] - ghost.pos[0],
                              self.pacman_pos[1] - ghost.pos[1])
            gx, gy = pusat_tile(layout, ghost.pos[0], ghost.pos[1])
            bob = math.sin(now / 130.0) * max(1, radius * 0.06)
            warna_ghost = (theme.warna_algoritma(ghost.algorithm) if self.is_duel
                           else theme.GHOST_RED)
            gambar_ghost(screen, (gx, gy), radius, arah_ghost,
                         color=warna_ghost, bob=bob)

        if self.is_duel:
            # Nama algoritma ditulis penuh. Jika ghost masih bertumpuk,
            # tampilkan satu label "BFS / A*"; setelah berpisah, masing-masing
            # ghost membawa labelnya sendiri.
            skala = max(0.8, min(1.4, layout["tile"] / 30.0))
            if list(self.ghosts[0].pos) == list(self.ghosts[1].pos):
                gx, gy = pusat_tile(layout, self.ghosts[0].pos[0],
                                    self.ghosts[0].pos[1])
                gambar_label_algoritma_gabungan(
                    screen, (gx, gy - radius - 12), skala)
            else:
                for ghost in self.ghosts:
                    gx, gy = pusat_tile(layout, ghost.pos[0], ghost.pos[1])
                    gambar_label_algoritma(
                        screen, (gx, gy - radius - 10),
                        theme.label_algoritma(ghost.algorithm),
                        theme.warna_algoritma(ghost.algorithm), skala)

        gambar_hud(screen, layout, self)
        if not self.jeda_selesai:
            sisa = max(0.0, self.start_delay - (now - self.started_at) / 1000.0)
            self._gambar_jeda(screen, layout, sisa)



def snapshot_initial_state(game, random_seed=None):
    """Ambil kondisi awal lengkap dari game yang sedang berjalan."""
    if random_seed is None:
        random_seed = int.from_bytes(os.urandom(4), "little")
    maze_file = str(game.maze_path or "")
    try:
        maze_file = os.path.relpath(maze_file, config.BASE_DIR)
    except (ValueError, OSError):
        pass
    return {
        "maze_file": maze_file,
        "maze": copy.deepcopy(game.maze_data),
        "player": list(game.pacman_pos),
        "ghosts": [{"algorithm": g.algorithm, "pos": list(g.pos)}
                   for g in game.ghosts],
        "exit": list(game.exit_pos),
        "game_config": {
            "condition": game.condition,
            "algorithm": game.algorithm,
            "tick_rate": int(config.FPS),
            "pacman_move_delay": float(game.pacman_move_delay),
            "ghost_move_delay": float(config.GHOST_MOVE_DELAY),
            "start_delay_seconds": float(game.start_delay),
            "ghost_mode": game.ghost_mode,
            "key_bindings": game.key_bindings(),
            "costs": [[r, c, v] for (r, c), v in sorted(game.costs.items())],
        },
        "spawn_settings": copy.deepcopy(game.spawn_settings),
        "random_seed": int(random_seed),
    }


def build_game_from_recording(recording, algorithm):
    """Bangun ulang Game dari rekaman; algoritma diambil dari pilihan UI, bukan metadata."""
    initial = recording["initial_state"]
    algo = str(algorithm).lower()
    if algo not in SEARCH:
        raise ValueError("Algoritma tidak dikenal: {0}".format(algorithm))
    cfg = initial.get("game_config", {})
    seed = initial.get("random_seed")
    if seed is not None:
        try:
            random.seed(int(seed))
        except (TypeError, ValueError):
            pass
    game = Game(initial.get("maze_file") or "rekaman",
                algo, "bergerak",
                spawn_settings=copy.deepcopy(initial.get("spawn_settings") or {}),
                start_delay=cfg.get("start_delay_seconds"),
                costs=cfg.get("costs"),
                maze_data=initial["maze"])
    saved = [dict(g) for g in initial["ghosts"]]
    cocok = [g for g in saved if str(g.get("algorithm", "")).lower() == algo]
    if cocok:
        saved = [cocok[0]]
    game.apply_initial_state(dict(initial, ghosts=saved[:1]))
    game.playback_mode = True
    return game


# FUNGSI YANG HILANG TADI, SEKARANG SUDAH DIKEMBALIKAN
def run_game(screen, game, session=None, mode="manual"):
    """Jalankan satu sesi gameplay.

    mode='manual'  : gameplay lama, tanpa recorder/playback.
    mode='record'  : recorder sudah aktif sebelum loop; STOP disimpan.
    mode='playback': runner sudah dibuat sebelum loop; input fisik diabaikan.
    """
    from core.recorder import ExperimentSession
    from tampilan.ui_record import RuntimeStatus

    if session is None:
        session = ExperimentSession()
    status = RuntimeStatus()
    clock = pygame.time.Clock()
    tick = 0  # simulation tick = jumlah update() sejak run_game dimulai
    rekam = mode == "record"
    playback = mode == "playback"

    while game.state == config.STATE_PLAYING:
        if playback and session.runner and session.runner.finished:
            break
        laju = (session.runner.recording["simulation_tick_rate"]
                if playback and session.runner else config.FPS)
        clock.tick(max(1, int(laju)))
        berhenti = False

        for event in pygame.event.get():
            audio.handle_event(event)
            if event.type == pygame.QUIT:
                if rekam and session.recorder.active:
                    session.stop_recording(game, tick)
                    return "quit"
                if playback and session.runner and not session.runner.finished:
                    session.runner.finish(game, "ended")
                    session.selesai_playback(game)
                return "quit"
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if playback or rekam:
                    berhenti = True  # STOP lewat keyboard juga didukung
                    continue
                return "menu"
            if playback or rekam:
                if status.handle(event, screen) == "stop":
                    berhenti = True
                if playback:
                    continue  # keyboard arah fisik tidak mencampuri playback
            if (event.type in (pygame.KEYDOWN, pygame.KEYUP)
                    and not getattr(event, "repeat", False)):
                game.handle_input(event,
                                  recorder=session.recorder if rekam else None,
                                  tick=tick)

        # Event tick berjalan diproses dulu sebelum STOP diberlakukan.
        if (playback and session.runner and not session.runner.finished
                and not berhenti):
            session.runner.inject(game, tick)

        game.update()
        tick += 1

        if playback and session.runner and not session.runner.finished:
            session.runner.advance(game)
        if playback and session.runner and session.runner.finished:
            session.selesai_playback(game)

        if berhenti:
            if rekam:
                session.stop_recording(game, tick)
                return "record_done"
            if playback and session.runner and not session.runner.finished:
                session.runner.stop(game)
                session.selesai_playback(game)
                return "finished"

        game.render(screen)
        if rekam or playback:
            status.draw(screen, session, mode, game, tick)
        pygame.display.flip()

    if rekam:
        if session.recorder.active:
            session.stop_recording(game, tick)
        return "record_done"
    if playback and session.runner and not session.runner.finished:
        session.runner.finish(game, "ended")
    if playback:
        session.selesai_playback(game)
    return "finished"
