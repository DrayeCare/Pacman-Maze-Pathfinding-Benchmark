import json
import math
from collections import deque

import pygame

from algoritma.astar import cari_jalur_astar
from algoritma.bfs import cari_jalur_bfs
from core import config
from core import audio
from tampilan import theme
from tampilan.ui_setting import get_movement_keys
from tampilan.visual import (gambar_exit, gambar_ghost, gambar_hud,
                             gambar_maze, gambar_pacman, gambar_path_aktif,
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


def _pilih_spawn(grid):
    """Pilih Player, Ghost, dan Exit secara deterministik memakai BFS.

    Player dan Exit memakai pasangan sudut dengan jarak jalur terjauh. Ghost
    dipilih dari sel walkable yang memaksimalkan jarak shortest-path ke Player,
    lalu jumlah persimpangan pada rute, lalu jarak ke Exit. Tie-break selalu
    berdasarkan koordinat agar reproducible.
    """
    baris, kolom = len(grid), len(grid[0])
    valid = [(r, c) for r in range(baris) for c in range(kolom)
             if grid[r][c] != 1]
    if not valid:
        return [0, 0], [0, 0], [0, 0]

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
        return list(p), list(cadangan), list(e)

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
    return list(p), list(h), list(e)


class Game:
    def __init__(self, maze_path, algorithm="astar", condition="diam"):
        self.algorithm = algorithm.lower()
        self.condition = condition  
        self.search_func = SEARCH.get(self.algorithm, cari_jalur_astar)
        
        with open(maze_path, "r") as f:
            self.maze_data = json.load(f)

        self.grid = self.maze_data["grid"]
        self.pacman_pos, self.ghost_pos, self.exit_pos = _pilih_spawn(self.grid)

        self.state = config.STATE_PLAYING 
        self.ghost_last_move_time = pygame.time.get_ticks()
        self.pacman_last_move_time = pygame.time.get_ticks()
        self.pacman_move_delay = config.PACMAN_MOVE_DELAY

        self.total_nodes = 0
        self.total_time = 0.0
        self.search_count = 0
        self.pacman_total_nodes = 0
        self.pacman_total_time = 0.0
        self.pacman_search_count = 0
        self.last_path_length = 0
        self.current_path = []
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

    def update_ghost_path(self):
        start = tuple(self.ghost_pos)
        target = tuple(self.pacman_pos)
        path, nodes, elapsed = self.search_func(self.grid, start, target)
        
        self.total_nodes += nodes
        self.total_time += elapsed
        self.search_count += 1
        
        self.last_path_length = max(len(path) - 1, 0)
        self.current_path = path[1:] if len(path) > 1 else []

    def get_stats(self):
        n = max(self.search_count, 1)
        return {
            "search_time_ms": (self.total_time / n) * 1000,
            "nodes_explored": int(self.total_nodes / n),
            "path_length": self.last_path_length
        }

    @property
    def winner(self):
        return "pacman" if self.state == config.STATE_WIN else "ghost"

    def handle_input(self, event):
        if self.state != config.STATE_PLAYING or self.condition != "bergerak":
            return
        if event.type == pygame.KEYDOWN and event.key in self.key_dir:
            self.buffered_dir = self.key_dir[event.key]

    def is_valid_move(self, r, c):
        return (0 <= r < len(self.grid) and 0 <= c < len(self.grid[0]) and self.grid[r][c] != 1)

    def update(self):
        if self.state != config.STATE_PLAYING:
            return
        now = pygame.time.get_ticks()

        # 1. PERGERAKAN PAC-MAN: hanya saat "bergerak" dan hanya oleh input player
        if (self.condition == "bergerak"
                and now - self.pacman_last_move_time >= self.pacman_move_delay * 1000):
            def bisa(arah):
                return (arah is not None
                        and self.is_valid_move(self.pacman_pos[0] + arah[0],
                                               self.pacman_pos[1] + arah[1]))

            keys = pygame.key.get_pressed()
            held_dir = None
            for key, arah in self.key_dir.items():
                if keys[key] and bisa(arah):
                    held_dir = arah
                    break

            arah = None
            if self.buffered_dir is not None:
                if bisa(self.buffered_dir):
                    arah = self.buffered_dir
                    self.buffered_dir = None
                elif bisa(held_dir):
                    arah = held_dir
                elif bisa(self.current_dir):
                    arah = self.current_dir
            elif bisa(held_dir):
                arah = held_dir

            if arah is not None:
                self.pacman_pos = [self.pacman_pos[0] + arah[0], self.pacman_pos[1] + arah[1]]
                self.current_dir = arah
                interval_ms = self.pacman_move_delay * 1000
                if now - self.pacman_last_move_time >= 2 * interval_ms:
                    self.pacman_last_move_time = now
                else:
                    self.pacman_last_move_time += interval_ms
                self.update_ghost_path()
                self.check_game_conditions()

        # 2. PERGERAKAN GHOST
        if now - self.ghost_last_move_time >= config.GHOST_MOVE_DELAY * 1000:
            interval_ms = config.GHOST_MOVE_DELAY * 1000
            if now - self.ghost_last_move_time >= 2 * interval_ms:
                self.ghost_last_move_time = now
            else:
                self.ghost_last_move_time += interval_ms
            if self.current_path:
                self.ghost_pos = list(self.current_path.pop(0))
                self.check_game_conditions()

    def check_game_conditions(self):
        if self.pacman_pos == self.exit_pos:
            self.state = config.STATE_WIN
        elif self.pacman_pos == self.ghost_pos:
            self.state = config.STATE_LOSE

    def render(self, screen):
        """Render murni visual. Tidak mengubah posisi, state, atau metrik."""
        layout = hitung_layout(screen.get_size())
        screen.fill(config.COLOR_BG)

        gambar_maze(screen, layout, self.grid)
        # Path aktif adalah keluaran nyata algoritma (self.current_path).
        # Tidak menggambar visited/frontier karena tidak dikembalikan algoritma.
        # Sertakan posisi Ghost sekarang agar garis menyambung ke sprite.
        # Ini tetap data nyata: ghost_pos + sisa path dari algoritma.
        path_tampil = ([list(self.ghost_pos)] + self.current_path) if self.current_path else []
        gambar_path_aktif(screen, layout, path_tampil,
                          theme.warna_algoritma(self.algorithm))
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

        # Ghost: arah diambil dari langkah berikutnya pada path yang sudah ada.
        if self.current_path:
            nr, nc = self.current_path[0]
            arah_ghost = (nr - self.ghost_pos[0], nc - self.ghost_pos[1])
        else:
            arah_ghost = (self.pacman_pos[0] - self.ghost_pos[0],
                          self.pacman_pos[1] - self.ghost_pos[1])
        gx, gy = pusat_tile(layout, self.ghost_pos[0], self.ghost_pos[1])
        bob = math.sin(now / 130.0) * max(1, radius * 0.06)
        gambar_ghost(screen, (gx, gy), radius, arah_ghost,
                     color=theme.GHOST_RED, bob=bob)

        gambar_hud(screen, layout, self)


# FUNGSI YANG HILANG TADI, SEKARANG SUDAH DIKEMBALIKAN
def run_game(screen, game):
    clock = pygame.time.Clock()
    while game.state == config.STATE_PLAYING:
        clock.tick(config.FPS)
        for event in pygame.event.get():
            audio.handle_event(event)
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "menu"
            game.handle_input(event)
            
        game.update()
        game.render(screen)
        pygame.display.flip()
        
    return "finished"