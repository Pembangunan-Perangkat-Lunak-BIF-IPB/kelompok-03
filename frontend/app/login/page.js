"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { svc, USE_MOCK } from "../../lib/api";
import { setSession } from "../../lib/session";
import { Alert, Field, FlaskIcon } from "../../components/ui";

export default function Masuk() {
  const r = useRouter();
  const [f, setF] = useState({ email: "", password: "" });
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault(); setErr("");
    if (!f.email || !f.password) return setErr("Email dan kata sandi wajib diisi.");
    setBusy(true);
    try { const d = await svc.login(f.email, f.password); setSession(d.token, d.pengguna); r.replace(d.pengguna.peran === "administrator" ? "/admin" : "/unggah"); }
    catch (x) { setErr(x.message); } finally { setBusy(false); }
  }
  return (
    <div className="login">
      <form className="card" onSubmit={submit}>
        <div className="logo"><i><FlaskIcon /></i>Human GVC</div>
        <Alert type="err">{err}</Alert>
        <Field label="Email"><input type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} placeholder="nama@ipb.ac.id" autoFocus /></Field>
        <Field label="Kata sandi"><input type="password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
        <button className="btn pri" style={{ width: "100%" }} disabled={busy}>{busy ? "Memeriksa..." : "Masuk"}</button>
        {USE_MOCK && <p className="hint">Mode data tiruan. Peneliti: peneliti@ipb.ac.id / Peneliti#123. Admin: rakahendrawan@ipb.ac.id / Admin#123.</p>}
      </form>
    </div>
  );
}
