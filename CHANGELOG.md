# Changelog

Semua perubahan penting dicatat di sini.
Format: [Keep a Changelog](https://keepachangelog.com/) + [SemVer](https://semver.org/).

## [1.1.0] - 2026-10-07

### Added
- Tema UI dengan 4 pilihan: Midnight, Nord, Dracula, Light
- Warna tetap per kelas (deterministik) untuk bounding box
- Auto-suggest bounding box dengan YOLO COCO (`Ctrl+A`)
- Progress timeline + filter file + distribusi kelas
- Auto-save anotasi & resume posisi terakhir
- Split dataset dengan input numerik + live count
- Generator notebook Colab untuk 5 versi YOLO
- Evaluasi model + analisis results.csv
- Panduan 9 sub-tab di dalam aplikasi

### Fixed
- Kontras teks pada tema gelap (fg_muted, danger, warning)
- Bar chart distribusi kelas tidak terbaca di tema gelap
- Warna tema nyangkut saat ganti tema berulang

## [1.0.0] - 2026-10-05

### Added
- Rilis awal: akuisisi (video/webcam), anotasi, split, export,
  training Colab, evaluasi.