"""
FILE PEREKAM GERAKAN & DATA
Fungsi lama : Mencatat langkah Pac-Man dan menyimpan statistik hasil pertandingan.
Fungsi baru : Merekam PERINTAH INPUT pemain (PRESS/RELEASE + tick) dan memutarnya
              kembali lewat jalur input yang sama dengan keyboard manual.

Rekaman berisi perintah pemain + kondisi awal eksperimen, BUKAN koordinat atau
hasil pergerakan. Lihat config.RECORDING_SCHEMA_VERSION untuk versi format.
"""

import copy
import datetime
import json
import os
import random
import re
from typing import TypeGuard

from core import config

# API lama (Recorder) sengaja dipertahankan tanpa perubahan.


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


# ---------------------------------------------------------------------------
# Rekaman input pemain
# ---------------------------------------------------------------------------
class RecordingError(Exception):
    """File rekaman tidak dapat dibaca/dipakai (rusak, versi salah, dll)."""


VALID_EVENTS = ("PRESS", "RELEASE")
VALID_DIRECTIONS = tuple(config.DIRECTION_BY_NAME)


def _slug(nama):
    teks = re.sub(r"[^A-Za-z0-9_-]+", "_", str(nama or "").strip())
    return teks.strip("_")[:60] or "player"


def _adalah_int(nilai) -> TypeGuard[int]:
    return isinstance(nilai, int) and not isinstance(nilai, bool)


class InputRecorder:
    """Menangkap perintah PRESS/RELEASE pada simulation tick saat rekaman aktif."""

    def __init__(self):
        self.events = []
        self.active = False
        self.name = "player_test_001"
        self.initial_state = None
        self.recorded_algorithm = None
        self.sequence = 0
        self.started_tick = 0
        self.last_tick = 0
        self._pressed = set()  # kunci fisik yang sedang ditekan (anti keyboard-repeat)

    def start(self, initial_state, name=None, algorithm=None, tick=0):
        if not isinstance(initial_state, dict):
            raise RecordingError("Kondisi awal rekaman tidak tersedia.")
        self.events = []
        self.sequence = 0
        self._pressed.clear()
        self.active = True
        self.initial_state = copy.deepcopy(initial_state)
        self.name = _slug(name) if name else self.name
        self.recorded_algorithm = str(algorithm or "")
        self.started_tick = int(tick)
        self.last_tick = int(tick)

    def stop(self, tick=None, release_keys=None):
        """Hentikan rekaman. Lepaskan arah yang masih ditahan agar replay tidak macet."""
        if release_keys and self.active:
            for key in sorted(set(self._pressed)):
                arah = release_keys.get(key)
                if arah is not None and arah in config.DIRECTION_NAMES:
                    self.capture(tick if tick is not None else self.last_tick,
                                 "RELEASE", config.DIRECTION_NAMES[arah], key=key)
        self.active = False
        if tick is not None:
            self.last_tick = max(self.last_tick, int(tick))
        self._pressed.clear()

    def capture(self, tick, event_type, direction, key=None):
        """Simpan satu perintah. kunci fisik dipakai untuk menolak repeat/KEYUP ganda."""
        if not self.active:
            return False
        event_type = str(event_type).upper()
        direction = str(direction).upper()
        if event_type not in VALID_EVENTS or direction not in VALID_DIRECTIONS:
            return False
        if key is not None:
            if event_type == "PRESS" and key in self._pressed:
                return False
            if event_type == "RELEASE" and key not in self._pressed:
                return False
            if event_type == "PRESS":
                self._pressed.add(key)
            else:
                self._pressed.discard(key)
        self.events.append({
            "tick": max(0, int(tick)),
            "sequence": self.sequence,
            "event": event_type,
            "direction": direction,
        })
        self.sequence += 1
        self.last_tick = max(self.last_tick, int(tick))
        return True

    def snapshot(self, tick_rate=None):
        if self.initial_state is None:
            raise RecordingError("Rekaman belum memiliki kondisi awal.")
        return {
            "schema_version": config.RECORDING_SCHEMA_VERSION,
            "recording_name": self.name,
            "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "simulation_tick_rate": int(tick_rate or config.FPS),
            "duration_ticks": max(0, self.last_tick - self.started_tick),
            "event_count": len(self.events),
            "recorded_algorithm": self.recorded_algorithm,
            "initial_state": copy.deepcopy(self.initial_state),
            "input_events": copy.deepcopy(self.events),
        }


