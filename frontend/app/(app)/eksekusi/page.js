"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { svc } from "../../../lib/api";
import { useAnalisis } from "../../../lib/hooks";
import { PARAM_DEFAULT, STAGES } from "../../../lib/constants";
import { Alert, Badge, Card } from "../../../components/ui";
import NoActive from "../../../components/NoActive";

export default function Eksekusi() {
  const r = useRouter(); const { a, error, loading } = useAnalisis();
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  if (loading) return <p className="mut">Memuat...</p>;
  if (!a) return <NoActive error={error} />;

  const s = a.sampel, p = a.parameter || {};
  const isDefault = Object.keys(PARAM_DEFAULT).every((k) => Number(p[k]) === PARAM_DEFAULT[k]);
  const meta = s ? [s.lokasi, s.karakteristik, s.strain].filter((x) => x && x !== "-").join(", ") : "";
  // UC-03 alt 1: tampilkan bagian yang belum lengkap. BR-01: referensi wajib.
  const missing = [];
  if (!s) missing.push("Data sekuens FASTQ belum diunggah (menu 1).");
  else if (!s.lokasi || !s.karakteristik || !s.strain || !s.nama_sampel) missing.push("Metadata sampel belum lengkap (menu 1).");
  if (!a.id_referensi) missing.push("Genom referensi belum dipilih (menu 2).");
  const ready = !missing.length && a.status === "draf";

  async function run() {
    setBusy(true); setErr("");
    try { await svc.jalankan(a.id_analisis); r.push("/status"); } catch (x) { setErr(x.message); setBusy(false); }
  }
  const rows = [
    ["Data Masukan:", s ? `${s.tipe_baca === "paired-end" ? "2 berkas FASTQ (Paired-end)" : "1 berkas FASTQ (Single-end)"} · ${s.nama_sampel}` : "Belum ada", s ? "VALID" : "BELUM ADA", s],
    ["Metadata:", meta || "Belum lengkap", meta && s?.nama_sampel ? "LENGKAP" : "BELUM LENGKAP", meta && s?.nama_sampel],
    ["Referensi:", a.referensi ? `${a.referensi.nama_referensi}${a.referensi.status === "bawaan" ? " (Bawaan)" : ""}${a.anotasi ? ` · anotasi ${a.anotasi.nama_referensi}` : " · tanpa anotasi"}` : "Belum dipilih", a.referensi ? "TERSEDIA" : "BELUM DIPILIH", a.referensi],
    ["Parameter:", `Min Quality ${p.kualitas_pemangkasan_min} · Min Depth ${p.kedalaman_min} · Min QUAL ${p.qual_min}${isDefault ? " (Default)" : " (Diubah)"}`, "TERKONFIRMASI", true],
  ];
  return (
    <>
      <Alert type="err">{err}</Alert>
      {a.status !== "draf" && <Alert type="info">Analisis #{a.id_analisis} sudah dijalankan. <Link href="/status">Lihat Status &amp; Log</Link></Alert>}
      {missing.length > 0 && <Alert type="warn">Analisis belum dapat dijalankan:<ul>{missing.map((m) => <li key={m}>{m}</li>)}</ul></Alert>}
      <Card title="Ringkasan Konfigurasi">
        {rows.map(([k, v, b, ok]) => (
          <div className="srow" key={k}><span><b>{k}</b> {v}</span><Badge tone={ok ? "" : "red"}>{b}</Badge></div>
        ))}
        <div className="actions"><Link className="btn sm" href="/pengaturan">Ubah pengaturan</Link></div>
      </Card>
      <div className="pipe">
        <h3>Alur Pemrosesan (Pipeline)</h3>
        <div className="st">{STAGES.map((x, i) => <span key={x.key}>{x.label}{i < STAGES.length - 1 && <i> →</i>}</span>)}</div>
      </div>
      <div className="actions" style={{ justifyContent: "center" }}>
        <button className="btn pri" style={{ fontSize: "1.1rem", padding: ".9rem 2.4rem" }} disabled={!ready || busy} onClick={run}>{busy ? "Memulai..." : "Mulai Jalankan Analisis"}</button>
      </div>
    </>
  );
}
