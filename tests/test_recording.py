"""Test otomatis untuk fitur Player Input Recording & Playback.

Jalankan: .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
Semua test memakai SDL dummy driver; tidak menulis ke input_recordings/ proyek.
"""

import copy
import json
import os
import tempfile
import unittest
import unittest.mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

from algoritma.astar import cari_jalur_astar
from algoritma.bfs import cari_jalur_bfs
from core import config
from core.game import (Game, build_game_from_recording, run_game,
                       snapshot_initial_state)
from core.recorder import (ExperimentSession, InputRecorder, PlaybackRunner,
                           Recorder, RecordingError, list_input_recordings,
                           load_input_recording, save_input_recording,
                           validate_recording)


class FakeTicks:
    """Jam virtual deterministik: naik step ms setiap kali dibaca."""

    def __init__(self, start=0, step=100):
        self.value = start
        self.step = step

    def __call__(self):
        self.value += self.step
        return self.value


class ScriptedEvents:
    """Satu frame pygame.event.get() per entri; sisanya kosong."""

    def __init__(self, frames):
        self.frames = list(frames)
        self.index = 0
        self.real_get = pygame.event.get

    def __enter__(self):
        pygame.event.get = self.get
        return self

    def __exit__(self, *_):
        pygame.event.get = self.real_get

    def get(self):
        frame = self.frames[self.index] if self.index < len(self.frames) else []
        self.index += 1
        return list(frame)


def key_event(key, event_type=pygame.KEYDOWN):
    return pygame.event.Event(event_type, key=key, unicode="")


def buat_game(algo="bfs"):
    return Game(config.MAZE_FILES[1], algo, "bergerak",
                spawn_settings={"mode": "auto"}, start_delay=0.0)


def buat_rekaman(events=None, algo="bfs"):
    game = buat_game(algo)
    initial = snapshot_initial_state(game, random_seed=12345)
    events = events if events is not None else [
        {"tick": 1, "sequence": 0, "event": "PRESS", "direction": "RIGHT"},
        {"tick": 6, "sequence": 1, "event": "RELEASE", "direction": "RIGHT"},
    ]
    return {
        "schema_version": config.RECORDING_SCHEMA_VERSION,
        "recording_name": "test_rekaman",
        "created_at": "2026-01-01T00:00:00",
        "simulation_tick_rate": 10,
        "duration_ticks": events[-1]["tick"] if events else 0,
        "event_count": len(events),
        "recorded_algorithm": algo,
        "initial_state": initial,
        "input_events": copy.deepcopy(events),
    }


def jalankan_playback(recording, algo, ticks=30, bekukan_ghost=True):
    game = build_game_from_recording(recording, algo)
    game.pacman_last_move_time = 0  # jam virtual test dimulai dari nol
    if bekukan_ghost:
        for ghost in game.ghosts:
            ghost.last_move_time = 10 ** 9
    runner = PlaybackRunner(recording, algo, game)
    fake = FakeTicks()
    with unittest.mock.patch("core.game.pygame.time.get_ticks", side_effect=fake):
        for t in range(ticks):
            runner.inject(game, t)
            game.update()
            runner.advance(game)
            if runner.finished:
                break
    return game, runner


