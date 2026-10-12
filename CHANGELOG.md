# Changelog

Semua perubahan penting dicatat di sini.
Format: [Keep a Changelog](https://keepachangelog.com/) + [SemVer](https://semver.org/).

## [1.1.1] - 2026-10-12

### Added
- Auto-release otomatis via GitHub Actions (trigger dari tag `v*.*.*`)
- Screenshot tab Panduan di README
- Section "Fitur Unggulan" di panduan Alur Singkat (6 fitur kunci)
- Section "Alur Detail per Tab" di panduan Alur Singkat
- Badge Release & Downloads di README

### Changed
- Sinkronisasi nama file screenshot (`01` s/d `08`) agar konsisten
- Perbaikan urutan tombol kontrol ukuran font di tab Panduan
- README direstrukturisasi dengan section screenshot, hasil prediksi, dan hasil training

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
- Prediksi gambar, video, dan kamera real-time
- Import hasil training (ZIP) dengan viewer grafik
- Panduan 10 sub-tab di dalam aplikasi
- Support YOLO v12, v13, v26

### Fixed
- Kontras teks pada tema gelap (fg_muted, danger, warning)
- Bar chart distribusi kelas tidak terbaca di tema gelap
- Warna tema nyangkut saat ganti tema berulang
- Validasi lokal pakai `data.yaml` dengan path lokal (bukan path Colab)
- Canvas redraw guard saat jendela anotator baru dibuka

## [1.0.0] - 2026-10-05

### Added
- Rilis awal: akuisisi (video/webcam), anotasi, split, export, training Colab, evaluasi