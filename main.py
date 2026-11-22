import pygame
from core import audio
from core import config
from core.game import Game, run_game
from tampilan.main_ui import show_main_menu
from tampilan.ui_mulai import show_mulai
from tampilan.ui_spawn import pilih_spawn
from tampilan.ui_setting import show_setting
from tampilan.ui_info import show_hasil

data_hasil_percobaan = []
def mainkan(screen, pilihan):
    spawn_terpilih = None
    while True:
        maze_file = config.MAZE_FILES[pilihan["maze"]]

        # Editor spawn GUI dipakai sekali; replay memakai posisi yang sama.
        if spawn_terpilih is None:
            spawn_terpilih = pilih_spawn(
                screen, maze_file, str(pilihan["algorithm"]).lower() == "duel")
            if spawn_terpilih in ("back", "quit"):
                return spawn_terpilih

        game = Game(maze_file, pilihan["algorithm"], pilihan["condition"],
                    spawn_settings=spawn_terpilih)

        aksi = run_game(screen, game)
        
        if aksi != "finished":
            return aksi
        
        # Ambil data dari game. Mode duel menyimpan satu baris per algoritma.
        daftar_stats = (game.get_all_stats() if game.is_duel
                        else [dict(game.get_stats(), algorithm=game.algorithm)])
        for stat in daftar_stats:
            algo = stat.get("algorithm", game.algorithm)
            nama_algo = {"bfs": "BFS", "astar": "A*", "duel": "BFS + A*"}.get(algo, algo)
            data_baru = {
                "maze_id": pilihan["maze"],
                "nama_map": config.MAZE_TITLES[pilihan["maze"]],
                "kondisi": "Pac-Man Bergerak" if pilihan.get("condition") == "bergerak" else "Pac-Man Diam",
                "waktu": round(float(stat.get("search_time_ms", 0.0)), 3),
                "simpul": int(stat.get("nodes_explored", 0)),
                "panjang": int(stat.get("path_length", 0)),
                # Field display-only: tidak masuk CSV (export_to_csv menulis field eksplisit).
                "algoritma": nama_algo,
                "hasil": "MENANG" if game.state == config.STATE_WIN else "KALAH",
            }
            data_hasil_percobaan.append(data_baru)
        
        # Tampilkan UI Hasil
        aksi = show_hasil(screen, data_hasil_percobaan)
        
        if aksi == "back":
            return "back" 
        if aksi == "quit":
            return "quit"
            
        if aksi == "replay":
            continue 

def main():
    pygame.init()
    if not audio.init_music():
        print("[BGM] Tidak ada file musik; game tetap berjalan tanpa BGM.")
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    
    while True:
        menu = show_main_menu(screen)
        
        if menu == "quit":
            break
            
        elif menu == "setting":
            if show_setting(screen) == "quit":
                break
            
        elif menu == "mulai":
            keluar_dari_mulai = False
            while True:
                pilihan = show_mulai(screen)
                if pilihan == "quit":
                    keluar_dari_mulai = True
                    break
                if pilihan == "back":
                    break

                hasil_akhir = mainkan(screen, pilihan)
                if hasil_akhir == "quit":
                    keluar_dari_mulai = True
                    break
                if hasil_akhir == "back":
                    continue
                break
            if keluar_dari_mulai:
                break
                    
        elif menu == "info":
            # Panggil UI Info
            aksi_info = show_hasil(screen, data_hasil_percobaan)
            if aksi_info == "quit":
                break
                
    audio.shutdown()
    pygame.quit()

if __name__ == "__main__":
    main()

# Huwaiza ahma