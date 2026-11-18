"use client";
import { useState } from "react";
import Link from "next/link";
import { svc } from "../../lib/api";
import { Alert, Field } from "../../components/ui";
import AuthCard from "../../components/AuthCard";

export default function Daftar() {
  const [f, setF] = useState({ nama: "", email: "", password: "", ulang: "" });
  const [errs, setErrs] = useState({}); const [err, setErr] = useState(""); const [ok, setOk] = useState(null); const [busy, setBusy] = useState(false);
  const set = (k) => (e) => { setF({ ...f, [k]: e.target.value }); setErrs((p) => ({ ...p, [k]: undefined })); };

  async function submit(e) {
    e.preventDefault(); setErr("");
    const v = {};
    if (!f.nama.trim()) v.nama = "Nama wajib diisi.";
    if (!/^\S+@\S+\.\S+$/.test(f.email.trim())) v.email = "Format email tidak valid.";
    if (f.password.length < 8) v.password = "Kata sandi minimal 8 karakter.";
    if (f.ulang !== f.password) v.ulang = "Konfirmasi kata sandi tidak sama.";
    setErrs(v); if (Object.keys(v).length) return;
    setBusy(true);
    try { setOk(await svc.daftar(f.nama.trim(), f.email.trim(), f.password)); } catch (x) { setErr(x.message); } finally { setBusy(false); }
  }
  if (ok) return (
    <AuthCard title="Periksa email Anda">
      <Alert type="ok">{ok.pesan}</Alert>
      {ok.tautan_dev && <Alert type="info">Mode tiruan: <Link href={ok.tautan_dev}>buka tautan verifikasi</Link></Alert>}
      <p className="hint">Tidak menemukan email? Periksa folder spam, lalu gunakan "Kirim ulang email verifikasi" di halaman masuk.</p>
      <div className="alt"><Link href="/login"><b>Ke halaman masuk</b></Link></div>
    </AuthCard>
  );
  return (
    <AuthCard title="Daftar akun" sub="Akun peneliti. Email akan diverifikasi sebelum akun dapat dipakai." onSubmit={submit}>
      <Alert type="err">{err}</Alert>
      <Field label="Nama lengkap" error={errs.nama}><input className={errs.nama ? "err" : ""} value={f.nama} onChange={set("nama")} autoFocus /></Field>
      <Field label="Email" error={errs.email}><input type="email" className={errs.email ? "err" : ""} value={f.email} onChange={set("email")} placeholder="nama@email.com" /></Field>
      <Field label="Kata sandi" hint="Minimal 8 karakter." error={errs.password}><input type="password" className={errs.password ? "err" : ""} value={f.password} onChange={set("password")} /></Field>
      <Field label="Ulangi kata sandi" error={errs.ulang}><input type="password" className={errs.ulang ? "err" : ""} value={f.ulang} onChange={set("ulang")} /></Field>
      <button className="btn pri" style={{ width: "100%" }} disabled={busy}>{busy ? "Mendaftarkan..." : "Daftar"}</button>
      <div className="alt"><span>Sudah punya akun? <Link href="/login"><b>Masuk</b></Link></span></div>
    </AuthCard>
  );
}
