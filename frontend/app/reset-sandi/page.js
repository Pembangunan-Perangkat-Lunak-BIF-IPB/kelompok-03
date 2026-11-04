"use client";
import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { svc } from "../../lib/api";
import { Alert, Field } from "../../components/ui";
import AuthCard from "../../components/AuthCard";

function Isi() {
  const token = useSearchParams().get("token");
  const [f, setF] = useState({ password: "", ulang: "" }); const [errs, setErrs] = useState({}); const [err, setErr] = useState(""); const [ok, setOk] = useState(""); const [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault(); setErr("");
    const v = {};
    if (f.password.length < 8) v.password = "Kata sandi minimal 8 karakter.";
    if (f.ulang !== f.password) v.ulang = "Konfirmasi kata sandi tidak sama.";
    setErrs(v); if (Object.keys(v).length) return;
    setBusy(true);
    try { setOk((await svc.reset(token, f.password)).pesan); } catch (x) { setErr(x.message); } finally { setBusy(false); }
  }
  if (!token) return <AuthCard title="Atur ulang kata sandi"><Alert type="err">Tautan tidak lengkap. Minta tautan baru.</Alert><div className="alt"><Link href="/lupa-sandi"><b>Minta tautan baru</b></Link></div></AuthCard>;
  if (ok) return <AuthCard title="Atur ulang kata sandi"><Alert type="ok">{ok}</Alert><div className="alt"><Link href="/login"><b>Ke halaman masuk</b></Link></div></AuthCard>;
  return (
    <AuthCard title="Atur ulang kata sandi" onSubmit={submit}>
      <Alert type="err">{err}</Alert>
      <Field label="Kata sandi baru" hint="Minimal 8 karakter." error={errs.password}><input type="password" className={errs.password ? "err" : ""} value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} autoFocus /></Field>
      <Field label="Ulangi kata sandi baru" error={errs.ulang}><input type="password" className={errs.ulang ? "err" : ""} value={f.ulang} onChange={(e) => setF({ ...f, ulang: e.target.value })} /></Field>
      <button className="btn pri" style={{ width: "100%" }} disabled={busy}>{busy ? "Menyimpan..." : "Simpan kata sandi"}</button>
      <div className="alt">{err.includes("tidak valid") || err.includes("kedaluwarsa") ? <Link href="/lupa-sandi"><b>Minta tautan baru</b></Link> : null}</div>
    </AuthCard>
  );
}
export default function Reset() { return <Suspense fallback={null}><Isi /></Suspense>; }
