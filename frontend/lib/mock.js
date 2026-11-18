// Backend tiruan di localStorage supaya alur 1-7 bisa dicoba tanpa API.
// Bentuk data = kolom tabel di database/01_schema.sql. Aktifkan: NEXT_PUBLIC_USE_MOCK=true
import { PARAM_DEFAULT, STAGES } from "./constants";

const KEY = "gvc_mockdb";
const now = () => Date.now();
const iso = (t = now()) => new Date(t).toISOString();
const delay = (ms = 250) => new Promise((r) => setTimeout(r, ms));
const fail = (m) => { throw new Error(m); };

// pipeline tiruan: durasi tiap tahap (ms). Nama sampel mengandung "gagal" => gagal di alignment.
const STAGE_MS = 5000;
const TOTAL = STAGE_MS * STAGES.length;

function seedVarian(analisisId, sampelId, n, seed) {
  const chrs = ["chr1", "chr2", "chr7", "chr12", "chr17", "chr19"];
  const gens = ["BRCA1", "TP53", "CFTR", "APOE", "EGFR", "KRAS", "BRCA2", "MTHFR"];
  const bases = ["A", "C", "G", "T"]; let s = seed;
  const rnd = () => ((s = (s * 1664525 + 1013904223) % 4294967296) / 4294967296);
  return Array.from({ length: n }, (_, i) => {
    const ref = bases[Math.floor(rnd() * 4)]; let alt = bases[Math.floor(rnd() * 4)]; if (alt === ref) alt = bases[(bases.indexOf(ref) + 1) % 4];
    return {
      id_varian: seed * 1000 + i + 1, id_analisis: analisisId, kromosom: chrs[Math.floor(rnd() * chrs.length)],
      posisi: 1000000 + Math.floor(rnd() * 140000000), ref, alt, quality_score: +(20 + rnd() * 79).toFixed(1),
      gen: rnd() > 0.4 ? gens[Math.floor(rnd() * gens.length)] : null,
      genotipe: { genotipe: rnd() > 0.5 ? "0/1" : "1/1", kedalaman: 10 + Math.floor(rnd() * 60), kualitas_genotipe: +(30 + rnd() * 69).toFixed(1), id_sampel: sampelId },
    };
  }).sort((a, b) => a.kromosom.localeCompare(b.kromosom) || a.posisi - b.posisi);
}