class TestInputRecorder(unittest.TestCase):
    def test_capture_urutan_tick_sequence_dan_anti_repeat(self):
        rec = InputRecorder()
        rec.start(buat_rekaman()["initial_state"], name="contoh",
                  algorithm="bfs", tick=0)
        self.assertTrue(rec.capture(0, "PRESS", "RIGHT", key=pygame.K_RIGHT))
        self.assertFalse(rec.capture(0, "PRESS", "RIGHT", key=pygame.K_RIGHT),
                         "keyboard repeat tidak boleh tercatat dua kali")
        self.assertTrue(rec.capture(3, "RELEASE", "RIGHT", key=pygame.K_RIGHT))
        self.assertFalse(rec.capture(5, "RELEASE", "RIGHT", key=pygame.K_RIGHT),
                         "KEYUP ganda tidak boleh tercatat")
        self.assertTrue(rec.capture(5, "PRESS", "UP", key=pygame.K_UP))
        self.assertEqual([e["sequence"] for e in rec.events], [0, 1, 2])
        self.assertEqual([e["tick"] for e in rec.events], [0, 3, 5])
        self.assertEqual([e["direction"] for e in rec.events],
                         ["RIGHT", "RIGHT", "UP"])
        snap = rec.snapshot()
        self.assertEqual(snap["event_count"], 3)
        self.assertEqual(snap["duration_ticks"], 5)
        self.assertEqual(snap["recording_name"], "contoh")

    def test_tidak_merekam_saat_tidak_aktif(self):
        rec = InputRecorder()
        self.assertFalse(rec.capture(1, "PRESS", "RIGHT", key=pygame.K_RIGHT))
        rec.start(buat_rekaman()["initial_state"])
        rec.stop()
        self.assertFalse(rec.capture(2, "PRESS", "UP", key=pygame.K_UP))

    def test_api_recorder_lama_tetap_kerja(self):
        lama = Recorder()
        lama.rekam_langkah((3, 4))
        lama.rekam_hasil(1, "Maze 1", "diam", 1.2, 30, 12)
        self.assertEqual(lama.dapatkan_rekaman(), [(3, 4)])
        self.assertEqual(lama.dapatkan_semua_hasil()[0]["simpul"], 30)
        lama.reset()
        self.assertEqual(lama.dapatkan_rekaman(), [])


class TestPenyimpanan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_simpan_nama_unik_dan_muat_ulang(self):
        rec = buat_rekaman()
        p1 = save_input_recording(rec, self.directory)
        p2 = save_input_recording(rec, self.directory)
        self.assertNotEqual(p1, p2)
        self.assertEqual(len(list_input_recordings(self.directory)), 2)
        dengan = load_input_recording(p1)
        self.assertEqual(dengan["input_events"], rec["input_events"])
        self.assertEqual(dengan["initial_state"]["player"],
                         rec["initial_state"]["player"])
        self.assertEqual(dengan["simulation_tick_rate"], 10)

    def test_file_rusak_dan_schema_tidak_dikenal_ditolak(self):
        rusak = os.path.join(self.directory, "rusak.json")
        with open(rusak, "w", encoding="utf-8") as f:
            f.write("{bukan json")
        with self.assertRaises(RecordingError):
            load_input_recording(rusak)

        rec = buat_rekaman()
        rec["schema_version"] = 999
        with self.assertRaises(RecordingError):
            validate_recording(rec)
        rec["schema_version"] = config.RECORDING_SCHEMA_VERSION
        rec["input_events"][1]["sequence"] = 7
        with self.assertRaises(RecordingError):
            validate_recording(rec)

    def test_validasi_menolak_urutan_tick_mundur(self):
        rec = buat_rekaman([
            {"tick": 5, "sequence": 0, "event": "PRESS", "direction": "UP"},
            {"tick": 2, "sequence": 1, "event": "RELEASE", "direction": "UP"},
        ])
        with self.assertRaises(RecordingError):
            validate_recording(rec)


class TestPlaybackInput(unittest.TestCase):
    def test_input_diterapkan_lewat_update_dan_pacman_bergeser(self):
        rec = buat_rekaman()
        game, runner = jalankan_playback(rec, "bfs")
        self.assertEqual(runner.applied, rec["input_events"])
        self.assertEqual(runner.desync, [])
        self.assertNotEqual(game.pacman_pos,
                            rec["initial_state"]["player"],
                            "Pac-Man harus bergerak lewat movement system asli")
        self.assertEqual(game.current_dir, config.DIRECTION_BY_NAME["RIGHT"])

    def test_posisi_rekaman_tidak_disalin_ke_game(self):
        rec = buat_rekaman()
        game, _ = jalankan_playback(rec, "bfs", ticks=1)
        self.assertEqual(game.pacman_pos, rec["initial_state"]["player"])

    def test_algoritma_bfs_dan_astar_mendapat_input_identik(self):
        rec = buat_rekaman()
        hasil = {}
        for algo in ("bfs", "astar"):
            game, runner = jalankan_playback(rec, algo)
            self.assertEqual(game.ghosts[0].algorithm, algo)
            self.assertEqual(game.ghosts[0].pos,
                             rec["initial_state"]["ghosts"][0]["pos"])
            self.assertEqual(runner.applied, rec["input_events"])
            hasil[algo] = runner.applied
        self.assertEqual(hasil["bfs"], hasil["astar"])
        self.assertEqual(rec["initial_state"]["random_seed"], 12345)

    def test_metadata_algoritma_rekaman_tidak_memaksa_playback(self):
        rec = buat_rekaman(algo="bfs")
        game, runner = jalankan_playback(rec, "astar")
        self.assertEqual(game.algorithm, "astar")
        self.assertEqual(runner.algorithm, "astar")

    def test_stop_di_tengah_menyimpan_hasil_status_stopped(self):
        rec = buat_rekaman()
        game = build_game_from_recording(rec, "bfs")
        runner = PlaybackRunner(rec, "bfs", game)
        runner.inject(game, 1)
        runner.advance(game)
        runner.stop(game)
        sesi = ExperimentSession(directory=tempfile.gettempdir())
        sesi.runner = runner
        sesi.selesai_playback(game)
        self.assertEqual(sesi.last_result["status"], "stopped")
        self.assertEqual(sesi.last_result["input_count"], 1)


