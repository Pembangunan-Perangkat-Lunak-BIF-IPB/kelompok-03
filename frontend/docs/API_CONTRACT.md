# Kontrak API Frontend ↔ Backend (Human GVC)

Dipakai `frontend/lib/api.js` saat `NEXT_PUBLIC_USE_MOCK=false`. Semua endpoint kecuali login memakai `Authorization: Bearer <token>`. Error: HTTP 4xx/5xx dengan `{"detail": "pesan Indonesia"}`; pesan ditampilkan apa adanya ke pengguna (NFR Usability). Nama field mengikuti `database/01_schema.sql`.

| Endpoint | Fungsi | Rujukan SKPL |
|---|---|---|
| `POST /api/auth/login` `{email,password}` → `{token, pengguna:{id_pengguna,nama,email,peran}}` | Tolak akun `aktif=false` atau email belum terverifikasi (403); catat log_akses login | prakondisi UC-01, FR-13 |
| `POST /api/auth/daftar` `{nama,email,password}` → 201 `{pesan}` | Registrasi mandiri, peran selalu `peneliti`, `email_terverifikasi=false`, kirim email token. 409 jika email ada | **di luar SKPL** |
| `POST /api/auth/verifikasi` `{token}` · `POST /api/auth/kirim-ulang` `{email}` | Aktifkan akun / kirim ulang (jawaban generik, tidak membocorkan keberadaan akun) | di luar SKPL |
| `POST /api/auth/lupa` `{email}` · `POST /api/auth/reset` `{token,password}` | Atur ulang kata sandi lewat tautan email | di luar SKPL |
| `DELETE /api/pengguna/{id}` (admin) | Hanya akun tanpa sampel, analisis, dan jejak akses; selain itu 409 (nonaktifkan) | UC-07 |
| `POST /api/sampel` multipart (`nama_sampel,lokasi,strain,karakteristik,fastq_r1,fastq_r2?`) → analisis draf (+ `id_referensi` genom bawaan) | Simpan ke storage, validasi ulang format/pasangan, insert `sampel` + `analisis` | UC-01, FR-01/02/04, BR-02/03 |
| `GET /api/referensi?jenis=genom\|anotasi` | Daftar referensi | UC-02, FR-03 |
| `POST /api/referensi` multipart (`nama_referensi,jenis,berkas`) | Status `unggahan`, `id_pengunggah` | UC-02/07 |
| `DELETE /api/referensi/{id}` (admin) | 409 jika masih dipakai (FK RESTRICT) | UC-07 |
| `GET /api/analisis` | Hanya milik pemanggil | FR-17, BR-07 |
| `GET /api/analisis/{id}` → analisis + `sampel`, `referensi`, `anotasi` | 404 jika bukan milik | BR-07 |
| `PATCH /api/analisis/{id}` `{id_referensi?,id_referensi_anotasi?,parameter?}` | 422 jika di luar rentang; tolak jika bukan `draf`/terkunci | UC-02, FR-06, BR-04/05 |
| `POST /api/analisis/{id}/jalankan` | Cek BR-01 → `menunggu` → Job Manager | UC-03, FR-05 |
| `GET /api/analisis/{id}/log` → `[log_proses]` | Dipolling 3 detik | UC-04, FR-07/08 |
| `POST /api/analisis/{id}/salin` → analisis draf baru | Jalankan ulang sebagai analisis baru | BR-05 |
| `GET /api/analisis/{id}/ringkasan` → `{total_varian,ti_tv,qual_rata2}` | Statistik | FR-12 |
| `GET /api/analisis/{id}/varian?page&size` → `{total,page,size,items}` | Tabel hasil | UC-05 |
| `POST /api/analisis/{id}/kunci` · `POST .../publikasi` | Hanya status `selesai` | FR-10/11, BR-05/06 |
| `GET /api/analisis/{id}/unduh?format=vcf\|csv` | Berkas; catat log_akses unduh | FR-09/19 |
| `GET /api/varian?q&kromosom&qual_min&page&size` → `{total,page,size,items:[{id_varian,id_analisis,id_sampel,sampel_dibuat,nama_sampel,kromosom,posisi,ref,alt,quality_score,gen,pengunggah}]}` | Hanya analisis `dipublikasikan` | UC-06, FR-11 |
| `GET /api/varian/{id}` → varian + `genotipe{}`, `sampel`, `pengunggah` | Detail | FR-18 |
| `GET/POST /api/pengguna`, `PATCH /api/pengguna/{id}` (admin) `{nama,email,password?,peran,aktif}` | Email unik | UC-07, FR-21 |

Kode sampel tampilan `SAMP-<tahun>-<id 3 digit>` dibentuk frontend dari `id_sampel` dan `dibuat_pada`.
