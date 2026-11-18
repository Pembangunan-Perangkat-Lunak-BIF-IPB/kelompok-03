"use client";
import { useState } from "react";
import Link from "next/link";
import { svc } from "../../lib/api";
import { Alert, Field } from "../../components/ui";
import AuthCard from "../../components/AuthCard";

export default function Lupa() {
  const [email, setEmail] = useState(""); const [err, setErr] = useState(""); const [ok, setOk] = useState(null); const [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault(); setErr("");
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) return setErr("Format email tidak valid.");
    setBusy(true);
    try { setOk(await svc.lupa(email.trim())); } catch (x) { setErr(x.message); } finally { setBusy(false); }
  }
  return (
    <AuthCard title="Lupa kata sandi" sub="Masukkan email akun Anda. Kami akan mengirim tautan untuk mengatur ulang kata sandi." onSubmit={submit}>
      <Alert type="err">{err}</Alert><Alert type="ok">{ok?.pesan}</Alert>
      {ok?.tautan_dev && <Alert type="info">Mode tiruan: <Link href={ok.tautan_dev}>buka tautan atur ulang</Link></Alert>}
      <Field label="Email"><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoFocus /></Field>
      <button className="btn pri" style={{ width: "100%" }} disabled={busy}>{busy ? "Mengirim..." : "Kirim tautan"}</button>
      <div className="alt"><Link href="/login">Kembali ke halaman masuk</Link></div>
    </AuthCard>
  );
}
