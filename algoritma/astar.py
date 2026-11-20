import time
import heapq

from algoritma.biaya import biaya_sel
from algoritma.hasil import keluaran


def heuristik_manhattan(posisi_sekarang, target):
    return abs(posisi_sekarang[0] - target[0]) + abs(posisi_sekarang[1] - target[1])

def cari_jalur_astar(grid, start, goal, biaya=None, with_visited=False):
    start_time = time.perf_counter()
    if start == goal:
        return keluaran([start], 1, time.perf_counter() - start_time,
                        {start}, with_visited)

    baris, kolom = len(grid), len(grid[0])
    open_heap = [(heuristik_manhattan(start, goal), 0, start)]
    g_score = {start: 0}
    induk = {start: None}
    sudah_dikunjungi = set()
    nodes_explored = 0

    while open_heap:
        f, g, sekarang = heapq.heappop(open_heap)

        if sekarang in sudah_dikunjungi:
            continue
        sudah_dikunjungi.add(sekarang)
        nodes_explored += 1

        if sekarang == goal:
            jalur = []
            node = sekarang
            while node is not None:
                jalur.append(node)
                node = induk[node]
            jalur.reverse()
            return keluaran(jalur, nodes_explored,
                            time.perf_counter() - start_time,
                            sudah_dikunjungi, with_visited)

        r, c = sekarang
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < baris and 0 <= nc < kolom and grid[nr][nc] != 1:
                tetangga = (nr, nc)
                g_baru = g + biaya_sel(biaya, nr, nc)
                if tetangga not in g_score or g_baru < g_score[tetangga]:
                    g_score[tetangga] = g_baru
                    induk[tetangga] = sekarang
                    f_baru = g_baru + heuristik_manhattan(tetangga, goal)
                    heapq.heappush(open_heap, (f_baru, g_baru, tetangga))

    return keluaran([], nodes_explored, time.perf_counter() - start_time,
                    sudah_dikunjungi, with_visited)