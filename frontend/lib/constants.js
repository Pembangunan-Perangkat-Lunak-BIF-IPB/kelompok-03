// Konstanta bersama. Sumber: SKPL (FR/UC/BR) dan database/01_schema.sql.

// Tahap pipeline = enum tahap_saat_ini / log_proses.tahap pada skema DB.
export const STAGES = [
  { key: "qc_trimming", label: "QC & Trimming" },
  { key: "alignment", label: "Alignment" },
  { key: "bam_processing", label: "Pemrosesan BAM" },
  { key: "variant_calling", label: "Variant Calling" },
  { key: "filtering", label: "Filtering" },
  { key: "anotasi", label: "Anotasi" },
];

// enum analisis.status pada DB
export const STATUS_LABEL = {
  draf: "Draf", menunggu: "Menunggu", berjalan: "Berjalan", selesai: "Selesai", gagal: "Gagal",
};
export const STATUS_TONE = {
  draf: "gray", menunggu: "amber", berjalan: "indigo", selesai: "blue", gagal: "red",
};

// default sama dengan DEFAULT kolom analisis.parameter pada DB
export const PARAM_DEFAULT = { kualitas_pemangkasan_min: 20, kedalaman_min: 10, qual_min: 30 };
// ASUMSI: SKPL (BR-04) menyebut "rentang yang diizinkan" tanpa angka. Konfirmasi ke System Analyst.
export const PARAM_RANGE = {
  kualitas_pemangkasan_min: [0, 40],
  kedalaman_min: [1, 1000],
  qual_min: [0, 1000],
};
export const PARAM_LABEL = {
  kualitas_pemangkasan_min: "Batas Kualitas Pemangkasan (Min Quality)",
  kedalaman_min: "Kedalaman Minimal (Min Depth)",
  qual_min: "Batas QUAL Filtering (Min QUAL)",
};

export const PERAN_LABEL = { peneliti: "Peneliti Biologi", administrator: "Administrator" };

export const NAV = [
  { href: "/unggah", label: "1. Unggah Data", title: "Unggah Data & Metadata" },
  { href: "/pengaturan", label: "2. Pengaturan Analisis", title: "Pengaturan Analisis" },
  { href: "/eksekusi", label: "3. Eksekusi Analisis", title: "Eksekusi Analisis" },
  { href: "/status", label: "4. Status & Log", title: "Status & Log" },
  { href: "/hasil", label: "5. Hasil Analisis", title: "Hasil Analisis" },
  { href: "/varian", label: "6. Database Varian", title: "Database Varian" },
  { href: "/admin", label: "7. Kelola Sistem (Admin)", title: "Kelola Sistem (Admin)", admin: true },
];

// Kode sampel tampilan (desain: SAMP-2026-001) diturunkan dari id_sampel + tahun dibuat.
export const sampelCode = (id, ts) =>
  `SAMP-${new Date(ts || Date.now()).getFullYear()}-${String(id).padStart(3, "0")}`;

export const fmtTime = (ts) => {
  const d = new Date(ts); const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
};
export const fmtSize = (b) => (b >= 1e9 ? (b / 1e9).toFixed(2) + " GB" : b >= 1e6 ? (b / 1e6).toFixed(1) + " MB" : Math.max(1, Math.round(b / 1e3)) + " KB");
