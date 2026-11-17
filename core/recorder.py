"""
FILE PEREKAM GERAKAN & DATA
Fungsi: Mencatat langkah Pac-Man dan menyimpan statistik hasil pertandingan.
"""

class Recorder:
    def __init__(self):
        self.history_moves = []
        self.history_hasil = [] # List baru untuk menyimpan data statistik

    def rekam_langkah(self, posisi_pacman):
        # Menyimpan posisi (row, col) ke dalam list
        self.history_moves.append(posisi_pacman)

    def dapatkan_rekaman(self):
        return self.history_moves

    def reset(self):
        self.history_moves = []
        self.history_hasil = []

    # --- FUNGSI BARU UNTUK MENYIMPAN HASIL PERCOBAAN ---
    def rekam_hasil(self, maze_id, nama_map, kondisi, waktu, simpul, panjang):
        self.history_hasil.append({
            "maze_id": maze_id,
            "nama_map": nama_map,
            "kondisi": kondisi,
            "waktu": waktu,
            "simpul": simpul,
            "panjang": panjang
        })

    def dapatkan_semua_hasil(self):
        return self.history_hasil