function load() {
  let db = null;
  try { db = JSON.parse(localStorage.getItem(KEY)); } catch {}
  if (db) return db;
  const t = now() - 864e5 * 3;
  db = {
    seq: { pengguna: 3, sampel: 2, referensi: 4, analisis: 2 },
    pengguna: [
      { id_pengguna: 1, nama: "Rakazaki Putra Hendrawan", email: "rakahendrawan@ipb.ac.id", password: "Admin#123", peran: "administrator", aktif: true, email_terverifikasi: true, dibuat_pada: iso(t) },
      { id_pengguna: 2, nama: "Yaphets Mubakar", email: "peneliti@ipb.ac.id", password: "Peneliti#123", peran: "peneliti", aktif: true, dibuat_pada: iso(t) },
      { id_pengguna: 3, nama: "Peneliti B", email: "penelitib@ipb.ac.id", password: "Peneliti#123", peran: "peneliti", aktif: true, dibuat_pada: iso(t) },
    ],
    referensi: [
      { id_referensi: 1, nama_referensi: "GRCh38.fasta", status: "bawaan", jenis: "genom", id_pengunggah: null, dibuat_pada: iso(t) },
      { id_referensi: 2, nama_referensi: "dbSNP_v155.vcf.gz", status: "bawaan", jenis: "anotasi", id_pengunggah: null, dibuat_pada: iso(t) },
    ],
    sampel: [
      { id_sampel: 1, id_pengguna: 3, nama_sampel: "SAMP-A", lokasi: "Bogor, Jawa Barat", strain: "-", karakteristik: "Jaringan tumor", tipe_baca: "paired-end", lokasi_fastq_r1: "s3://x/a_R1.fastq.gz", lokasi_fastq_r2: "s3://x/a_R2.fastq.gz", dibuat_pada: iso(t) },
      { id_sampel: 2, id_pengguna: 3, nama_sampel: "SAMP-B", lokasi: "Jember, Jawa Timur", strain: "-", karakteristik: "Darah normal", tipe_baca: "single-end", lokasi_fastq_r1: "s3://x/b.fastq.gz", lokasi_fastq_r2: null, dibuat_pada: iso(t) },
    ],
    analisis: [
      { id_analisis: 1, id_pengguna: 3, id_sampel: 1, id_referensi: 1, id_referensi_anotasi: 2, tanggal: iso(t), status: "selesai", parameter: PARAM_DEFAULT, tahap_saat_ini: "anotasi", progres_persen: 100, log_kesalahan: null, keterangan: null, terkunci: true, dipublikasikan: true, mulai_ms: t, ok: true },
      { id_analisis: 2, id_pengguna: 3, id_sampel: 2, id_referensi: 1, id_referensi_anotasi: 2, tanggal: iso(t), status: "selesai", parameter: PARAM_DEFAULT, tahap_saat_ini: "anotasi", progres_persen: 100, log_kesalahan: null, keterangan: null, terkunci: true, dipublikasikan: true, mulai_ms: t, ok: true },
    ],
    varian: [...seedVarian(1, 1, 12, 7), ...seedVarian(2, 2, 12, 11)],
    log: [],
  };
  save(db); return db;
}
const save = (db) => localStorage.setItem(KEY, JSON.stringify(db));
const me = () => { const u = JSON.parse(localStorage.getItem("gvc_user") || "null"); if (!u) fail("Sesi berakhir. Silakan masuk kembali."); return u; };
const pub = (u) => { const { password, ...r } = u; return r; };

function logFor(a, sampel) {
  const t0 = a.mulai_ms, L = []; const el = Math.max(0, now() - t0);
  const add = (off, tahap, jenis_pesan, pesan) => { if (el >= off) L.push({ waktu: iso(t0 + off), tahap, jenis_pesan, pesan }); };
  add(0, null, "info", "Memulai pipeline...");
  const failAt = a.fail_stage;
  STAGES.forEach((s, i) => {
    const b = i * STAGE_MS;
    if (s.key === "anotasi" && !a.id_referensi_anotasi) { add(b, s.key, "info", "Berkas anotasi tidak dipilih. Tahap anotasi dilewati."); return; }
    add(b + 200, s.key, "info", `Memulai tahap ${s.label}...`);
    if (failAt === s.key) { add(b + 2500, s.key, "error", `Tahap ${s.label} gagal: kode keluar 1 (data tidak dapat diproses).`); return; }
    add(b + STAGE_MS / 2, s.key, "berjalan", `Memproses ${s.label} (${sampel?.nama_sampel || "sampel"})...`);
    add(b + STAGE_MS - 200, s.key, "berhasil", `${s.label} selesai.`);
  });
  return L;
}

