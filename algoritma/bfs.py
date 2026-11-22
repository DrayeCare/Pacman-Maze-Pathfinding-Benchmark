import heapq
import time
from collections import deque

from algoritma.biaya import ada_biaya, biaya_sel
from algoritma.hasil import keluaran


def cari_jalur_bfs(grid, start, goal, biaya=None, with_visited=False):
    start_time = time.perf_counter()
    if start == goal:
        return keluaran([start], 1, time.perf_counter() - start_time,
                        {start}, with_visited)

    # BFS berbobot memakai priority queue (Dijkstra). Tanpa biaya, kode
    # BFS original di bawah tetap dipakai supaya eksperimen lama identik.
    if ada_biaya(biaya):
        jarak = {start: 0}
        induk = {start: None}
        antrean = [(0, 0, start)]
        urutan = 1
        selesai = set()
        nodes_explored = 0
        baris, kolom = len(grid), len(grid[0])
        while antrean:
            d, _, sekarang = heapq.heappop(antrean)
            if sekarang in selesai:
                continue
            selesai.add(sekarang)
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
                                selesai, with_visited)
            r, c = sekarang
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < baris and 0 <= nc < kolom and grid[nr][nc] != 1:
                    tetangga = (nr, nc)
                    baru = d + biaya_sel(biaya, nr, nc)
                    if baru < jarak.get(tetangga, float("inf")):
                        jarak[tetangga] = baru
                        induk[tetangga] = sekarang
                        heapq.heappush(antrean, (baru, urutan, tetangga))
                        urutan += 1
        return keluaran([], nodes_explored, time.perf_counter() - start_time,
                        selesai, with_visited)

    baris, kolom = len(grid), len(grid[0])
    antrean = deque([start])
    sudah_dikunjungi = {start}
    dieksplorasi = set()
    induk = {start: None}
    nodes_explored = 0

    while antrean:
        sekarang = antrean.popleft()
        dieksplorasi.add(sekarang)
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
                            dieksplorasi, with_visited)

        r, c = sekarang
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < baris and 0 <= nc < kolom and grid[nr][nc] != 1:
                tetangga = (nr, nc)
                if tetangga not in sudah_dikunjungi:
                    sudah_dikunjungi.add(tetangga)
                    induk[tetangga] = sekarang
                    antrean.append(tetangga)

    return keluaran([], nodes_explored, time.perf_counter() - start_time,
                    dieksplorasi, with_visited)