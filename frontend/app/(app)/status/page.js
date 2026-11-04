"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { svc } from "../../../lib/api";
import { useAnalisis } from "../../../lib/hooks";
import { STAGES, STATUS_LABEL, fmtTime } from "../../../lib/constants";
import { Alert, Badge, Card } from "../../../components/ui";
import NoActive from "../../../components/NoActive";
import { setActive } from "../../../lib/session";

const LVL = { info: "INFO", berjalan: "PROGRESS", berhasil: "SUCCESS", error: "ERROR" };

export default function Status() {
  const r = useRouter(); const { a, error, loading } = useAnalisis(3000); // FR-07/FR-08: polling 3 dtk
  const [log, setLog] = useState([]); const [err, setErr] = useState(""); const box = useRef();
  useEffect(() => {
    if (!a) return; let live = true;
    svc.getLog(a.id_analisis).then((l) => live && setLog(l)).catch(() => {});
    return () => { live = false; };
  }, [a]);
  useEffect(() => { if (box.current) box.current.scrollTop = box.current.scrollHeight; }, [log]);

  if (loading) return <p className="mut">Memuat...</p>;
  if (!a) return <NoActive error={error} />;

  const skipAnot = !a.id_referensi_anotasi;
  const ci = STAGES.findIndex((s) => s.key === a.tahap_saat_ini);
  const state = (i, key) => {
    if (a.status === "selesai") return key === "anotasi" && skipAnot ? "Dilewati" : "Selesai";
    if (a.status === "draf" || a.status === "menunggu" || ci < 0) return "-";
    if (i < ci) return "Selesai";
    if (i === ci) return a.status === "gagal" ? "Gagal" : "Berjalan";
    return "-";
  };
  const stageName = STAGES[ci]?.label;
  const head = a.status === "berjalan" ? `Status: ${stageName} (Sedang Berjalan)` : a.status === "gagal" ? `Status: Gagal pada ${stageName || "pipeline"}` : `Status: ${STATUS_LABEL[a.status]}`;

  async function ulang() {
    try { const n = await svc.salinAnalisis(a.id_analisis); setActive(n.id_analisis); r.push("/pengaturan"); } catch (x) { setErr(x.message); }
  }
  return (
    <>
      <Alert type="err">{err}</Alert>
      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
          <b style={{ fontSize: "1.1rem" }}>● {head}</b>
          <b style={{ fontSize: "1.5rem", color: a.status === "gagal" ? "#e11d48" : "#2563eb" }}>{a.progres_persen}%</b>
        </div>
        <div className={`bar ${a.status === "gagal" ? "red" : ""}`}><b style={{ width: `${a.progres_persen}%` }} /></div>
      </Card>
      {a.status === "draf" && <Alert type="info">Analisis belum dijalankan. <Link href="/eksekusi">Buka Eksekusi Analisis</Link></Alert>}
      {a.status === "gagal" && <Alert type="err"><b>Analisis gagal.</b> {a.log_kesalahan}<div className="actions" style={{ marginTop: ".6rem" }}><button className="btn sm" onClick={ulang}>Buat analisis baru dengan konfigurasi ini</button></div></Alert>}
      {a.status === "selesai" && <Alert type="ok">Analisis selesai. {a.keterangan && <>({a.keterangan}) </>}<Link href="/hasil">Lihat Hasil Analisis</Link></Alert>}
      <div className="grid2" style={{ gridTemplateColumns: "2.2fr 1fr" }}>
        <div className="logbox" ref={box} aria-live="polite">
          {log.length === 0 && <div>{a.status === "draf" ? "Log belum tersedia." : "Menunggu log pertama..."}</div>}
          {log.map((l, i) => {
            const L = LVL[l.jenis_pesan]; const t = `[${fmtTime(l.waktu)}]`;
            return <div key={i} className={L}>{L === "INFO" ? <>{t} <b>INFO</b>: {l.pesan}</> : <>{t} {L}: {l.pesan}</>}</div>;
          })}
        </div>
        <Card>
          <p className="eyebrow">RIWAYAT TAHAPAN</p>
          {STAGES.map((s, i) => { const st = state(i, s.key); return (
            <div key={s.key} className={`stg ${st === "Berjalan" ? "on" : st === "Selesai" ? "done" : ""}`}>
              <span>{s.label}</span>{st !== "-" ? <Badge tone={st === "Gagal" ? "red" : st === "Berjalan" ? "indigo" : st === "Dilewati" ? "gray" : ""}>{st}</Badge> : <span>-</span>}
            </div>); })}
        </Card>
      </div>
    </>
  );
}
