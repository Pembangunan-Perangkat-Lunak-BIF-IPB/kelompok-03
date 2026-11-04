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
    <AuthCard title="Masuk" onSubmit={submit}>
      <Alert type="err">{err}</Alert><Alert type="ok">{info}</Alert>
      {belumVerif && <p style={{ margin: "0 0 1rem" }}><button type="button" className="linkbtn" onClick={kirimUlang}>Kirim ulang email verifikasi</button></p>}
      {dev && <Alert type="info">Mode tiruan: <Link href={dev}>buka tautan verifikasi</Link></Alert>}
      <Field label="Email"><input type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} placeholder="nama@email.com" autoFocus /></Field>
      <Field label="Kata sandi"><input type="password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
      <button className="btn pri" style={{ width: "100%" }} disabled={busy}>{busy ? "Memeriksa..." : "Masuk"}</button>
      <div className="alt"><Link href="/lupa-sandi">Lupa kata sandi?</Link><span>Belum punya akun? <Link href="/daftar"><b>Daftar</b></Link></span></div>
      {USE_MOCK && <p className="hint">Mode data tiruan. Peneliti: peneliti@ipb.ac.id / Peneliti#123. Admin: rakahendrawan@ipb.ac.id / Admin#123.</p>}
    </AuthCard>
  );
}
