Letakkan file musik latar (BGM) di folder ini.

Nama file yang dikenali (huruf kecil):
  bgm.ogg   -- direkomendasikan (Ogg Vorbis, kecil, looping mulus)
  bgm.mp3   -- alternatif umum
  bgm.wav   -- alternatif tanpa kompresi (ukuran besar)

Satu file sudah cukup. core/audio.py memilih file pertama yang tersedia
dalam urutan di atas. Bila tidak ada file, game tetap berjalan tanpa BGM.

Gunakan musik karya sendiri atau berlisensi yang mengizinkan penggunaan Anda
(misalnya CC0 / bebas royalti). Proyek ini tidak mengunduh musik otomatis.

Kontrol saat aplikasi berjalan (berlaku di semua layar):
  M   = nyala / mati musik, tanpa memutar ulang dari awal
  -   = volume turun 0.05
  +   = volume naik 0.05 (tombol =/+ pada keyboard)

Volume awal 0.18 dari 1.0, diatur lewat core/config.py -> AUDIO_VOLUME.