def save_input_recording(recording, directory=None):
    """Tulis file unik dengan exclusive-create; tidak pernah menimpa rekaman lama."""
    validate_recording(recording)
    folder = directory or config.RECORDINGS_DIR
    os.makedirs(folder, exist_ok=True)
    dasar = _slug(recording["recording_name"])
    cap = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for i in range(100):
        suffix = "" if i == 0 else "_{0:02d}".format(i)
        path = os.path.join(folder, "{0}_{1}{2}.json".format(dasar, cap, suffix))
        try:
            with open(path, "x", encoding="utf-8") as f:
                json.dump(recording, f, indent=2, ensure_ascii=False)
            return path
        except FileExistsError:
            continue
    raise RecordingError("Gagal membuat nama file rekaman yang unik.")


def rename_input_recording(path, nama_baru, directory=None):
    """Ganti nama rekaman: nama file DAN recording_name di dalam JSON.

    Stempel waktu di akhir nama file (_YYYYMMDD_HHMMSS) dipertahankan, jadi
    hasilnya mis. 'maze1_bfs_20261127_054218.json'. Tidak pernah menimpa file
    lain. Mengembalikan (path_baru, nama_bersih).
    """
    folder = directory or config.RECORDINGS_DIR
    if not _dalam_direktori(path, folder):
        raise RecordingError("Lokasi file rekaman tidak valid.")
    if not str(nama_baru or "").strip():
        raise RecordingError("Nama tidak boleh kosong.")
    dasar = _slug(nama_baru)

    nama_lama = os.path.splitext(os.path.basename(path))[0]
    cocok = re.search(r"_(\d{8}_\d{6})(?:_\d{2})?$", nama_lama)
    cap = cocok.group(1) if cocok else datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    data = load_input_recording(path)
    data["recording_name"] = dasar

    for i in range(100):
        suffix = "" if i == 0 else "_{0:02d}".format(i)
        baru = os.path.join(folder, "{0}_{1}{2}.json".format(dasar, cap, suffix))
        if os.path.abspath(baru) == os.path.abspath(path):
            # Nama file sama: cukup perbarui isi file di tempat.
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return path, dasar
        try:
            with open(baru, "x", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except FileExistsError:
            continue
        os.remove(path)
        return baru, dasar
    raise RecordingError("Gagal membuat nama file rekaman yang unik.")


def list_input_recordings(directory=None):
    folder = directory or config.RECORDINGS_DIR
    if not os.path.isdir(folder):
        return []
    return [os.path.join(folder, n) for n in sorted(os.listdir(folder))
            if n.lower().endswith(".json")]


def _dalam_direktori(path, folder):
    """Path harus file .json langsung di folder, bukan symlink, bukan traversal."""
    if not isinstance(path, str):
        return False
    if not path.lower().endswith(".json"):
        return False
    folder_abs = os.path.abspath(folder)
    file_abs = os.path.abspath(path)
    if os.path.dirname(file_abs) != folder_abs:
        return False
    if os.path.islink(file_abs):
        return False
    folder_real = os.path.realpath(folder)
    file_real = os.path.realpath(file_abs)
    if os.path.dirname(file_real) != folder_real:
        return False
    try:
        return os.path.commonpath([folder_real, file_real]) == folder_real
    except ValueError:
        return False


def recording_info(path, directory=None):
    """Metadata satu rekaman untuk manager; file rusak ditandai, tidak dilempar."""
    folder = directory or config.RECORDINGS_DIR
    info = {
        "path": path, "file": os.path.basename(str(path)), "name": "-",
        "created_at": "-", "count": 0, "duration": 0, "tick_rate": 0,
        "version": None, "valid": False, "error": None,
    }
    if not _dalam_direktori(path, folder):
        info["error"] = "Path bukan file rekaman di direktori yang diizinkan."
        return info
    try:
        data = load_input_recording(path)
        info.update(
            name=str(data.get("recording_name", "?")),
            created_at=str(data.get("created_at", "-")),
            count=int(data.get("event_count", len(data.get("input_events", [])))),
            duration=int(data.get("duration_ticks", 0)),
            tick_rate=int(data.get("simulation_tick_rate", 0)),
            version=data.get("schema_version"),
            valid=True,
        )
    except (RecordingError, TypeError, ValueError) as exc:
        info["error"] = str(exc)
    return info


def list_recording_infos(directory=None):
    """Semua entri .json di direktori recording, valid maupun rusak."""
    folder = directory or config.RECORDINGS_DIR
    return [recording_info(p, folder) for p in list_input_recordings(folder)]


def delete_input_recording(path, directory=None, active_path=None):
    """Hapus SATU rekaman tervalidasi. Kembalikan nama rekaman yang dihapus."""
    folder = directory or config.RECORDINGS_DIR
    if active_path is not None and os.path.abspath(str(path)) == os.path.abspath(str(active_path)):
        raise RecordingError("Rekaman sedang diputar; hentikan playback sebelum menghapus.")
    info = recording_info(path, folder)
    if not info["valid"]:
        raise RecordingError("Bukan rekaman valid: {0}".format(info["error"]))
    if not _dalam_direktori(path, folder):
        raise RecordingError("Path penghapusan di luar direktori rekaman.")
    try:
        os.remove(path)
    except OSError as exc:
        raise RecordingError("Gagal menghapus {0}: {1}".format(
            info["file"], exc)) from exc
    return info["name"]


def delete_all_input_recordings(directory=None, active_path=None):
    """Hapus semua rekaman valid di folder. File rusak/asing sengaja dilewati."""
    folder = directory or config.RECORDINGS_DIR
    hasil = {"deleted": [], "skipped": [], "errors": []}
    for info in list_recording_infos(folder):
        if not info["valid"]:
            hasil["skipped"].append("{0} (tidak valid)".format(info["file"]))
            continue
        try:
            hasil["deleted"].append(delete_input_recording(
                info["path"], folder, active_path=active_path))
        except RecordingError as exc:
            if "sedang diputar" in str(exc):
                hasil["skipped"].append(info["file"])
            else:
                hasil["errors"].append(str(exc))
    return hasil


def validate_recording(data):
    """Validasi schema + konsistensi event. Lempar RecordingError bila tidak valid."""
    if not isinstance(data, dict):
        raise RecordingError("Isi file bukan objek JSON.")
    if data.get("schema_version") != config.RECORDING_SCHEMA_VERSION:
        raise RecordingError("Versi schema tidak dikenal: {0!r}".format(
            data.get("schema_version")))
    if not isinstance(data.get("recording_name"), str) or not data["recording_name"].strip():
        raise RecordingError("Nama rekaman kosong atau tidak valid.")
    rate = data.get("simulation_tick_rate")
    if not _adalah_int(rate) or rate <= 0:
        raise RecordingError(" simulation_tick_rate tidak valid.")
    initial = data.get("initial_state")
    if not isinstance(initial, dict):
        raise RecordingError("initial_state tidak ditemukan.")
    for k in ("maze", "player", "ghosts", "exit", "game_config"):
        if k not in initial:
            raise RecordingError("initial_state.{0} tidak ditemukan.".format(k))
    grid = initial["maze"].get("grid") if isinstance(initial["maze"], dict) else None
    if not isinstance(grid, list) or not grid:
        raise RecordingError("Grid maze pada rekaman kosong/rusak.")
    for k in ("player", "exit"):
        pos = initial[k]
        if (not isinstance(pos, (list, tuple)) or len(pos) < 2
                or not all(_adalah_int(v) for v in pos[:2])):
            raise RecordingError("Posisi {0} tidak valid.".format(k))
    ghosts = initial["ghosts"]
    if not isinstance(ghosts, list) or not ghosts:
        raise RecordingError("Daftar ghost pada rekaman kosong/rusak.")
    for g in ghosts:
        if (not isinstance(g, dict) or not isinstance(g.get("pos"), (list, tuple))
                or len(g["pos"]) < 2 or not all(_adalah_int(v) for v in g["pos"][:2])):
            raise RecordingError("Posisi ghost tidak valid.")
    if not isinstance(initial["game_config"], dict):
        raise RecordingError("game_config tidak valid.")
    events = data.get("input_events")
    if not isinstance(events, list):
        raise RecordingError("input_events bukan daftar.")
    tick_sebelum, urutan_sebelum = -1, -1
    for i, ev in enumerate(events):
        if not isinstance(ev, dict):
            raise RecordingError("Event #{0} bukan objek.".format(i))
        tick, seq = ev.get("tick"), ev.get("sequence")
        if not _adalah_int(tick) or tick < 0:
            raise RecordingError("Tick event #{0} tidak valid.".format(i))
        if not _adalah_int(seq) or seq != urutan_sebelum + 1:
            raise RecordingError("Nomor urut event #{0} tidak monotonic.".format(i))
        if tick < tick_sebelum:
            raise RecordingError("Tick event #{0} mundur dari sebelumnya.".format(i))
        if ev.get("event") not in VALID_EVENTS:
            raise RecordingError("Jenis event #{0} tidak dikenal: {1!r}.".format(
                i, ev.get("event")))
        if ev.get("direction") not in VALID_DIRECTIONS:
            raise RecordingError("Arah event #{0} tidak dikenal: {1!r}.".format(
                i, ev.get("direction")))
        tick_sebelum, urutan_sebelum = tick, seq
    return data


def load_input_recording(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        raise RecordingError("Gagal membaca file rekaman: {0}".format(exc)) from exc
    return validate_recording(data)


def config_warnings(recording):
    """Peringatan bila rekaman dibuat dengan konfigurasi berbeda dari sekarang."""
    awas = []
    init = recording.get("initial_state", {})
    cfg = init.get("game_config", {})
    if recording.get("simulation_tick_rate") != config.FPS:
        awas.append("tick rate rekaman {0} != FPS kini {1}".format(
            recording.get("simulation_tick_rate"), config.FPS))
    for kunci, sekarang in (("pacman_move_delay", config.PACMAN_MOVE_DELAY),
                            ("ghost_move_delay", config.GHOST_MOVE_DELAY),
                            ("start_delay_seconds", config.START_DELAY_SECONDS)):
        nilai = cfg.get(kunci)
        if isinstance(nilai, (int, float)) and abs(float(nilai) - float(sekarang)) > 1e-6:
            awas.append("{0} rekaman {1} != kini {2}".format(kunci, nilai, sekarang))
    return awas


# ---------------------------------------------------------------------------
# Playback: menyuntik perintah rekaman ke game yang sedang berjalan
# ---------------------------------------------------------------------------
class PlaybackRunner:
    """Memainkan input_events pada tick yang sama, lewat game.submit_input()."""

    def __init__(self, recording, algorithm, game, tail_ticks=None):
        self.recording = recording
        self.name = recording["recording_name"]
        self.algorithm = str(algorithm).lower()
        self.events = copy.deepcopy(recording["input_events"])
        self.index = 0
        self.tick = 0
        self.applied = []
        self.desync = []
        self.finished = False
        self.stopped = False
        self.status = "playing"
        self.source_path: str | None = None  # diisi oleh ExperimentSession saat PRE-game
        last = max((int(e["tick"]) for e in self.events), default=0)
        self.last_event_tick = last
        self.tail_ticks = int(tail_ticks if tail_ticks is not None
                              else max(10, recording["simulation_tick_rate"]))
        self.total_ticks = last + self.tail_ticks
        game.playback_mode = True

    def inject(self, game, tick):
        """Masukkan semua event yang jatuh pada tick ini, urut sesuai sequence."""
        while self.index < len(self.events) and self.events[self.index]["tick"] <= tick:
            ev = self.events[self.index]
            if ev["tick"] < tick:
                self.desync.append({"tick": ev["tick"], "sequence": ev["sequence"]})
            arah = config.DIRECTION_BY_NAME[ev["direction"]]
            game.submit_input(ev["event"], arah, record=False)
            self.applied.append({
                "tick": ev["tick"], "sequence": ev["sequence"],
                "event": ev["event"], "direction": ev["direction"],
            })
            self.index += 1

    def advance(self, game):
        self.tick += 1
        if game.state != config.STATE_PLAYING:
            self.finish(game, "ended")
        elif self.index >= len(self.events) and self.tick >= self.total_ticks:
            self.finish(game, "completed")

    def stop(self, game):
        self.stopped = True
        self.finish(game, "stopped")

    def finish(self, game, status):
        if self.finished:
            return
        self.status = status
        self.finished = True
        game.playback_mode = False

    def result(self, game):
        stats = game.get_stats()
        if game.state == config.STATE_WIN:
            winner = "pacman"
        elif game.state == config.STATE_LOSE:
            winner = "ghost"
        else:
            winner = "belum selesai"
        return {
            "recording": self.name,
            "algorithm": self.algorithm,
            "status": self.status,
            "ticks": self.tick,
            "winner": winner,
            "stats": {
                "search_time_ms": float(stats.get("search_time_ms", 0.0)),
                "nodes_explored": int(stats.get("nodes_explored", 0)),
                "path_length": int(stats.get("path_length", 0)),
            },
            "input_count": len(self.applied),
            "desync_count": len(self.desync),
            "initial_state": {
                "maze_file": self.recording["initial_state"].get("maze_file"),
                "player": list(self.recording["initial_state"]["player"]),
                "ghosts": [list(g["pos"]) for g in self.recording["initial_state"]["ghosts"]],
                "random_seed": self.recording["initial_state"].get("random_seed"),
            },
        }


class ExperimentSession:
    """State bersama panel UI: recorder, playback, pilihan algoritma, hasil."""

    def __init__(self, directory=None):
        self.directory = directory or config.RECORDINGS_DIR
        self.recorder = InputRecorder()
        self.runner = None
        self.algorithm = "bfs"
        self.selected_index = 0
        self.results = []
        self.last_result = None
        self.message = "Siap. Rekam input lalu putar ulang untuk BFS dan A*."
        self.message_kind = "info"
        self.name_focused = False
        self.paths = []
        self.selected_name = None
        self.last_record_info = None
        self._dir_mtime = None

    def set_message(self, text, kind="info"):
        self.message = str(text)
        self.message_kind = kind

    def refresh(self, force=False):
        """Cache daftar file; dipanggil ulang tiap frame dan setelah delete/save."""
        try:
            mtime = os.path.getmtime(self.directory)
        except OSError:
            mtime = None
        if not force and self.paths and self._dir_mtime == mtime:
            return self.paths
        self._dir_mtime = mtime
        self.paths = list_input_recordings(self.directory)
        self.selected_index = max(0, min(self.selected_index, len(self.paths) - 1))
        return self.paths

    def start_recording(self, game, tick):
        from core.game import snapshot_initial_state  # impor lambat: hindari siklus
        if self.runner is not None and not self.runner.finished:
            self.set_message("Hentikan playback sebelum mulai rekaman.", "warn")
            return
        state = snapshot_initial_state(game)
        self.recorder.initial_state = state
        self.recorder.start(state, name=self.recorder.name,
                            algorithm=game.algorithm, tick=tick)
        if game.condition != "bergerak":
            game.condition = "bergerak"  # input pemain hanya diproses pada mode ini
        self.set_message("REC aktif: {0}".format(self.recorder.name), "rec")

    def stop_recording(self, game=None, tick=None):
        self.recorder.stop(tick=tick,
                           release_keys=(getattr(game, "key_dir", None)
                                         if game is not None else None))
        if not self.recorder.events:
            self.set_message("Rekaman kosong; tidak ada file yang disimpan.", "warn")
            self.last_record_info = {
                "name": self.recorder.name, "file": None, "count": 0,
                "ticks": self.recorder.last_tick, "message": self.message,
            }
            return None
        path = save_input_recording(self.recorder.snapshot(), self.directory)
        self.refresh()
        if self.paths:
            self.selected_index = self.paths.index(path)
        self.set_message("Tersimpan: {0} ({1} input)".format(
            os.path.basename(path), len(self.recorder.events)), "ok")
        self.last_record_info = {
            "name": self.recorder.name, "file": path,
            "count": len(self.recorder.events),
            "ticks": self.recorder.last_tick, "message": self.message,
        }
        return path

    @property
    def selected_path(self):
        if not self.paths:
            return None
        return self.paths[self.selected_index]

    def pilih_rekaman(self, path):
        self.refresh()
        if path in self.paths:
            self.selected_index = self.paths.index(path)
            return True
        return False

    def build_playback_game(self, algorithm=None, path=None):
        """Bangun game dari rekaman SEBELUM gameplay; kembalikan (game, runner)."""
        self.refresh()
        path = path or self.selected_path
        if path is None:
            self.set_message("Belum ada rekaman untuk diputar.", "warn")
            return None, None
        try:
            data = load_input_recording(path)
        except RecordingError as exc:
            self.set_message("Gagal memuat: {0}".format(exc), "err")
            return None, None
        if not data["input_events"]:
            self.set_message("Rekaman kosong; tidak bisa diputar.", "warn")
            return None, None
        if self.recorder.active:
            self.stop_recording()
        self.recorder.active = False
        algo = str(algorithm or self.algorithm).lower()
        try:
            from core.game import build_game_from_recording
            baru = build_game_from_recording(data, algo)
        except (ValueError, TypeError, KeyError, OSError) as exc:
            self.set_message("Gagal membangun ulang kondisi awal: {0}".format(exc), "err")
            return None, None
        self.algorithm = algo
        self.pilih_rekaman(path)
        self.runner = PlaybackRunner(data, algo, baru)
        self.runner.source_path = os.path.abspath(path)
        amaran = config_warnings(data)
        pesan = "PLAYBACK {0}: {1}".format(algo.upper(), data["recording_name"])
        if amaran:
            pesan += " (peringatan: {0})".format(amaran[0])
        self.set_message(pesan, "play")
        return baru, self.runner

    def start_playback(self, game, tick):
        """Kompatibilitas pemanggil lama; game baru dipilih sebelum loop dimulai."""
        baru, runner = self.build_playback_game()
        return (baru if baru is not None else game), runner

    @property
    def active_recording_path(self):
        """File yang sedang dipakai playback aktif (tidak boleh dihapus)."""
        if self.runner is not None and not self.runner.finished:
            return getattr(self.runner, "source_path", None)
        return None

    def hapus_rekaman(self, path):
        """Hapus satu rekaman lewat backend tervalidasi; kembalikan True/False."""
        try:
            nama = delete_input_recording(
                path, self.directory, active_path=self.active_recording_path)
        except RecordingError as exc:
            self.set_message("Gagal menghapus: {0}".format(exc), "err")
            return False
        self.refresh(force=True)
        self.set_message("Rekaman dihapus: {0}".format(nama), "ok")
        return True

    def hapus_semua_rekaman(self):
        """Hapus semua rekaman valid; kembalikan ringkasan backend."""
        try:
            hasil = delete_all_input_recordings(
                self.directory, active_path=self.active_recording_path)
        except RecordingError as exc:
            self.set_message("Gagal menghapus: {0}".format(exc), "err")
            return {"deleted": [], "skipped": [], "errors": [str(exc)]}
        self.refresh(force=True)
        self.set_message("Dihapus {0} rekaman; {1} dilewati; {2} gagal.".format(
            len(hasil["deleted"]), len(hasil["skipped"]),
            len(hasil["errors"])), "ok")
        return hasil

    def stop_playback(self, game):
        if self.runner is None or self.runner.finished:
            return
        self.runner.stop(game)
        self._simpan_hasil(game)

    def _simpan_hasil(self, game):
        if self.runner is None:
            return
        hasil = self.runner.result(game)
        self.results = [r for r in self.results
                        if not (r["recording"] == hasil["recording"]
                                and r["algorithm"] == hasil["algorithm"])]
        self.results.append(hasil)
        self.results.sort(key=lambda r: (r["recording"], r["algorithm"]))
        self.last_result = hasil
        hasil["_game"] = game  # penanda in-memory: hasil ini milik game yang baru saja selesai

    def selesai_playback(self, game):
        if self.runner is None or not self.runner.finished:
            return
        if getattr(self, "_results_saved", None) is self.runner:
            return
        self._simpan_hasil(game)
        self._results_saved = self.runner
        self.set_message("Playback {0} selesai ({1}).".format(
            self.runner.algorithm.upper(), self.runner.status), "ok")

    def clear_results(self):
        self.results = []
        self.last_result = None
