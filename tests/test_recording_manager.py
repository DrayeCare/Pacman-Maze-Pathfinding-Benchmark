"""Test pengelolaan rekaman: validasi hapus, konfirmasi UI, dan regresi playback."""

import json
import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

from core import config
from core.game import Game, snapshot_initial_state
from core.recorder import (
    ExperimentSession, PlaybackRunner, RecordingError,
    delete_all_input_recordings, delete_input_recording,
    list_recording_infos, load_input_recording, save_input_recording,
)
from tampilan.ui_record_manager import _konfirmasi, show_record_manager


class Scripted:
    def __init__(self, frames):
        self.frames = list(frames)
        self.i = 0
        self.real = pygame.event.get

    def __enter__(self):
        pygame.event.get = self.get
        return self

    def __exit__(self, *_):
        pygame.event.get = self.real

    def get(self):
        frame = self.frames[self.i] if self.i < len(self.frames) else []
        self.i += 1
        return list(frame)


def ev(key, t=pygame.KEYDOWN):
    return pygame.event.Event(t, key=key, unicode="")


class TestRecordingManager(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.session = ExperimentSession(directory=self.dir)
        self.game = Game(config.MAZE_FILES[1], "bfs", "bergerak",
                         spawn_settings={"mode": "auto"}, start_delay=0.0)
        self.initial = snapshot_initial_state(self.game, random_seed=11)
        pygame.display.set_mode((1000, 800))

    def tearDown(self):
        pygame.display.quit()
        self.tmp.cleanup()

    def buat(self, nama, events=None):
        events = events if events is not None else [
            {"tick": 1, "sequence": 0, "event": "PRESS", "direction": "RIGHT"},
            {"tick": 5, "sequence": 1, "event": "RELEASE", "direction": "RIGHT"},
        ]
        data = {
            "schema_version": config.RECORDING_SCHEMA_VERSION,
            "recording_name": nama,
            "created_at": "2026-01-02T03:04:05",
            "simulation_tick_rate": 10,
            "duration_ticks": 4,
            "event_count": len(events),
            "recorded_algorithm": "bfs",
            "initial_state": self.initial,
            "input_events": events,
        }
        return save_input_recording(data, self.dir)

    # --- BACKEND ---

    def test_daftar_menampilkan_metadata(self):
        self.buat("satu")
        self.buat("dua")
        infos = list_recording_infos(self.dir)
        self.assertEqual(len(infos), 2)
        self.assertTrue(all(i["valid"] for i in infos))
        self.assertEqual(sorted(i["name"] for i in infos), ["dua", "satu"])
        self.assertEqual(infos[0]["count"], 2)
        self.assertEqual(infos[0]["duration"], 4)
        self.assertEqual(infos[0]["tick_rate"], 10)
        self.assertEqual(infos[0]["created_at"], "2026-01-02T03:04:05")

    def test_delete_individual_hanya_file_terpilih(self):
        p1, p2, p3 = self.buat("satu"), self.buat("dua"), self.buat("tiga")
        nama = delete_input_recording(p2, self.dir)
        self.assertEqual(nama, "dua")
        self.assertFalse(os.path.exists(p2))
        self.assertTrue(os.path.exists(p1) and os.path.exists(p3))
        self.assertEqual(len(list_recording_infos(self.dir)), 2)

    def test_delete_all_hanya_file_rekaman_valid(self):
        p1, p2 = self.buat("satu"), self.buat("dua")
        catatan = os.path.join(self.dir, "catatan.txt")
        with open(catatan, "w", encoding="utf-8") as f:
            f.write("bukan rekaman")
        hasil = delete_all_input_recordings(self.dir)
        self.assertEqual(len(hasil["deleted"]), 2)
        self.assertFalse(os.path.exists(p1) or os.path.exists(p2))
        self.assertTrue(os.path.exists(catatan))
        self.assertEqual(os.listdir(self.dir), ["catatan.txt"])

    def test_file_rusak_tidak_dihapus_dan_ditandai(self):
        self.buat("bagus")
        rusak = os.path.join(self.dir, "rusak.json")
        with open(rusak, "w", encoding="utf-8") as f:
            f.write("{bukan json")
        infos = {i["file"]: i for i in list_recording_infos(self.dir)}
        self.assertFalse(infos["rusak.json"]["valid"])
        with self.assertRaises(RecordingError):
            delete_input_recording(rusak, self.dir)
        hasil = delete_all_input_recordings(self.dir)
        self.assertEqual(len(hasil["deleted"]), 1)
        self.assertTrue(os.path.exists(rusak))

    def test_file_non_recording_json_tidak_diubah(self):
        asing = os.path.join(self.dir, "bukanrekaman.json")
        with open(asing, "w", encoding="utf-8") as f:
            json.dump({"hello": "world"}, f)
        hasil = delete_all_input_recordings(self.dir)
        self.assertEqual(hasil["deleted"], [])
        self.assertTrue(os.path.exists(asing))
        self.assertTrue(os.path.isfile(asing))

    def test_path_traversal_dan_symlink_ditolak(self):
        luar = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        luar.close()
        try:
            self.buat("di_dalam")
            data = load_input_recording(
                os.path.join(self.dir, sorted(os.listdir(self.dir))[0]))
            with open(luar.name, "w", encoding="utf-8") as f:
                json.dump(data, f)
            traversal = os.path.join(self.dir, "..",
                                     os.path.basename(luar.name))
            with self.assertRaises(RecordingError):
                delete_input_recording(traversal, self.dir)
            tautan = os.path.join(self.dir, "tautan.json")
            os.symlink(luar.name, tautan)
            with self.assertRaises(RecordingError):
                delete_input_recording(tautan, self.dir)
            hasil = delete_all_input_recordings(self.dir)
            self.assertTrue(os.path.exists(luar.name))
            self.assertTrue(os.path.islink(tautan))
            self.assertEqual(len(hasil["deleted"]), 1)
        finally:
            os.unlink(luar.name)

    def test_playback_aktif_mencegah_penghapusan(self):
        path = self.buat("diputar")
        game, runner = self.session.build_playback_game("astar", path)
        self.assertIsNotNone(game)
        self.assertEqual(self.session.active_recording_path, os.path.abspath(path))
        self.assertFalse(self.session.hapus_rekaman(path))
        self.assertTrue(os.path.exists(path))
        runner.finished = True
        self.assertIsNone(self.session.active_recording_path)
        self.assertTrue(self.session.hapus_rekaman(path))
        self.assertFalse(os.path.exists(path))

    def test_refresh_setelah_hapus_dan_rekaman_baru(self):
        path = self.buat("lama")
        self.session.refresh()
        self.assertEqual(len(self.session.paths), 1)
        self.assertTrue(self.session.hapus_rekaman(path))
        self.assertEqual(self.session.paths, [])
        baru = self.buat("baru")
        self.session.refresh()
        self.assertEqual(self.session.paths, [baru])

    def test_playback_regresi_setelah_hapus_rekaman_lain(self):
        dipakai = self.buat("dipakai")
        lain = self.buat("lain")
        self.session.hapus_rekaman(lain)
        game, runner = self.session.build_playback_game("bfs", dipakai)
        self.assertIsNotNone(game)
        for t in range(6):
            runner.inject(game, t)
        self.assertEqual(runner.applied, load_input_recording(dipakai)["input_events"])

    # --- UI ---

    def test_dialog_batal_tidak_menghapus(self):
        path = self.buat("aman")
        with Scripted([[ev(pygame.K_ESCAPE)]]):
            setuju = _konfirmasi(pygame.display.get_surface(), "HAPUS", "Hapus 'aman'?")
        self.assertFalse(setuju)
        self.assertTrue(os.path.exists(path))

    def test_ui_delete_individual_dengan_konfirmasi(self):
        path = self.buat("hapus_saya")
        frames = [[], [ev(pygame.K_d)], [], [ev(pygame.K_RETURN)],
                  [ev(pygame.K_ESCAPE)]]
        with Scripted(frames):
            aksi = show_record_manager(pygame.display.get_surface(), self.session)
        self.assertEqual(aksi, "back")
        self.assertFalse(os.path.exists(path))

    def test_ui_batal_menyisahkan_file(self):
        path = self.buat("jangan_hapus")
        frames = [[], [ev(pygame.K_d)], [], [ev(pygame.K_ESCAPE)],
                  [ev(pygame.K_ESCAPE)]]
        with Scripted(frames):
            show_record_manager(pygame.display.get_surface(), self.session)
        self.assertTrue(os.path.exists(path))

    def test_ui_delete_all_perlu_dua_konfirmasi(self):
        p1, p2 = self.buat("a"), self.buat("b")
        # Hanya satu konfirmasi -> batal di konfirmasi kedua.
        frames = [[], [ev(pygame.K_a)], [], [ev(pygame.K_RETURN)],
                  [], [ev(pygame.K_ESCAPE)], [ev(pygame.K_ESCAPE)]]
        with Scripted(frames):
            show_record_manager(pygame.display.get_surface(), self.session)
        self.assertTrue(os.path.exists(p1) and os.path.exists(p2))

        frames = [[], [ev(pygame.K_a)], [], [ev(pygame.K_RETURN)],
                  [], [ev(pygame.K_RETURN)], [ev(pygame.K_ESCAPE)]]
        with Scripted(frames):
            aksi = show_record_manager(pygame.display.get_surface(), self.session)
        self.assertEqual(aksi, "back")
        self.assertFalse(os.path.exists(p1) or os.path.exists(p2))


if __name__ == "__main__":
    unittest.main(verbosity=2)
