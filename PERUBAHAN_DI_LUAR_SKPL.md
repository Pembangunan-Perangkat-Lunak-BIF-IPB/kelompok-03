# Perubahan di Luar SKPL (untuk Laporan Mingguan)

Disusun dari seluruh pekerjaan implementasi. Setiap butir yang tidak tertulis di SKPL/desain ditandai agar bisa dicantumkan di laporan dan, bila disetujui tim, dimasukkan ke revisi SKPL oleh System Analyst.

## A. Perubahan struktur database (migrasi `database/03_akun_verifikasi.sql`)
| # | Perubahan | Rincian | Dampak |
|---|---|---|---|
| 1 | **Kolom baru** `pengguna.email_terverifikasi` | `BOOLEAN NOT NULL DEFAULT FALSE`. Akun yang sudah ada otomatis `TRUE` saat migrasi | Login ditolak jika `FALSE`. Akun buatan admin langsung `TRUE` |
| 2 | **Tabel baru** `token_email` | `id_token`, `id_pengguna` (FK → pengguna, `ON DELETE CASCADE`), `jenis` (`verifikasi` / `reset_sandi`), `token_hash` (SHA-256, UNIQUE), `kedaluwarsa`, `dipakai_pada`, `dibuat_pada`; indeks `(id_pengguna, jenis)` | Menyimpan hanya hash token. Satu pengguna dapat memiliki banyak token |

Tidak ada perubahan pada tabel, kolom, atau constraint yang sudah ada (termasuk `log_akses`, yang tetap `ON DELETE RESTRICT`). Pencatatan jejak akses untuk verifikasi dan reset kata sandi memakai nilai yang sudah ada (`jenis_objek='akun'`, `jenis_aksi='ubah'`). **ERD/skema Minggu 6 perlu diperbarui** dengan butir 1 dan 2.

## B. Fitur di luar SKPL
SKPL hanya memuat UC-07 (administrator mengelola akun, FR-21 berprioritas *Could*). Tidak ada use case registrasi mandiri.
| Fitur | Keterangan | Status terhadap SKPL |
|---|---|---|
| Registrasi mandiri (halaman Daftar) | Semua domain email boleh; peran selalu peneliti; kata sandi min. 8 karakter | **Di luar SKPL** |
| Verifikasi email | Tautan token sekali pakai, berlaku 24 jam; akun aktif langsung setelah verifikasi (tanpa persetujuan admin) | **Di luar SKPL** |
| Kirim ulang email verifikasi | Token lama dibatalkan; respons generik | **Di luar SKPL** |
| Lupa dan atur ulang kata sandi | Tautan berlaku 60 menit, sekali pakai; membuka tautan juga memverifikasi email | **Di luar SKPL** |
| Pembatas percobaan | Daftar/kirim ulang/lupa sandi: 5 kali per 15 menit per IP; login: 10 kali | **Di luar SKPL** (keamanan) |
| Admin melihat status verifikasi dan menghapus akun | Hapus hanya untuk akun tanpa sampel, analisis, dan jejak akses; selain itu dinonaktifkan | Cakupan UC-07 "mengelola akun"; aturan hapusnya adalah keputusan implementasi |

**Usulan revisi SKPL (untuk System Analyst):** tambah use case "Registrasi dan Verifikasi Akun" (aktor: calon pengguna), "Mengatur Ulang Kata Sandi", FR terkait, serta aturan bisnis: akun hanya aktif setelah email terverifikasi; registrasi mandiri selalu berperan peneliti; token verifikasi/reset berlaku terbatas dan sekali pakai.

## C. Perubahan sebelumnya yang juga berbeda dari SKPL/desain
| Perubahan | Alasan |
|---|---|
| Halaman Login ditambahkan | Tidak ada di 7 desain, dibutuhkan UC-07 dan hak akses |
| Parameter ke-3 "Min QUAL" di Pengaturan | Ada di default JSON `analisis.parameter`, tidak di desain |
| Kolom QUAL di tabel Database Varian | UC-06 mewajibkan kualitas tampil |
| 6 tahap pipeline (ditambah Pemrosesan BAM dan Filtering) | Mengikuti enum DB, desain hanya menampilkan 4-5 |
| Chip "Analisis aktif" (riwayat dan pemilih analisis) | Alur end-to-end butuh penentu analisis yang sedang dikerjakan (FR-17) |
| Modal detail varian | FR-18; halaman detail belum didesain |
| Peneliti dapat mengunggah referensi dari halaman Pengaturan | UC-02 "memilih atau mengunggah referensi" |
| Tombol "Buat analisis baru" untuk analisis gagal/terkunci | BR-05: ubah = analisis baru |
| Rentang parameter (Min Quality 0-40, Min Depth 1-1000, Min QUAL 0-1000) | SKPL tidak menyebut angka (BR-04); **perlu dikonfirmasi** |
| Batas unggah 2048 MB | SKPL hanya menyebut "ukuran wajar"; **perlu dikonfirmasi** |
| Mode pipeline `simulasi` | Tool bioinformatika dan referensi belum tersedia; hasil acak, bukan analisis sungguhan |

## D. Batasan yang perlu jujur dicantumkan
- Pengiriman email lewat Gmail SMTP **belum diuji** (alur diuji dengan mode pengembangan yang mencetak tautan di terminal backend).
- Setelah kata sandi di-reset, sesi login lama tetap berlaku hingga kedaluwarsa (12 jam).
- Pesan "email sudah terdaftar" pada pendaftaran memungkinkan orang menebak email terdaftar. Dipilih demi kemudahan pengguna; dapat diganti pesan generik.
- Pembatas percobaan disimpan di memori server (hilang saat restart).
- Belum ada enkripsi data genomik at-rest, serta FR-15, FR-20, dan halaman riwayat akses.
