"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getUser } from "../lib/session";
import { FlaskIcon } from "../components/ui";
import "./landing.css";

const TAHAP = [
  ["Quality Control", "Menilai kualitas read hasil sekuensing."],
  ["Preprocessing", "Membersihkan read dari adaptor dan basa berkualitas rendah."],
  ["Alignment", "Memetakan read ke genom referensi."],
  ["Variant Calling", "Mendeteksi SNP dan indel dari hasil pemetaan."],
  ["Filtering", "Menyaring varian agar hasil akhir lebih andal."],
];

export default function Beranda() {
  const [user, setUser] = useState(null);
  useEffect(() => { setUser(getUser()); }, []);
  const tujuan = user ? (user.peran === "administrator" ? "/admin" : "/unggah") : "/login";

  return (
    <div className="lp">
      <header className="lp-nav">
        <div className="lp-brand"><i><FlaskIcon /></i>Human GVC</div>
        <nav>
          {user ? <Link href={tujuan} className="lp-btn lp-solid">Buka aplikasi</Link> : <>
            <Link href="/login" className="lp-link">Masuk</Link>
            <Link href="/daftar" className="lp-btn lp-solid">Daftar</Link>
          </>}
        </nav>
      </header>

      <section className="lp-hero">
        <div className="lp-wrap">
          <p className="lp-tag">Automated Web-Based Variant Calling Platform</p>
          <h1>Variant calling dari FASTQ hingga VCF, langsung dari browser.</h1>
          <p className="lp-lead">Human GVC menyatukan seluruh tahap analisis variant calling germline dalam satu alur kerja. Unggah data, atur parameter, pantau proses, lalu lihat hasilnya tanpa mengetik perintah command line.</p>
          <div className="lp-cta">
            <Link href={tujuan} className="lp-btn lp-light">{user ? "Buka aplikasi" : "Masuk"}</Link>
            {!user && <Link href="/daftar" className="lp-btn lp-ghost">Buat akun</Link>}
          </div>
        </div>
      </section>

      <main className="lp-wrap">
        <section className="lp-sec">
          <h2>Apa itu Human GVC?</h2>
          <p>Human GVC (Human Germline Variant Calling) adalah platform web untuk menjalankan pipeline variant calling germline. Pengguna cukup mengunggah data sekuensing berformat FASTQ atau FASTQ.GZ, baik single-end maupun paired-end, lalu menjalankan analisis dan mengunduh hasil dalam format VCF.</p>
        </section>

        <section className="lp-sec lp-note">
          <h2>Tidak terbatas pada manusia</h2>
          <p>Platform ini dirancang untuk data whole exome sequencing (WES) manusia, tetapi alurnya dapat dipakai untuk organisme lain, misalnya bakteri atau organisme model berukuran genom kecil, selama tersedia data sekuensing dan genom referensi organisme tersebut.</p>
        </section>

        <section className="lp-sec">
          <h2>Alur pipeline</h2>
          <ol className="lp-steps">
            {TAHAP.map(([nama, ket], i) => (
              <li key={nama}><span>{i + 1}</span><b>{nama}</b><p>{ket}</p></li>
            ))}
          </ol>
        </section>

        <section className="lp-sec">
          <h2>Keunggulan</h2>
          <div className="lp-grid">
            <div><h3>Terintegrasi</h3><p>Data, parameter, status proses, dan hasil akhir terkelola dalam satu sistem.</p></div>
            <div><h3>Mudah digunakan</h3><p>Tidak perlu memasang tools atau memahami command line.</p></div>
            <div><h3>Terpantau</h3><p>Progres dan log setiap tahap dapat dilihat, hasil dibuka lewat result viewer.</p></div>
          </div>
        </section>
      </main>

      <footer className="lp-foot">Kelompok GenoSys (3) · Program Studi Bioinformatika, IPB University 2026</footer>
    </div>
  );
}
