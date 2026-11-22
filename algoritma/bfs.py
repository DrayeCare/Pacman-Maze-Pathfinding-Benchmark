import time
from collections import deque

from algoritma.biaya import biaya_sel
from algoritma.hasil import keluaran


def cari_jalur_bfs(
    grid, start, goal, biaya=None,
    with_visited=False, with_cost=False
):
    start_time = time.perf_counter()

    if start == goal:
        hasil = keluaran(
            [start], 1, time.perf_counter() - start_time,
            {start}, with_visited
        )
        return (*hasil, 0) if with_cost else hasil

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

        # Periksa apakah tujuan ditemukan
        if sekarang == goal:
            jalur = []
            node = sekarang

            # Rekonstruksi jalur
            while node is not None:
                jalur.append(node)
                node = induk[node]

            jalur.reverse()

            # Hitung total biaya tanpa memengaruhi pencarian BFS
            total_biaya = sum(
                biaya_sel(biaya, r, c)
                for r, c in jalur[1:]
            )

            hasil = keluaran(
                jalur,
                nodes_explored,
                time.perf_counter() - start_time,
                dieksplorasi,
                with_visited
            )

            if with_cost:
                return (*hasil, total_biaya)

            return hasil

        r, c = sekarang

        # Urutan gerakan: atas, bawah, kiri, kanan
        for dr, dc in (
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1)
        ):
            nr, nc = r + dr, c + dc

            if (
                0 <= nr < baris
                and 0 <= nc < kolom
                and grid[nr][nc] != 1
            ):
                tetangga = (nr, nc)

                if tetangga not in sudah_dikunjungi:
                    sudah_dikunjungi.add(tetangga)
                    induk[tetangga] = sekarang
                    antrean.append(tetangga)

    # Tidak ditemukan jalur
    hasil = keluaran(
        [],
        nodes_explored,
        time.perf_counter() - start_time,
        dieksplorasi,
        with_visited
    )

    if with_cost:
        return (*hasil, None)

    return hasil
