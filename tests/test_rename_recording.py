"""Tes ganti nama rekaman (tanpa pygame).

Jalankan: python -m unittest tests.test_rename_recording -v
"""

import json
import os
import tempfile
import unittest

from core import config
from core.recorder import (RecordingError, load_input_recording,
                           rename_input_recording, save_input_recording)


def _rekaman(nama="player_test_054200"):
    return {
        "schema_version": config.RECORDING_SCHEMA_VERSION,
        "recording_name": nama,
        "simulation_tick_rate": config.FPS,
        "initial_state": {
            "maze": {"grid": [[0, 0], [0, 0]]},
            "player": [0, 0],
            "ghosts": [{"pos": [1, 1]}],
            "exit": [1, 0],
            "game_config": {},
        },
        "input_events": [],
    }


class TestGantiNamaRekaman(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = self.tmp.name
        self.path = save_input_recording(_rekaman(), self.folder)

    def tearDown(self):
        self.tmp.cleanup()

    def test_nama_file_dan_isi_berubah_stempel_waktu_tetap(self):
        stempel = "_".join(os.path.splitext(os.path.basename(self.path))[0].split("_")[-2:])
        baru, nama = rename_input_recording(self.path, "maze 1 BFS", self.folder)
        self.assertEqual(nama, "maze_1_BFS")
        self.assertEqual(os.path.basename(baru), "maze_1_BFS_{0}.json".format(stempel))
        self.assertFalse(os.path.exists(self.path))
        self.assertEqual(load_input_recording(baru)["recording_name"], "maze_1_BFS")

    def test_nama_kosong_ditolak_dan_file_lama_aman(self):
        with self.assertRaises(RecordingError):
            rename_input_recording(self.path, "   ", self.folder)
        self.assertTrue(os.path.exists(self.path))

    def test_tidak_menimpa_file_lain(self):
        p1, _ = rename_input_recording(self.path, "uji", self.folder)
        p2 = save_input_recording(_rekaman("lain"), self.folder)
        # Samakan stempel waktu agar nama tujuan bentrok dengan p1.
        sama = os.path.join(self.folder, "lain_" + "_".join(
            os.path.splitext(os.path.basename(p1))[0].split("_")[-2:]) + ".json")
        os.replace(p2, sama)
        baru, _ = rename_input_recording(sama, "uji", self.folder)
        self.assertNotEqual(os.path.abspath(baru), os.path.abspath(p1))
        self.assertTrue(os.path.exists(p1))
        self.assertTrue(os.path.exists(baru))

    def test_karakter_berbahaya_dibersihkan(self):
        baru, nama = rename_input_recording(self.path, "../../evil/name", self.folder)
        self.assertEqual(os.path.dirname(os.path.abspath(baru)), os.path.abspath(self.folder))
        self.assertNotIn("/", nama)

    def test_path_di_luar_folder_ditolak(self):
        with tempfile.TemporaryDirectory() as lain:
            luar = os.path.join(lain, "x.json")
            with open(luar, "w", encoding="utf-8") as f:
                json.dump(_rekaman(), f)
            with self.assertRaises(RecordingError):
                rename_input_recording(luar, "baru", self.folder)


if __name__ == "__main__":
    unittest.main()