class TestAlurMode(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.session = ExperimentSession(directory=self.tmp.name)
        pygame.display.set_mode((1000, 800))

    def tearDown(self):
        pygame.display.quit()
        self.tmp.cleanup()

    def stop_event(self):
        from tampilan.ui_record import RuntimeStatus
        _, stop = RuntimeStatus()._rects(pygame.display.get_surface())
        return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                  pos=stop.center)

    def test_pilih_mode_sebelum_game(self):
        from tampilan.ui_mode import show_mode
        with ScriptedEvents([[key_event(pygame.K_2)]]):
            mode = show_mode(pygame.display.get_surface())
        self.assertEqual(mode, "record")

    def test_record_mode_mulai_otomatis_dan_stop_menyimpan(self):
        game = buat_game()
        self.session.start_recording(game, tick=0)
        self.assertTrue(self.session.recorder.active)
        self.assertEqual(game.condition, "bergerak")
        frames = [
            [key_event(pygame.K_RIGHT)],
            [key_event(pygame.K_RIGHT, pygame.KEYUP)],
            [key_event(pygame.K_UP)],
            [key_event(pygame.K_UP, pygame.KEYUP)],
            [self.stop_event()],
            [],
        ]
        with ScriptedEvents(frames):
            aksi = run_game(pygame.display.get_surface(), game,
                            self.session, mode="record")
        self.assertEqual(aksi, "record_done")
        self.assertFalse(self.session.recorder.active)
        self.assertIsNotNone(self.session.last_record_info["file"])
        data = load_input_recording(self.session.last_record_info["file"])
        self.assertEqual([e["direction"] for e in data["input_events"]],
                         ["RIGHT", "RIGHT", "UP", "UP"])
        self.assertEqual(self.session.last_record_info["count"], 4)

    def test_stop_recording_melepaskan_arah_yang_ditahan(self):
        game = buat_game()
        self.session.start_recording(game, tick=0)
        game.handle_input(key_event(pygame.K_RIGHT),
                          recorder=self.session.recorder, tick=1)
        self.session.stop_recording(game, tick=3)
        data = load_input_recording(self.session.last_record_info["file"])
        self.assertEqual(data["input_events"][-1],
                         {"tick": 3, "sequence": 1, "event": "RELEASE",
                          "direction": "RIGHT"})

    def test_manual_mode_tidak_merekam(self):
        game = buat_game()
        pos_awal = list(game.pacman_pos)
        frames = [[key_event(pygame.K_RIGHT)], [],
                  [key_event(pygame.K_RIGHT, pygame.KEYUP)], [],
                  [pygame.event.Event(pygame.QUIT)]]
        with ScriptedEvents(frames):
            aksi = run_game(pygame.display.get_surface(), game,
                            self.session, mode="manual")
        self.assertEqual(aksi, "quit")
        self.assertEqual(self.session.recorder.events, [])
        self.assertNotEqual(game.pacman_pos, pos_awal,
                            "gameplay manual tetap menggerakkan Pac-Man")

    def test_playback_mode_memilih_algoritma_sebelum_game(self):
        rec = buat_rekaman()
        path = save_input_recording(rec, self.tmp.name)
        game_bfs, run_bfs = self.session.build_playback_game("bfs", path)
        game_astar, run_astar = self.session.build_playback_game("astar", path)
        self.assertEqual(game_bfs.ghosts[0].algorithm, "bfs")
        self.assertEqual(game_astar.ghosts[0].algorithm, "astar")
        self.assertEqual(game_bfs.pacman_pos, game_astar.pacman_pos)
        self.assertEqual(game_bfs.ghosts[0].pos, game_astar.ghosts[0].pos)
        self.assertEqual(run_bfs.events, run_astar.events)

    def test_playback_keyboard_fisik_diabaikan(self):
        rec = buat_rekaman()
        path = save_input_recording(rec, self.tmp.name)
        game, _ = self.session.build_playback_game("astar", path)
        frames = [[key_event(pygame.K_LEFT)],
                  [key_event(pygame.K_LEFT, pygame.KEYUP)]] + [[]] * 8
        frames.append([pygame.event.Event(pygame.QUIT)])
        with ScriptedEvents(frames):
            aksi = run_game(pygame.display.get_surface(), game,
                            self.session, mode="playback")
        self.assertEqual(aksi, "quit")
        runner = self.session.runner
        self.assertEqual(runner.applied, rec["input_events"])
        self.assertNotIn("LEFT", [e["direction"] for e in runner.applied])
        self.assertEqual(self.session.recorder.events, [])

    def test_stop_playback_lewat_tombol_status(self):
        rec = buat_rekaman()
        path = save_input_recording(rec, self.tmp.name)
        game, _ = self.session.build_playback_game("bfs", path)
        frames = [[key_event(pygame.K_RIGHT)], [self.stop_event()], []]
        with ScriptedEvents(frames):
            aksi = run_game(pygame.display.get_surface(), game,
                            self.session, mode="playback")
        self.assertEqual(aksi, "finished")
        self.assertEqual(self.session.last_result["status"], "stopped")

    def test_halaman_konfigurasi_dan_hasil_playback(self):
        from tampilan.ui_playback import (show_playback_config,
                                          show_playback_result)
        rec = buat_rekaman()
        path = save_input_recording(rec, self.tmp.name)
        self.session.refresh()
        self.session.pilih_rekaman(path)
        frames = [[], [key_event(pygame.K_RIGHT)], [],
                  [key_event(pygame.K_RETURN)]]
        with ScriptedEvents(frames):
            konfig = show_playback_config(pygame.display.get_surface(),
                                          self.session)
        self.assertIsInstance(konfig, dict)
        self.assertEqual(konfig["path"], path)
        self.assertEqual(konfig["algorithm"], "astar")

        hasil = {"recording": "test_rekaman", "algorithm": "astar",
                 "status": "completed", "winner": "pacman", "ticks": 16,
                 "input_count": 2,
                 "stats": {"search_time_ms": 0.3, "nodes_explored": 9,
                           "path_length": 4}}
        with ScriptedEvents([[key_event(pygame.K_c)]]):
            aksi = show_playback_result(pygame.display.get_surface(), hasil)
        self.assertEqual(aksi, "change_algo")

    def test_rekaman_kosong_ditolak_sebelum_game_dibuat(self):
        rec = buat_rekaman(events=[])
        save_input_recording(rec, self.tmp.name)
        game, runner = self.session.build_playback_game("bfs")
        self.assertIsNone(game)
        self.assertIsNone(runner)
        self.assertIn("kosong", self.session.message)


class TestRegresi(unittest.TestCase):
    def test_algoritma_lama_masih_mencari_jalur(self):
        with open(config.MAZE_FILES[1], "r", encoding="utf-8") as f:
            grid = json.load(f)["grid"]
        for algo, fn in (("bfs", cari_jalur_bfs), ("astar", cari_jalur_astar)):
            path, nodes, elapsed = fn(grid, (1, 1), (19, 19))
            self.assertGreater(len(path), 0, algo)
            self.assertGreater(nodes, 0, algo)
            self.assertGreaterEqual(elapsed, 0.0)

    def test_manual_input_collision_dan_render_tetap_kerja(self):
        game = buat_game()
        game.handle_input(key_event(pygame.K_RIGHT))
        self.assertEqual(game.buffered_dir, config.RIGHT)
        game.pacman_pos = list(game.exit_pos)
        game.check_game_conditions()
        self.assertEqual(game.state, config.STATE_WIN)
        pygame.display.set_mode((1000, 800))
        game.render(pygame.display.get_surface())
        pygame.display.quit()


if __name__ == "__main__":
    unittest.main(verbosity=2)
