# Cara Mengecek Frontend dan Backend

## A. Frontend saja (tanpa database)
```bash
cd frontend
cp .env.local.example .env.local      # ubah NEXT_PUBLIC_USE_MOCK=true
npm install && npm run dev            # http://localhost:3000
```
Login `peneliti@ipb.ac.id / Peneliti#123`. Reset data: DevTools > Application > Local Storage > hapus.

## B. Frontend + backend sungguhan
Terminal 1: ikuti `backend/README_BACKEND.md` (database lalu `uvicorn app.main:app --port 8000`).
Terminal 2: `cd frontend`, `NEXT_PUBLIC_USE_MOCK=false`, `npm run dev`.

## C. Skenario uji manual
1. Login salah → pesan error; login benar → Unggah Data.
2. Unggah: .txt ditolak; pasangan `a_R1` + `b_R2` ditolak; metadata kosong ditolak; 1 file = Single-end, 2 file cocok = Paired-end. (FASTQ uji: 4 baris `@r1`/`ACGT`/`+`/`IIII`, lalu gzip.)
3. Pengaturan: Min Depth 5000 ditolak; Simpan Draf tanpa referensi boleh; Konfirmasi tanpa genom ditolak; anotasi kosong = tahap anotasi dilewati.
4. Eksekusi: ringkasan sesuai input; tombol nonaktif jika data kurang.
5. Status & Log: progres naik, log bertambah. Sampel "uji-gagal" → Gagal + tombol analisis baru.
6. Hasil: statistik, tabel, unduh CSV/VCF, Kunci, Publikasikan. Setelah dikunci, Pengaturan read-only.
7. Database Varian: cari `BRCA1`, `chr17:41196312`, `chr1:abc` (ditolak), filter QUAL, klik kode sampel. Login akun lain: varian terpublikasi terlihat, analisis orang lain tidak.
8. Admin: menu hanya untuk administrator; tambah/edit akun; unggah/hapus referensi (yang dipakai analisis tidak bisa dihapus).
9. Chip "Analisis aktif": pindah analisis dan "+ Analisis baru".

## D. Cek lewat database
```sql
SELECT id_analisis,status,tahap_saat_ini,progres_persen,terkunci,dipublikasikan FROM analisis;
SELECT tahap,jenis_pesan,pesan FROM log_proses WHERE id_analisis=1 ORDER BY waktu;
SELECT jenis_aksi,jenis_objek,count(*) FROM log_akses GROUP BY 1,2;
```
