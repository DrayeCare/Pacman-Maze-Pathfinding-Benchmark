import datetime
import os

import pygame
from core import audio
from core import config
from core.game import Game, run_game
from core.recorder import ExperimentSession
from tampilan.main_ui import show_main_menu
from tampilan.ui_mode import show_mode
from tampilan.ui_mulai import show_mulai
from tampilan.ui_spawn import pilih_spawn
from tampilan.ui_setting import show_setting
from tampilan.ui_info import show_hasil
from tampilan.ui_record import show_record_summary
from tampilan.ui_record_manager import show_record_manager
from tampilan.ui_playback import show_playback_config, show_playback_result

data_hasil_percobaan = []


def _label_algo(algo):
    return {"bfs": "BFS", "astar": "A*", "duel": "BFS + A*"}.get(algo, algo)


def _catat_hasil(stats, maze_id, nama_map, kondisi, algo, kemenangan):
    """Satu baris hasil untuk layar INFO (definisi metrik tidak diubah)."""
    data_hasil_percobaan.append({
        "maze_id": maze_id,
        "nama_map": nama_map,
        "kondisi": kondisi,
        "waktu": round(float(stats.get("search_time_ms", 0.0)), 3),
        "simpul": int(stats.get("nodes_explored", 0)),
        "panjang": int(stats.get("path_length", 0)),
        "algoritma": _label_algo(algo),
        "hasil": kemenangan,
    })


def _catat_hasil_playback(hasil):
    maze_file = (hasil.get("initial_state") or {}).get("maze_file") or ""
    maze_id = 1
    for key, path in config.MAZE_FILES.items():
        if os.path.basename(maze_file) == os.path.basename(path):
            maze_id = key
            break
    _catat_hasil(
        hasil["stats"], maze_id,
        "{0} | rekaman: {1}".format(config.MAZE_TITLES[maze_id],
                                    hasil["recording"]),
        "Pac-Man Bergerak", hasil["algorithm"],
        "MENANG" if hasil["winner"] == "pacman" else (
            "KALAH" if hasil["winner"] == "ghost" else "SELESAI"),
    )


def mainkan(screen, pilihan, session=None, mode="manual"):
    """MANUAL / RECORD: konfigurasi game dibuat dulu, lalu satu sesi gameplay."""
    if session is None:
        session = ExperimentSession()
    spawn_terpilih = None
    while True:
        maze_file = config.MAZE_FILES[pilihan["maze"]]

        # Editor spawn GUI dipakai sekali; konfigurasi rekaman memakai posisi sama.
        if spawn_terpilih is None:
            spawn_terpilih = pilih_spawn(
                screen, maze_file, str(pilihan["algorithm"]).lower() == "duel")
            if spawn_terpilih in ("back", "quit"):
                return spawn_terpilih

        game = Game(maze_file, pilihan["algorithm"], pilihan["condition"],
                    spawn_settings=spawn_terpilih)

        if mode == "record":
            # Mode RECORD mulai merekam otomatis pada tick pertama.
            session.recorder.name = "player_test_{0}".format(
                datetime.datetime.now().strftime("%H%M%S"))
            session.start_recording(game, 0)

        aksi = run_game(screen, game, session, mode)

        if mode == "record":
            if aksi == "quit":
                return "quit"
            # Ringkasan penyimpanan; tidak memaksa pindah ke playback.
            return show_record_summary(screen, session.last_record_info)

        if aksi != "finished":
            return aksi

        # Mode duel menyimpan satu baris per algoritma.
        daftar_stats = (game.get_all_stats() if game.is_duel
                        else [dict(game.get_stats(), algorithm=game.algorithm)])
        for stat in daftar_stats:
            algo = stat.get("algorithm", game.algorithm)
            kemenangan = "MENANG" if game.state == config.STATE_WIN else "KALAH"
            _catat_hasil(stat, pilihan["maze"],
                         config.MAZE_TITLES[pilihan["maze"]],
                         "Pac-Man Bergerak" if pilihan.get("condition") == "bergerak"
                         else "Pac-Man Diam", algo, kemenangan)

        aksi = show_hasil(screen, data_hasil_percobaan)
        if aksi == "back":
            return "back"
        if aksi == "quit":
            return "quit"
        if aksi == "replay":
            continue


def jalankan_playback(screen, session):
    """PLAYBACK: pilih rekaman + algoritma dulu, baru buat game."""
    while True:
        konfig = show_playback_config(screen, session)
        if konfig in ("back", "quit"):
            return konfig
        path = konfig["path"]
        algo = konfig["algorithm"]
        session.pilih_rekaman(path)

        while True:
            game, runner = session.build_playback_game(algo, path)
            if game is None:
                break  # rekaman rusak/kosong: kembali ke konfigurasi

            aksi = run_game(screen, game, session, mode="playback")
            if aksi == "quit":
                return "quit"

            hasil = session.last_result
            if hasil is None or hasil.get("_game") is not game:
                session.selesai_playback(game)
                hasil = session.last_result
            if hasil is None:
                break

            _catat_hasil_playback(hasil)
            aksi = show_playback_result(screen, hasil)
            if aksi == "play_again":
                continue
            if aksi == "change_algo":
                algo = "astar" if algo == "bfs" else "bfs"
                continue
            if aksi == "menu":
                return "menu"
            if aksi == "quit":
                return "quit"


def main():
    pygame.init()
    if not audio.init_music():
        print("[BGM] Tidak ada file musik; game tetap berjalan tanpa BGM.")
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    # Satu session dipakai lintas percobaan agar hasil BFS/A* bisa dibandingkan.
    session = ExperimentSession()

    while True:
        menu = show_main_menu(screen)

        if menu == "quit":
            break

        elif menu == "setting":
            if show_setting(screen) == "quit":
                break

        elif menu == "info":
            if show_hasil(screen, data_hasil_percobaan) == "quit":
                break

        elif menu == "recordings":
            if show_record_manager(screen, session) == "quit":
                break

        elif menu == "mulai":
            mode = show_mode(screen)
            if mode == "quit":
                break
            if mode == "back":
                continue
            if mode == "playback":
                if jalankan_playback(screen, session) == "quit":
                    break
                continue

            keluar = False
            while True:
                pilihan = show_mulai(screen)
                if pilihan == "quit":
                    keluar = True
                    break
                if pilihan == "back":
                    break
                if mode == "record":
                    # Tanpa ini input keyboard tidak diproses Game.handle_input.
                    pilihan["condition"] = "bergerak"
                hasil_akhir = mainkan(screen, pilihan, session, mode)
                if hasil_akhir == "quit":
                    keluar = True
                    break
                if hasil_akhir == "back":
                    continue
                break
            if keluar:
                break

    audio.shutdown()
    pygame.quit()


if __name__ == "__main__":
    main()
