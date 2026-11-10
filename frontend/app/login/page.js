"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { svc, USE_MOCK } from "../../lib/api";
import { setSession } from "../../lib/session";
import { Alert, Field } from "../../components/ui";
import AuthCard from "../../components/AuthCard";

export default function Masuk() {
  const r = useRouter();
  const [f, setF] = useState({ email: "", password: "" });
  const [err, setErr] = useState(""); const [info, setInfo] = useState(""); const [busy, setBusy] = useState(false);
  const [dev, setDev] = useState("");
  const belumVerif = err.includes("belum diverifikasi");

  async function submit(e) {
    e.preventDefault(); setErr(""); setInfo(""); setDev("");
    if (!f.email || !f.password) return setErr("Email dan kata sandi wajib diisi.");
    setBusy(true);
    try { const d = await svc.login(f.email, f.password); setSession(d.token, d.pengguna); r.replace(d.pengguna.peran === "administrator" ? "/admin" : "/unggah"); }
    catch (x) { setErr(x.message); } finally { setBusy(false); }
  }
  async function kirimUlang() {
    try { const d = await svc.kirimUlang(f.email); setErr(""); setInfo(d.pesan); setDev(d.tautan_dev || ""); } catch (x) { setErr(x.message); }
  }
  return (
    <div className="login-page">
      <div className="info-panel">
        <span className="badge amber">Automated Web-Based Variant Calling Platform</span>
        <h1 className="info-head">Analisis Variant Calling Genomik dalam Satu Platform</h1>
        <p className="info-subhead">Human GVC membantu Anda menjalankan pipeline variant calling dari data sekuensing hingga hasil VCF tanpa perlu mengetik perintah command line yang rumit.</p>
        <h2 className="section-title">Apa itu Human GVC?</h2>
        <p>Human GVC adalah platform berbasis web yang mengintegrasikan seluruh tahapan analisis variant calling dalam satu alur kerja terstruktur. Anda cukup mengunggah data sekuensing berformat FASTQ/FASTQ.GZ, mengatur analisis, memantau proses pipeline, dan mengakses hasil analisis langsung dari browser.</p>
        <h2 className="section-title">Alur Pipeline</h2>
        <div className="pipeline-steps">
          <div className="step"><span className="step-number">1</span> Quality Control</div>
          <div className="step"><span className="step-number">2</span> Preprocessing</div>
          <div className="step"><span className="step-number">3</span> Alignment</div>
          <div className="step"><span className="step-number">4</span> Variant Calling</div>
          <div className="step"><span className="step-number">5</span> Filtering</div>
        </div>
        <h2 className="section-title">Keunggulan</h2>
        <div className="features-grid">
          <div className="feature-card"><h3>Terintegrasi</h3><p>Input data, parameter, status proses, dan hasil akhir terkelola dalam satu sistem.</p></div>
          <div className="feature-card"><h3>Mudah Digunakan</h3><p>Antarmuka sederhana tanpa perlu memahami command line dan dependency tools.</p></div>
          <div className="feature-card"><h3>Terpantau &amp; Terdokumentasi</h3><p>Pantau progres pipeline, lihat log setiap tahap, dan akses hasil melalui result viewer.</p></div>
        </div>
        <div className="stats-row">
          <div className="stat-item"><strong>FASTQ/FASTQ.GZ</strong><span>Input data</span></div>
          <div className="stat-item"><strong>5 Tahap</strong><span>Pipeline terintegrasi</span></div>
          <div className="stat-item"><strong>VCF</strong><span>Output hasil</span></div>
          <div className="stat-item"><strong>Web‑based</strong><span>Akses dari browser</span></div>
        </div>
        <footer className="info-footer">Dikembangkan oleh Kelompok GenoSys (3) - Program Studi Bioinformatika, IPB University 2026</footer>
      </div>
      <div className="login-card">
        <AuthCard title="Masuk" onSubmit={submit}>
          <Alert type="err">{err}</Alert>
          <Alert type="ok">{info}</Alert>
          {belumVerif && <p style={{ margin: "0 0 1rem" }}><button type="button" className="linkbtn" onClick={kirimUlang}>Kirim ulang email verifikasi</button></p>}
          {dev && <Alert type="info">Mode tiruan: <Link href={dev}>buka tautan verifikasi</Link></Alert>}
          <Field label="Email"><input type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} placeholder="nama@email.com" autoFocus /></Field>
          <Field label="Kata sandi"><input type="password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
          <button className="btn pri" style={{ width: "100%" }} disabled={busy}>{busy ? "Memeriksa..." : "Masuk"}</button>
          <div className="alt"><Link href="/lupa-sandi">Lupa kata sandi?</Link><span>Belum punya akun? <Link href="/daftar"><b>Daftar</b></Link></span></div>
          {USE_MOCK && <p className="hint">Mode data tiruan. Peneliti: peneliti@ipb.ac.id / Peneliti#123. Admin: rakahendrawan@ipb.ac.id / Admin#123.</p>}
        </AuthCard>
      </div>
    </div>
  );
}