// hitung status dari waktu berjalan (tanpa timer), lalu bekukan saat selesai/gagal
function tick(db, a) {
  if (!["menunggu", "berjalan"].includes(a.status)) return a;
  const el = now() - a.mulai_ms, sampel = db.sampel.find((s) => s.id_sampel === a.id_sampel);
  const failIdx = a.fail_stage ? STAGES.findIndex((s) => s.key === a.fail_stage) : -1;
  if (el < 1500) { a.status = "menunggu"; a.progres_persen = 0; return a; }
  a.status = "berjalan";
  if (failIdx >= 0 && el >= failIdx * STAGE_MS + 2500) {
    a.status = "gagal"; a.tahap_saat_ini = a.fail_stage; a.progres_persen = Math.round((failIdx / STAGES.length) * 100);
    a.log_kesalahan = `Tahap ${STAGES[failIdx].label} gagal: kode keluar 1 (data tidak dapat diproses).`;
  } else if (el >= TOTAL) {
    a.status = "selesai"; a.progres_persen = 100; a.tahap_saat_ini = "anotasi";
    if (!a.id_referensi_anotasi) a.keterangan = "Anotasi dilewati: berkas anotasi tidak tersedia.";
    const v = seedVarian(a.id_analisis, a.id_sampel, 40, a.id_analisis * 13 + 5);
    if (!a.id_referensi_anotasi) v.forEach((x) => (x.gen = null));
    db.varian.push(...v);
  } else {
    const i = Math.min(STAGES.length - 1, Math.floor(el / STAGE_MS)); a.tahap_saat_ini = STAGES[i].key;
    a.progres_persen = Math.min(99, Math.round((el / TOTAL) * 100));
  }
  save(db); return a;
}
function full(db, a) {
  const R = (id) => db.referensi.find((r) => r.id_referensi === id) || null;
  return { ...a, sampel: db.sampel.find((s) => s.id_sampel === a.id_sampel) || null, referensi: R(a.id_referensi), anotasi: R(a.id_referensi_anotasi) };
}
function own(db, id) {
  const u = me(), a = db.analisis.find((x) => x.id_analisis === Number(id));
  if (!a || (a.id_pengguna !== u.id_pengguna)) fail("Analisis tidak ditemukan atau bukan milik akun Anda."); // BR-07
  return tick(db, a);
}
const pageOf = (arr, page, size) => ({ total: arr.length, page, size, items: arr.slice((page - 1) * size, page * size) });

