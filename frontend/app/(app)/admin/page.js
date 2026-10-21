"use client";
import { useEffect, useRef, useState } from "react";
import { svc } from "../../../lib/api";
import { PERAN_LABEL } from "../../../lib/constants";
import { Alert, Badge, Card, Field, Modal } from "../../../components/ui";

const EMPTY = { nama: "", email: "", password: "", peran: "peneliti", aktif: true };
export default function Admin() {
  const [users, setUsers] = useState([]); const [refs, setRefs] = useState([]); const [msg, setMsg] = useState({ t: "", m: "" });
  const [uf, setUf] = useState(null); const [rf, setRf] = useState(null); const [del, setDel] = useState(null);
  const [errs, setErrs] = useState({}); const file = useRef();

  const load = async () => { try { setUsers(await svc.listPengguna()); setRefs(await svc.listReferensi()); } catch (e) { setMsg({ t: "err", m: e.message }); } };
  useEffect(() => { load(); }, []);

  async function saveUser() {
    const e = {};
    if (!uf.nama.trim()) e.nama = "Nama wajib diisi.";
    if (!/^\S+@\S+\.\S+$/.test(uf.email)) e.email = "Format email tidak valid.";
    if (!uf.id_pengguna && uf.password.length < 8) e.password = "Kata sandi minimal 8 karakter.";
    setErrs(e); if (Object.keys(e).length) return;
    try { await svc.simpanPengguna(uf.id_pengguna || null, uf); setUf(null); setMsg({ t: "ok", m: "Akun tersimpan." }); load(); } catch (x) { setErrs({ form: x.message }); }
  }
  async function saveRef() {
    const e = {}; const f = file.current?.files[0];
    if (!f) e.file = "Pilih berkas referensi."; setErrs(e); if (Object.keys(e).length) return;
    try { await svc.unggahReferensi({ nama_referensi: rf.nama || f.name, jenis: rf.jenis, file: f }); setRf(null); setMsg({ t: "ok", m: "Referensi baru ditambahkan." }); load(); } catch (x) { setErrs({ form: x.message }); }
  }
  async function hapus() {
    try { await svc.hapusReferensi(del.id_referensi); setMsg({ t: "ok", m: `"${del.nama_referensi}" dihapus.` }); } catch (x) { setMsg({ t: "err", m: x.message }); } // data lama dipertahankan jika gagal
    setDel(null); load();
  }

  return (
    <>
      <Alert type={msg.t}>{msg.m}</Alert>
      <Card title="Manajemen Akun Pengguna" right={<button className="btn pri sm" onClick={() => { setErrs({}); setUf({ ...EMPTY }); }}>+ Tambah Akun</button>}>
        <div className="tw"><table>
          <thead><tr><th>NAMA LENGKAP</th><th>EMAIL</th><th>PERAN</th><th>STATUS</th><th>AKSI</th></tr></thead>
          <tbody>{users.map((u) => (
            <tr key={u.id_pengguna}><td><b>{u.nama}</b></td><td className="mut">{u.email}</td><td><Badge>{u.peran === "administrator" ? "Admin" : "Peneliti"}</Badge></td>
              <td>{u.aktif ? <Badge tone="green">Aktif</Badge> : <Badge tone="gray">Nonaktif</Badge>}</td>
              <td><button className="btn sm" onClick={() => { setErrs({}); setUf({ ...u, password: "" }); }}>Edit</button></td></tr>))}</tbody>
        </table></div>
      </Card>
      <Card title="Manajemen Data Referensi Sistem" dot="ind" right={<button className="btn pri sm" onClick={() => { setErrs({}); setRf({ nama: "", jenis: "genom" }); }}>↑ Unggah Referensi Baru</button>}>
        <div className="tw"><table>
          <thead><tr><th>NAMA BERKAS</th><th>JENIS REFERENSI</th><th>STATUS</th><th>AKSI</th></tr></thead>
          <tbody>{refs.map((r) => (
            <tr key={r.id_referensi}><td><b>{r.nama_referensi}</b></td><td className="mut">{r.jenis === "genom" ? "Genom Referensi" : "Basis Data Anotasi"}</td>
              <td><Badge>{r.status === "bawaan" ? "Bawaan Sistem" : "Unggahan"}</Badge></td>
              <td><button className="btn sm danger" onClick={() => setDel(r)}>Hapus</button></td></tr>))}</tbody>
        </table></div>
      </Card>

      {uf && (
        <Modal title={uf.id_pengguna ? "Edit Akun" : "Tambah Akun"} onClose={() => setUf(null)}>
          <Alert type="err">{errs.form}</Alert>
          <Field label="Nama lengkap" error={errs.nama}><input value={uf.nama} onChange={(e) => setUf({ ...uf, nama: e.target.value })} /></Field>
          <Field label="Email" error={errs.email}><input type="email" value={uf.email} onChange={(e) => setUf({ ...uf, email: e.target.value })} /></Field>
          <Field label="Kata sandi" hint={uf.id_pengguna ? "Kosongkan jika tidak diubah." : "Minimal 8 karakter."} error={errs.password}><input type="password" value={uf.password} onChange={(e) => setUf({ ...uf, password: e.target.value })} /></Field>
          <Field label="Peran"><select value={uf.peran} onChange={(e) => setUf({ ...uf, peran: e.target.value })}>{Object.entries(PERAN_LABEL).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
          {uf.id_pengguna && <label className="f" style={{ gridAutoFlow: "column", justifyContent: "start", alignItems: "center" }}><input type="checkbox" style={{ width: "auto" }} checked={uf.aktif} onChange={(e) => setUf({ ...uf, aktif: e.target.checked })} />Akun aktif</label>}
          <div className="actions"><button className="btn" onClick={() => setUf(null)}>Batal</button><button className="btn pri" onClick={saveUser}>Simpan</button></div>
        </Modal>
      )}
      {rf && (
        <Modal title="Unggah Referensi Baru" onClose={() => setRf(null)}>
          <Alert type="err">{errs.form}</Alert>
          <Field label="Jenis referensi"><select value={rf.jenis} onChange={(e) => setRf({ ...rf, jenis: e.target.value })}><option value="genom">Genom Referensi (FASTA)</option><option value="anotasi">Basis Data Anotasi</option></select></Field>
          <Field label="Nama tampilan" hint="Opsional. Default: nama berkas."><input value={rf.nama} onChange={(e) => setRf({ ...rf, nama: e.target.value })} /></Field>
          <Field label="Berkas" error={errs.file}><input type="file" ref={file} /></Field>
          <div className="actions"><button className="btn" onClick={() => setRf(null)}>Batal</button><button className="btn pri" onClick={saveRef}>Unggah</button></div>
        </Modal>
      )}
      {del && (
        <Modal title="Hapus referensi?" onClose={() => setDel(null)}>
          <p>Hapus <b>{del.nama_referensi}</b>{del.status === "bawaan" ? " (referensi bawaan sistem)" : ""}? Referensi yang masih dipakai analisis tidak dapat dihapus.</p>
          <div className="actions"><button className="btn" onClick={() => setDel(null)}>Batal</button><button className="btn pri" style={{ background: "#e11d48" }} onClick={hapus}>Hapus</button></div>
        </Modal>
      )}
    </>
  );
}
