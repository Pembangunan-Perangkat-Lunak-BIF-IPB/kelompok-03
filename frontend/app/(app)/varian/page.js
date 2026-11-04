"use client";
import { useEffect, useState } from "react";
import { svc } from "../../../lib/api";
import { sampelCode } from "../../../lib/constants";
import { Alert, Card, Modal } from "../../../components/ui";

const SIZE = 10, CHR = ["", ...Array.from({ length: 22 }, (_, i) => `chr${i + 1}`), "chrX", "chrY"];
const code = (v) => sampelCode(v.id_sampel, v.sampel_dibuat);

export default function Varian() {
  const [q, setQ] = useState(""); const [chr, setChr] = useState(""); const [qual, setQual] = useState(""); const [showQ, setShowQ] = useState(false);
  const [applied, setApplied] = useState({}); const [page, setPage] = useState(1);
  const [data, setData] = useState(null); const [err, setErr] = useState(""); const [det, setDet] = useState(null);

  useEffect(() => {
    let live = true; setErr("");
    svc.cariVarian({ ...applied, page, size: SIZE }).then((d) => live && setData(d)).catch((e) => live && setErr(e.message));
    return () => { live = false; };
  }, [applied, page]);

  function cari(next = {}) {
    const f = { q, kromosom: chr, qual_min: qual, ...next };
    if (/^chr\w+:/i.test(f.q.trim()) && !/^chr\w+:\d+$/i.test(f.q.trim())) return setErr("Format posisi tidak valid. Gunakan chr17:41196312."); // UC-06 alt 1
    if (f.qual_min !== "" && (Number.isNaN(Number(f.qual_min)) || Number(f.qual_min) < 0)) return setErr("Nilai QUAL minimum harus angka 0 atau lebih.");
    setPage(1); setApplied(f);
  }
  async function open(v) { try { setDet(await svc.detailVarian(v.id_varian)); } catch (x) { setErr(x.message); } }
  const total = data?.total || 0, pages = Math.max(1, Math.ceil(total / SIZE));

  return (
    <>
      <Alert type="err">{err}</Alert>
      <Card>
        <div className="searchrow">
          <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && cari()} placeholder="Cari ID, Gen, atau Posisi (Cth: BRCA1, chr17:41196312)" />
          <button className="btn pri" onClick={() => cari()}>Cari</button>
        </div>
        <div className="filters">
          <label>Kromosom<select value={chr} onChange={(e) => { setChr(e.target.value); cari({ kromosom: e.target.value }); }}>{CHR.map((c) => <option key={c} value={c}>{c || "Semua Kromosom"}</option>)}</select></label>
          <button className="btn" onClick={() => setShowQ(!showQ)}>Filter Kualitas (QUAL){qual !== "" ? ` ≥ ${qual}` : ""}</button>
          {showQ && <label>QUAL minimum<input type="number" min="0" value={qual} onChange={(e) => setQual(e.target.value)} onBlur={() => cari()} placeholder="mis. 50" /></label>}
          {(applied.q || applied.kromosom || applied.qual_min) && <button className="btn sm" onClick={() => { setQ(""); setChr(""); setQual(""); setErr(""); setApplied({}); setPage(1); }}>Reset filter</button>}
        </div>
      </Card>
      <Card>
        <div className="tw"><table>
          <thead><tr><th>ID ANALISIS / SAMPEL</th><th>KROMOSOM</th><th>POSISI</th><th>MUTASI (REF&gt;ALT)</th><th>QUAL</th><th>PENGUNGGAH</th></tr></thead>
          <tbody>
            {data?.items.map((v) => (
              <tr key={v.id_varian} className="click" onClick={() => open(v)}>
                <td><a href="#" onClick={(e) => e.preventDefault()}><b>{code(v)}</b></a></td><td><b>{v.kromosom}</b></td><td className="mut">{v.posisi}</td>
                <td><span className="code">{v.ref} &gt; {v.alt}</span></td><td>{v.quality_score}</td><td>{v.pengunggah}</td>
              </tr>
            ))}
            {data && !data.items.length && <tr><td colSpan="6" className="empty">Tidak ada varian yang sesuai dengan kriteria pencarian.</td></tr>}
            {!data && !err && <tr><td colSpan="6" className="empty">Memuat...</td></tr>}
          </tbody>
        </table></div>
        <div className="pager"><span>Menampilkan {total ? (page - 1) * SIZE + 1 : 0}-{Math.min(page * SIZE, total)} dari {total} varian</span>
          <span style={{ display: "flex", gap: ".5rem" }}><button className="btn sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Prev</button><button className="btn sm" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</button></span></div>
      </Card>
      {det && (
        <Modal title={`Detail Varian · ${sampelCode(det.sampel.id_sampel, det.sampel.dibuat_pada)}`} onClose={() => setDet(null)}>
          <dl className="kv">
            <dt>Lokus</dt><dd>{det.kromosom}:{det.posisi}</dd><dt>Mutasi</dt><dd>{det.ref} &gt; {det.alt}</dd><dt>QUAL</dt><dd>{det.quality_score}</dd>
            <dt>Gen</dt><dd>{det.gen || "- (tidak teranotasi)"}</dd>
            <dt>Genotipe</dt><dd>{det.genotipe?.genotipe}</dd><dt>Kedalaman</dt><dd>{det.genotipe?.kedalaman}</dd><dt>Kualitas genotipe</dt><dd>{det.genotipe?.kualitas_genotipe}</dd>
            <dt>Sampel</dt><dd>{det.sampel.nama_sampel}</dd><dt>Lokasi</dt><dd>{det.sampel.lokasi}</dd><dt>Karakteristik</dt><dd>{det.sampel.karakteristik}</dd><dt>Strain</dt><dd>{det.sampel.strain}</dd>
            <dt>Pengunggah</dt><dd>{det.pengunggah}</dd><dt>ID analisis</dt><dd>#{det.id_analisis}</dd>
          </dl>
          <div className="actions" style={{ marginTop: "1rem" }}><button className="btn" onClick={() => setDet(null)}>Tutup</button></div>
        </Modal>
      )}
    </>
  );
}