export const mock = {
  async login(email, password) {
    await delay(); const db = load();
    const u = db.pengguna.find((x) => x.email.toLowerCase() === email.toLowerCase() && x.password === password);
    if (!u) fail("Email atau kata sandi salah."); if (!u.aktif) fail("Akun dinonaktifkan. Hubungi administrator.");
    if (u.email_terverifikasi === false) fail("Email belum diverifikasi. Periksa kotak masuk Anda atau kirim ulang email verifikasi.");
    return { token: "mock-" + u.id_pengguna, pengguna: pub(u) };
  },
  // --- akun (mode tiruan: tautan email dikembalikan langsung sebagai `tautan_dev`; backend asli TIDAK pernah melakukannya)
  async daftar(nama, email, password) {
    await delay(); const db = load();
    if (!nama.trim()) fail("Nama wajib diisi."); if (!/^\S+@\S+\.\S+$/.test(email)) fail("Format email tidak valid."); if (password.length < 8) fail("Kata sandi minimal 8 karakter.");
    const ada = db.pengguna.find((u) => u.email.toLowerCase() === email.toLowerCase());
    if (ada) fail(ada.email_terverifikasi === false ? "Email sudah terdaftar tetapi belum diverifikasi. Gunakan 'Kirim ulang email verifikasi' di halaman masuk." : "Email sudah terdaftar. Silakan masuk.");
    const u = { id_pengguna: ++db.seq.pengguna, nama: nama.trim(), email, password, peran: "peneliti", aktif: true, email_terverifikasi: false, dibuat_pada: iso() };
    db.pengguna.push(u); const t = "mock" + Math.random().toString(36).slice(2); (db.tokens ||= []).push({ t, id: u.id_pengguna, jenis: "verifikasi" }); save(db);
    return { pesan: "Pendaftaran berhasil. Kami mengirim tautan verifikasi ke email Anda. Akun dapat dipakai setelah email diverifikasi.", tautan_dev: "/verifikasi?token=" + t };
  },
  async verifikasi(token) {
    await delay(); const db = load(), k = (db.tokens || []).find((x) => x.t === token && x.jenis === "verifikasi");
    if (!k) fail("Tautan verifikasi tidak valid atau sudah tidak berlaku.");
    const u = db.pengguna.find((x) => x.id_pengguna === k.id); if (u.email_terverifikasi !== false) return { pesan: "Email sudah terverifikasi. Silakan masuk." };
    u.email_terverifikasi = true; save(db); return { pesan: "Email berhasil diverifikasi. Silakan masuk." };
  },
  async kirimUlang(email) {
    await delay(); const db = load(), u = db.pengguna.find((x) => x.email.toLowerCase() === email.toLowerCase() && x.email_terverifikasi === false), r = { pesan: "Jika email terdaftar, instruksi telah dikirim. Periksa kotak masuk dan folder spam." };
    if (u) { const t = "mock" + Math.random().toString(36).slice(2); db.tokens = (db.tokens || []).filter((x) => !(x.id === u.id_pengguna && x.jenis === "verifikasi")); db.tokens.push({ t, id: u.id_pengguna, jenis: "verifikasi" }); save(db); r.tautan_dev = "/verifikasi?token=" + t; }
    return r;
  },
  async lupa(email) {
    await delay(); const db = load(), u = db.pengguna.find((x) => x.email.toLowerCase() === email.toLowerCase()), r = { pesan: "Jika email terdaftar, instruksi telah dikirim. Periksa kotak masuk dan folder spam." };
    if (u) { const t = "mock" + Math.random().toString(36).slice(2); db.tokens = (db.tokens || []).filter((x) => !(x.id === u.id_pengguna && x.jenis === "reset")); db.tokens.push({ t, id: u.id_pengguna, jenis: "reset" }); save(db); r.tautan_dev = "/reset-sandi?token=" + t; }
    return r;
  },
  async reset(token, password) {
    await delay(); if (password.length < 8) fail("Kata sandi minimal 8 karakter.");
    const db = load(), k = (db.tokens || []).find((x) => x.t === token && x.jenis === "reset"); if (!k) fail("Tautan atur ulang kata sandi tidak valid atau sudah dipakai.");
    const u = db.pengguna.find((x) => x.id_pengguna === k.id); u.password = password; u.email_terverifikasi = true; db.tokens = db.tokens.filter((x) => x !== k); save(db);
    return { pesan: "Kata sandi berhasil diubah. Silakan masuk dengan kata sandi baru." };
  },
  async hapusPengguna(id) {
    await delay(); const db = load(), u = me(); if (id === u.id_pengguna) fail("Anda tidak dapat menghapus akun Anda sendiri.");
    if (db.sampel.some((s) => s.id_pengguna === id) || db.analisis.some((a) => a.id_pengguna === id) || id <= 3) fail("Akun sudah memiliki data atau riwayat akses sehingga tidak dapat dihapus. Nonaktifkan akun sebagai gantinya.");
    db.pengguna = db.pengguna.filter((x) => x.id_pengguna !== id); save(db);
  },
  async buatSampel(meta, files, onProgress) {
    const db = load(), u = me();
    for (let p = 0; p <= 100; p += 20) { onProgress?.(p); await delay(120); }
    const s = { id_sampel: ++db.seq.sampel, id_pengguna: u.id_pengguna, nama_sampel: meta.nama_sampel, lokasi: meta.lokasi, strain: meta.strain, karakteristik: meta.karakteristik,
      tipe_baca: files.length === 2 ? "paired-end" : "single-end", lokasi_fastq_r1: "mock://" + files[0].name, lokasi_fastq_r2: files[1] ? "mock://" + files[1].name : null, dibuat_pada: iso() };
    const gen = db.referensi.find((r) => r.jenis === "genom" && r.status === "bawaan");
    const a = { id_analisis: ++db.seq.analisis, id_pengguna: u.id_pengguna, id_sampel: s.id_sampel, id_referensi: gen?.id_referensi ?? null, id_referensi_anotasi: null, tanggal: iso(), status: "draf",
      parameter: { ...PARAM_DEFAULT }, tahap_saat_ini: null, progres_persen: 0, log_kesalahan: null, keterangan: null, terkunci: false, dipublikasikan: false };
    db.sampel.push(s); db.analisis.push(a); save(db); return full(db, a);
  },
  async listReferensi(jenis) { await delay(80); return load().referensi.filter((r) => !jenis || r.jenis === jenis); },
  async unggahReferensi({ nama_referensi, jenis, file }) {
    await delay(400); const db = load(), u = me();
    if (!/\.(fa|fasta|fa\.gz|fasta\.gz)$/i.test(file.name) && jenis === "genom") fail("Referensi genom harus berformat FASTA (.fa/.fasta).");
    if (jenis === "anotasi" && !/\.(vcf|vcf\.gz|gtf|gff|gff3|gtf\.gz|gff3\.gz)$/i.test(file.name)) fail("Berkas anotasi tidak dikenali (.vcf/.gtf/.gff).");
    const r = { id_referensi: ++db.seq.referensi, nama_referensi: nama_referensi || file.name, status: "unggahan", jenis, id_pengunggah: u.id_pengguna, dibuat_pada: iso() };
    db.referensi.push(r); save(db); return r;
  },
  async hapusReferensi(id) {
    await delay(); const db = load();
    if (db.analisis.some((a) => a.id_referensi === id || a.id_referensi_anotasi === id)) fail("Referensi masih dipakai oleh analisis dan tidak dapat dihapus.");
    db.referensi = db.referensi.filter((r) => r.id_referensi !== id); save(db);
  },
  async listAnalisis() { await delay(80); const db = load(), u = me(); return db.analisis.filter((a) => a.id_pengguna === u.id_pengguna).map((a) => full(db, tick(db, a))).sort((x, y) => y.id_analisis - x.id_analisis); },
  async getAnalisis(id) { await delay(60); const db = load(); return full(db, own(db, id)); },
  async simpanKonfigurasi(id, body) {
    await delay(); const db = load(), a = own(db, id);
    if (a.terkunci || a.status !== "draf") fail("Analisis yang sudah dijalankan tidak dapat diubah. Jalankan sebagai analisis baru."); // BR-05
    Object.assign(a, body); save(db); return full(db, a);
  },
  async jalankan(id) {
    await delay(); const db = load(), a = own(db, id);
    if (a.status !== "draf") fail("Analisis sudah pernah dijalankan.");
    if (!a.id_referensi) fail("Genom referensi belum ditentukan."); // BR-01
    const s = db.sampel.find((x) => x.id_sampel === a.id_sampel);
    a.status = "menunggu"; a.mulai_ms = now(); a.fail_stage = /gagal/i.test(s?.nama_sampel || "") ? "alignment" : null; save(db); return full(db, a);
  },
  async getLog(id) { await delay(60); const db = load(), a = own(db, id); return a.mulai_ms ? logFor(a, db.sampel.find((s) => s.id_sampel === a.id_sampel)) : []; },
  async salinAnalisis(id) {
    await delay(); const db = load(), a = own(db, id), u = me();
    const n = { id_analisis: ++db.seq.analisis, id_pengguna: u.id_pengguna, id_sampel: a.id_sampel, id_referensi: a.id_referensi, id_referensi_anotasi: a.id_referensi_anotasi, tanggal: iso(), status: "draf",
      parameter: { ...a.parameter }, tahap_saat_ini: null, progres_persen: 0, log_kesalahan: null, keterangan: null, terkunci: false, dipublikasikan: false };
    db.analisis.push(n); save(db); return full(db, n);
  },
  async ringkasan(id) {
    await delay(80); const db = load(); own(db, id); const v = db.varian.filter((x) => x.id_analisis === Number(id));
    const ti = v.filter((x) => ["AG", "GA", "CT", "TC"].includes(x.ref + x.alt)).length, tv = v.length - ti;
    return { total_varian: v.length, ti_tv: tv ? +(ti / tv).toFixed(2) : null, qual_rata2: v.length ? +(v.reduce((s, x) => s + x.quality_score, 0) / v.length).toFixed(1) : null };
  },
  async varianAnalisis(id, page = 1, size = 10) { await delay(80); const db = load(); own(db, id); return pageOf(db.varian.filter((x) => x.id_analisis === Number(id)), page, size); },
  async kunci(id) { await delay(); const db = load(), a = own(db, id); if (a.status !== "selesai") fail("Hanya analisis selesai yang dapat dikunci."); a.terkunci = true; save(db); return full(db, a); },
  async publikasi(id) { await delay(); const db = load(), a = own(db, id); if (a.status !== "selesai") fail("Analisis gagal atau belum selesai tidak dapat dipublikasikan."); a.dipublikasikan = true; save(db); return full(db, a); }, // BR-06
  async unduh(id, format) {
    await delay(150); const db = load(); own(db, id); const v = db.varian.filter((x) => x.id_analisis === Number(id));
    if (format === "csv") return { filename: `analisis-${id}.csv`, blob: new Blob(["kromosom,posisi,ref,alt,qual,gen\n" + v.map((x) => [x.kromosom, x.posisi, x.ref, x.alt, x.quality_score, x.gen || ""].join(",")).join("\n")], { type: "text/csv" }) };
    return { filename: `analisis-${id}.vcf`, blob: new Blob(["##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n" + v.map((x) => [x.kromosom, x.posisi, ".", x.ref, x.alt, x.quality_score, "PASS", x.gen ? "GENE=" + x.gen : "."].join("\t")).join("\n")], { type: "text/vcf" }) };
  },
  async cariVarian({ q = "", kromosom = "", qual_min = "", page = 1, size = 10 }) {
    await delay(150); const db = load(); me();
    const ok = db.varian.filter((v) => { const a = db.analisis.find((x) => x.id_analisis === v.id_analisis); return a?.dipublikasikan; });
    const qq = q.trim().toLowerCase(); let m = qq.match(/^(chr\w+):(\d+)$/);
    const rows = ok.filter((v) => {
      const a = db.analisis.find((x) => x.id_analisis === v.id_analisis), s = db.sampel.find((x) => x.id_sampel === a.id_sampel);
      const code = `samp-${new Date(s.dibuat_pada).getFullYear()}-${String(s.id_sampel).padStart(3, "0")}`;
      const hit = !qq || (m ? v.kromosom === m[1] && v.posisi === Number(m[2]) : [v.gen || "", code, String(v.posisi), s.nama_sampel].some((t) => t.toLowerCase().includes(qq)));
      return hit && (!kromosom || v.kromosom === kromosom) && (qual_min === "" || v.quality_score >= Number(qual_min));
    }).map((v) => { const a = db.analisis.find((x) => x.id_analisis === v.id_analisis), s = db.sampel.find((x) => x.id_sampel === a.id_sampel), u = db.pengguna.find((x) => x.id_pengguna === a.id_pengguna);
      return { id_varian: v.id_varian, id_analisis: v.id_analisis, id_sampel: s.id_sampel, sampel_dibuat: s.dibuat_pada, nama_sampel: s.nama_sampel, kromosom: v.kromosom, posisi: v.posisi, ref: v.ref, alt: v.alt, quality_score: v.quality_score, gen: v.gen, pengunggah: u?.nama || "-" }; });
    return pageOf(rows, page, size);
  },
  async detailVarian(id) {
    await delay(100); const db = load(), v = db.varian.find((x) => x.id_varian === id); if (!v) fail("Data varian tidak dapat diakses.");
    const a = db.analisis.find((x) => x.id_analisis === v.id_analisis); if (!a?.dipublikasikan) fail("Anda tidak memiliki hak akses ke varian ini.");
    const s = db.sampel.find((x) => x.id_sampel === a.id_sampel), u = db.pengguna.find((x) => x.id_pengguna === a.id_pengguna);
    return { ...v, sampel: s, pengunggah: u?.nama, tanggal_analisis: a.tanggal, parameter: a.parameter };
  },
  async listPengguna() { await delay(80); me(); return load().pengguna.map(pub); },
  async simpanPengguna(id, b) {
    await delay(); const db = load();
    if (db.pengguna.some((u) => u.email.toLowerCase() === b.email.toLowerCase() && u.id_pengguna !== id)) fail("Email sudah terdaftar.");
    if (id) { Object.assign(db.pengguna.find((u) => u.id_pengguna === id), { nama: b.nama, email: b.email, peran: b.peran, aktif: b.aktif, ...(b.password ? { password: b.password } : {}) }); }
    else db.pengguna.push({ id_pengguna: ++db.seq.pengguna, nama: b.nama, email: b.email, password: b.password, peran: b.peran, aktif: true, email_terverifikasi: true, dibuat_pada: iso() });
    save(db);
  },
  reset() { localStorage.removeItem(KEY); },
};
