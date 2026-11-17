import pygame
from core import config
from core.game import Game, run_game
from tampilan.main_ui import show_main_menu
from tampilan.ui_mulai import show_mulai
from tampilan.ui_setting import show_setting
from tampilan.ui_info import show_hasil

data_hasil_percobaan = []

def mainkan(screen, pilihan):
    while True:
        maze_file = config.MAZE_FILES[pilihan["maze"]]
        
        # PERBAIKAN 1: Masukkan pilihan["condition"] ke dalam Game
        game = Game(maze_file, pilihan["algorithm"], pilihan["condition"])

        aksi = run_game(screen, game)
        
        if aksi != "finished":
            return aksi
        
        # Ambil data dari game
        stats = game.get_stats()

        # PERBAIKAN 2: Sesuaikan key dictionary dengan yang ada di game.get_stats()
        data_baru = {
            "maze_id": pilihan["maze"],
            "nama_map": config.MAZE_TITLES[pilihan["maze"]],
            "kondisi": "Pac-Man Bergerak" if pilihan.get("condition") == "bergerak" else "Pac-Man Diam",
            "waktu": round(stats.get("search_time_ms", 0.0), 3), # Ambil dari search_time_ms
            "simpul": stats.get("nodes_explored", 0),            # Ambil dari nodes_explored
            "panjang": stats.get("path_length", 0)               # Ambil dari path_length
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
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    
    while True:
        menu = show_main_menu(screen)
        
        if menu == "quit":
            break
            
        elif menu == "setting":
            if show_setting(screen) == "quit":
                break
            
        elif menu == "mulai":
            pilihan = show_mulai(screen)
            if pilihan == "quit":
                break
            if pilihan != "back":
                hasil_akhir = mainkan(screen, pilihan)
                if hasil_akhir == "quit":
                    break
                    
        elif menu == "info":
            # Panggil UI Info
            aksi_info = show_hasil(screen, data_hasil_percobaan)
            if aksi_info == "quit":
                break
                
    pygame.quit()

if __name__ == "__main__":
    main()