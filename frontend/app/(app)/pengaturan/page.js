"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { svc } from "../../../lib/api";
import { useAnalisis } from "../../../lib/hooks";
import { PARAM_DEFAULT, PARAM_LABEL, PARAM_RANGE } from "../../../lib/constants";
import { Alert, Card, Field, StatusBadge } from "../../../components/ui";
import NoActive from "../../../components/NoActive";

const validate = (p) => {
  const e = {};
  Object.keys(PARAM_RANGE).forEach((k) => {
    const [lo, hi] = PARAM_RANGE[k], x = p[k];
    if (x === "" || x == null || Number.isNaN(Number(x))) e[k] = "Nilai wajib berupa angka.";
    else if (Number(x) < lo || Number(x) > hi) e[k] = `Di luar rentang yang diizinkan (${lo} sampai ${hi}).`; // BR-04
  });
  return e;
};

export default function Pengaturan() {
  const r = useRouter(); const { a, error, loading, reload } = useAnalisis();
  const [genom, setGenom] = useState([]); const [anot, setAnot] = useState([]);
  const [f, setF] = useState(null); const [errs, setErrs] = useState({}); const [msg, setMsg] = useState({ t: "", m: "" });
  const up = useRef(); const [upJenis, setUpJenis] = useState("genom");

  const loadRef = async () => { setGenom(await svc.listReferensi("genom")); setAnot(await svc.listReferensi("anotasi")); };
  useEffect(() => { loadRef().catch(() => {}); }, []);
  useEffect(() => { if (a) setF({ id_referensi: a.id_referensi || "", id_referensi_anotasi: a.id_referensi_anotasi || "", ...a.parameter }); }, [a]);

  if (loading) return <p className="mut">Memuat...</p>;
  if (!a) return <NoActive error={error} />;
  if (!f) return null;
  const ro = a.status !== "draf" || a.terkunci; // BR-05
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const body = () => ({
    id_referensi: f.id_referensi ? Number(f.id_referensi) : null,
    id_referensi_anotasi: f.id_referensi_anotasi ? Number(f.id_referensi_anotasi) : null,
    parameter: Object.fromEntries(Object.keys(PARAM_RANGE).map((k) => [k, Number(f[k])])),
  });

  async function save(confirm) {
    const e = validate(f); setErrs(e); setMsg({ t: "", m: "" });
    if (Object.keys(e).length) return setMsg({ t: "err", m: "Periksa kembali nilai parameter." });
    if (confirm && !f.id_referensi) return setMsg({ t: "err", m: "Genom referensi belum ditentukan. Analisis tidak dapat dijalankan sampai referensi dipilih." }); // UC-02 alt 3
    try {
      await svc.simpanKonfigurasi(a.id_analisis, body());
      if (confirm) r.push("/eksekusi"); else { await reload(); setMsg({ t: "ok", m: "Draf konfigurasi tersimpan." }); }
    } catch (x) { setMsg({ t: "err", m: x.message }); }
  }
  async function pickFile(e) {
    const file = e.target.files[0]; e.target.value = ""; if (!file) return;
    try { const n = await svc.unggahReferensi({ jenis: upJenis, file }); await loadRef(); setF((p) => ({ ...p, [upJenis === "genom" ? "id_referensi" : "id_referensi_anotasi"]: n.id_referensi })); setMsg({ t: "ok", m: `Referensi "${n.nama_referensi}" berhasil diunggah.` }); }
    catch (x) { setMsg({ t: "err", m: x.message }); }
  }
  const lab = (x) => `${x.nama_referensi}${x.status === "bawaan" ? " (Bawaan Sistem)" : ""}`;

  return (
    <>
      <p className="mut" style={{ marginTop: 0 }}>Analisis #{a.id_analisis} · {a.sampel?.nama_sampel} <StatusBadge status={a.status} /></p>
      {ro && <Alert type="warn">Analisis ini sudah dijalankan dan tidak dapat diubah. Untuk parameter berbeda, buat analisis baru dari menu Status &amp; Log.</Alert>}
      <Alert type={msg.t}>{msg.m}</Alert>
      <input ref={up} type="file" hidden onChange={pickFile} />
      <Card title="1. Pengaturan Referensi">
        <div className="cols2">
          <Field label="Genom Referensi (FASTA)" error={errs.ref}>
            <select disabled={ro} value={f.id_referensi} onChange={set("id_referensi")}>
              <option value="">Pilih genom referensi...</option>
              {genom.map((x) => <option key={x.id_referensi} value={x.id_referensi}>{lab(x)}</option>)}
            </select>
            {!ro && <button type="button" className="btn sm" onClick={() => { setUpJenis("genom"); up.current.click(); }}>Unggah FASTA baru</button>}
          </Field>
          <Field label="Basis Data Anotasi" hint="Opsional. Tanpa berkas anotasi, tahap anotasi dilewati.">
            <select disabled={ro} value={f.id_referensi_anotasi} onChange={set("id_referensi_anotasi")}>
              <option value="">Tanpa anotasi (tahap anotasi dilewati)</option>
              {anot.map((x) => <option key={x.id_referensi} value={x.id_referensi}>{lab(x)}</option>)}
            </select>
            {!ro && <button type="button" className="btn sm" onClick={() => { setUpJenis("anotasi"); up.current.click(); }}>Unggah anotasi baru</button>}
          </Field>
        </div>
      </Card>
      <Card title="2. Parameter Analisis" dot="ind" right={!ro && <button type="button" className="btn sm" onClick={() => { setF({ ...f, ...PARAM_DEFAULT }); setErrs({}); }}>Kembalikan default</button>}>
        <div className="cols2">
          {Object.keys(PARAM_RANGE).map((k) => (
            <Field key={k} label={PARAM_LABEL[k]} hint={`Rentang ${PARAM_RANGE[k][0]} sampai ${PARAM_RANGE[k][1]} · default ${PARAM_DEFAULT[k]}`} error={errs[k]}>
              <input type="number" disabled={ro} className={errs[k] ? "err" : ""} value={f[k]} onChange={set(k)} />
            </Field>
          ))}
        </div>
      </Card>
      <div className="actions">
        {ro ? <button className="btn pri" onClick={() => r.push(a.status === "draf" ? "/eksekusi" : "/status")}>Lanjut</button> : (<>
          <button className="btn" onClick={() => save(false)}>Simpan Draf</button>
          <button className="btn pri" onClick={() => save(true)}>Konfirmasi Parameter</button>
        </>)}
      </div>
    </>
  );
}
