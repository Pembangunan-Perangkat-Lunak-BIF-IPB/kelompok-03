"use client";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { svc } from "../../../lib/api";
import { setActive } from "../../../lib/session";
import { fmtSize } from "../../../lib/constants";
import { Alert, Badge, Card, CloudIcon, Field } from "../../../components/ui";

const EXT = /\.fastq(\.gz)?$/i; // UC-01 / BR-02: .fastq atau .fastq.gz
const parse = (n) => { const m = n.replace(EXT, "").match(/^(.*?)[_.-]?(?:R)?([12])$/i); return m ? { base: m[1], n: Number(m[2]) } : null; };

// Validasi sisi klien (server tetap memvalidasi ulang). Mengembalikan {files:[r1,r2?], tipe, errors[]}
function check(list) {
  const errors = [];
  const bad = list.filter((f) => !EXT.test(f.name));
  if (bad.length) errors.push(`Format tidak didukung: ${bad.map((f) => f.name).join(", ")}. Gunakan .fastq atau .fastq.gz.`);
  if (list.length > 2) errors.push("Maksimal 2 berkas (paired-end: R1 dan R2).");
  if (list.some((f) => f.size === 0)) errors.push("Terdapat berkas kosong.");
  let files = list;
  if (!errors.length && list.length === 2) {
    const [a, b] = list.map((f) => parse(f.name));
    if (!a || !b || a.base !== b.base || a.n === b.n) errors.push("Pasangan paired-end tidak cocok. Nama harus sama kecuali penanda R1/R2 (mis. sampel_R1.fastq.gz dan sampel_R2.fastq.gz).");
    else files = a.n === 1 ? list : [list[1], list[0]];
  }
  return { files, errors, tipe: list.length === 2 ? "Paired-end" : list.length === 1 ? "Single-end" : null };
}
const REQ = { nama_sampel: "Nama sampel", lokasi: "Lokasi pengambilan", karakteristik: "Karakteristik / kondisi", strain: "Strain" };

export default function Unggah() {
  const r = useRouter(), input = useRef();
  const [list, setList] = useState([]); const [over, setOver] = useState(false);
  const [meta, setMeta] = useState({ nama_sampel: "", lokasi: "", karakteristik: "", strain: "" });
  const [errs, setErrs] = useState({}); const [msg, setMsg] = useState(""); const [pct, setPct] = useState(null);
  const v = check(list);

  const add = (fl) => { setMsg(""); setList(Array.from(fl)); };
  async function submit() {
    const e = {};
    Object.entries(REQ).forEach(([k, l]) => { if (!meta[k].trim()) e[k] = `${l} wajib diisi.`; }); // UC-01 alur alt. 3
    setErrs(e);
    if (!list.length) return setMsg("Pilih berkas FASTQ terlebih dahulu.");
    if (v.errors.length || Object.keys(e).length) return setMsg(v.errors[0] || "Lengkapi metadata sampel sebelum melanjutkan.");
    setMsg(""); setPct(0);
    try {
      const a = await svc.buatSampel(Object.fromEntries(Object.entries(meta).map(([k, x]) => [k, x.trim()])), v.files, setPct);
      setActive(a.id_analisis); r.push("/pengaturan");
    } catch (x) { setMsg(x.message); setPct(null); }
  }
  const set = (k) => (e) => { setMeta({ ...meta, [k]: e.target.value }); setErrs((p) => ({ ...p, [k]: undefined })); };

  return (
    <>
      <Alert type="err">{msg}</Alert>
      <div className="grid2">
        <div className={`drop ${over ? "over" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
          onDrop={(e) => { e.preventDefault(); setOver(false); add(e.dataTransfer.files); }}>
          <div style={{ width: "100%" }}>
            <div className="ic"><CloudIcon /></div>
            <h3>Area Drag-and-Drop FASTQ</h3>
            <p>Mendukung format .fastq atau .fastq.gz<br />(Single-end &amp; Paired-end)</p>
            {list.length > 0 && (
              <div className="files">
                {list.map((f) => <div className="file" key={f.name}><span>{f.name}</span><span className="mut">{fmtSize(f.size)}</span></div>)}
                {v.tipe && !v.errors.length && <div><Badge tone="green">{v.tipe}</Badge></div>}
                {v.errors.map((x) => <div key={x} className="ferr">{x}</div>)}
              </div>
            )}
            <input ref={input} type="file" multiple hidden accept=".fastq,.gz" onChange={(e) => add(e.target.files)} />
            <button type="button" className="btn" style={{ color: "#1d4ed8" }} onClick={() => input.current.click()}>Pilih Berkas</button>
          </div>
        </div>
        <Card title="Informasi Metadata Sampel">
          <Field label="Nama Sampel" error={errs.nama_sampel}><input className={errs.nama_sampel ? "err" : ""} value={meta.nama_sampel} onChange={set("nama_sampel")} placeholder="......" /></Field>
          <Field label="Lokasi Pengambilan" error={errs.lokasi}><input className={errs.lokasi ? "err" : ""} value={meta.lokasi} onChange={set("lokasi")} placeholder="Cth: Bogor, Jawa Barat" /></Field>
          <Field label="Karakteristik / Kondisi" error={errs.karakteristik}><input className={errs.karakteristik ? "err" : ""} value={meta.karakteristik} onChange={set("karakteristik")} placeholder="Cth: Jaringan tumor, darah normal" /></Field>
          <Field label="Strain" error={errs.strain}><input className={errs.strain ? "err" : ""} value={meta.strain} onChange={set("strain")} placeholder="......" /></Field>
        </Card>
      </div>
      <div className="actions">
        {pct !== null && <span className="mut">Mengunggah {pct}%...</span>}
        <button className="btn pri" onClick={submit} disabled={pct !== null}>Simpan &amp; Lanjut</button>
      </div>
    </>
  );
}
