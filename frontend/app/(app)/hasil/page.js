"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { svc, saveBlob } from "../../../lib/api";
import { useAnalisis } from "../../../lib/hooks";
import { setActive } from "../../../lib/session";
import { Alert, Badge, Card, StatusBadge } from "../../../components/ui";
import NoActive from "../../../components/NoActive";

const SIZE = 10;
export default function Hasil() {
  const r = useRouter(); const { a, setA, error, loading } = useAnalisis(3000);
  const [sum, setSum] = useState(null); const [page, setPage] = useState(1); const [rows, setRows] = useState(null);
  const [msg, setMsg] = useState({ t: "", m: "" }); const [busy, setBusy] = useState("");
  const done = a?.status === "selesai";

  useEffect(() => { if (done) svc.ringkasan(a.id_analisis).then(setSum).catch((e) => setMsg({ t: "err", m: e.message })); }, [done, a?.id_analisis]);
  useEffect(() => { if (done) svc.varianAnalisis(a.id_analisis, page, SIZE).then(setRows).catch((e) => setMsg({ t: "err", m: e.message })); }, [done, a?.id_analisis, page]);

  if (loading) return <p className="mut">Memuat...</p>;
  if (!a) return <NoActive error={error} />;
  if (!done) return ( // UC-05 alt 1 & 2: tidak ada hasil akhir jika belum selesai / gagal
    <Card><div className="empty">
      <p>Hasil belum tersedia. Status analisis #{a.id_analisis}: <StatusBadge status={a.status} /></p>
      <Link className="btn pri" href={a.status === "draf" ? "/eksekusi" : "/status"}>{a.status === "draf" ? "Ke Eksekusi Analisis" : "Lihat Status & Log"}</Link>
    </div></Card>
  );

  async function act(name, fn, okMsg) {
    setBusy(name); setMsg({ t: "", m: "" });
    try { const n = await fn(); if (n?.id_analisis) setA(n); setMsg({ t: "ok", m: okMsg }); } catch (x) { setMsg({ t: "err", m: x.message }); } finally { setBusy(""); }
  }
  const dl = (f) => act(f, async () => saveBlob(await svc.unduh(a.id_analisis, f)), `Berkas ${f.toUpperCase()} diunduh.`);
  const total = rows?.total || 0, pages = Math.max(1, Math.ceil(total / SIZE));

  return (
    <>
      <Alert type={msg.t}>{msg.m}</Alert>
      <div style={{ display: "flex", gap: ".6rem", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap" }}>
        <b>Analisis #{a.id_analisis} · {a.sampel?.nama_sampel}</b>
        {a.terkunci && <Badge tone="indigo">Terkunci</Badge>}{a.dipublikasikan && <Badge tone="green">Dipublikasikan</Badge>}
        {a.keterangan && <Badge tone="amber">{a.keterangan}</Badge>}
      </div>
      <div className="stats">
        <div className="stat"><small>TOTAL VARIAN DITEMUKAN</small><b>{sum ? sum.total_varian.toLocaleString("en-US") : "…"}</b></div>
        <div className="stat"><small>TRANSISI / TRANSVERSI (TI/TV)</small><b>{sum ? sum.ti_tv ?? "-" : "…"}</b></div>
        <div className="stat"><small>KUALITAS RATA-RATA (QUAL)</small><b>{sum ? sum.qual_rata2 ?? "-" : "…"}</b></div>
      </div>
      <Card>
        <h2 style={{ border: 0, paddingBottom: 0 }}>Tabel Kandidat Varian</h2>
        <div className="tw"><table>
          <thead><tr><th>KROMOSOM</th><th>POSISI</th><th>REF</th><th>ALT</th><th>QUAL</th>{a.id_referensi_anotasi && <th>GEN</th>}</tr></thead>
          <tbody>
            {rows?.items.map((v) => (
              <tr key={v.id_varian}><td><b>{v.kromosom}</b></td><td className="mut">{v.posisi}</td><td><span className="code">{v.ref}</span></td><td><span className="code alt">{v.alt}</span></td><td><b>{v.quality_score}</b></td>{a.id_referensi_anotasi && <td>{v.gen || "-"}</td>}</tr>
            ))}
            {rows && !rows.items.length && <tr><td colSpan="6" className="empty">Tidak ada varian yang lolos filter.</td></tr>}
          </tbody>
        </table></div>
        <div className="pager"><span>Menampilkan {total ? (page - 1) * SIZE + 1 : 0}-{Math.min(page * SIZE, total)} dari {total} varian</span>
          <span style={{ display: "flex", gap: ".5rem" }}><button className="btn sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Prev</button><button className="btn sm" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</button></span></div>
      </Card>
      <div className="actions">
        {a.terkunci && <button className="btn" onClick={async () => { const n = await svc.salinAnalisis(a.id_analisis); setActive(n.id_analisis); r.push("/pengaturan"); }}>Jalankan ulang sebagai analisis baru</button>}
        {!a.terkunci && <button className="btn" disabled={!!busy} onClick={() => act("kunci", () => svc.kunci(a.id_analisis), "Hasil dan parameter dikunci. Perubahan hanya lewat analisis baru.")}>Kunci Hasil</button>}
        {!a.dipublikasikan && <button className="btn" disabled={!!busy} onClick={() => act("pub", () => svc.publikasi(a.id_analisis), "Varian dipublikasikan ke Database Varian bersama.")}>Publikasikan ke Database Varian</button>}
        <button className="btn" disabled={!!busy} onClick={() => dl("csv")}>Unduh CSV</button>
        <button className="btn dark" disabled={!!busy} onClick={() => dl("vcf")}>Unduh VCF Akhir</button>
      </div>
    </>
  );
}
