"""Bentuk keluaran bersama untuk algoritma pencarian.

Tanpa `with_visited`, fungsi mengembalikan 3-tuple yang sama seperti versi
awal, sehingga skrip benchmark lama tidak perlu diubah.
"""


def keluaran(jalur, simpul, waktu, dikunjungi, with_visited=False):
    if with_visited:
        return jalur, simpul, waktu, sorted(dikunjungi)
    return jalur, simpul, waktu
