"use client";
import { useEffect, useState } from "react";
import { svc } from "../lib/api";
import { Card } from "./ui";

const fmt = (n) => Number(n).toLocaleString("en-US");

function BarH({ data }) { // batang horizontal: satu baris per kategori
  const maks = Math.max(1, ...data.map((d) => d.jumlah));
  return (
    <div style={{ display: "grid", gap: ".45rem" }}>
      {data.map((d) => (
        <div key={d.nama} style={{ display: "grid", gridTemplateColumns: "6.5rem 1fr 4rem", gap: ".6rem", alignItems: "center", fontSize: ".85rem" }}>
          <span className="mut" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={d.nama}>{d.nama}</span>
          <div className="bar" style={{ margin: 0 }}><b style={{ width: `${(d.jumlah / maks) * 100}%` }} /></div>
          <span style={{ textAlign: "right", fontWeight: 600 }}>{fmt(d.jumlah)}</span>
        </div>
      ))}
    </div>
  );
}

function Histogram({ qual }) { // histogram vertikal 10 kelas QUAL
  const maks = Math.max(1, ...qual.bin.map((b) => b.jumlah));
  return (
    <>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height: 150, borderBottom: "1px solid #cbd5e1" }}>
        {qual.bin.map((b) => (
          <div key={b.dari} title={`QUAL ${b.dari}–${b.sampai}: ${fmt(b.jumlah)} varian`} style={{ flex: 1, height: `${(b.jumlah / maks) * 100}%`, minHeight: b.jumlah ? 2 : 0, background: "linear-gradient(180deg,#6366f1,#3b82f6)", borderRadius: "3px 3px 0 0" }} />
        ))}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: ".78rem", marginTop: ".4rem" }} className="mut">
        <span>{qual.min}</span><span>QUAL</span><span>{qual.max}</span>
      </div>
    </>
  );
}

export default function Distribusi({ idAnalisis }) {
  const [d, setD] = useState(null); const [err, setErr] = useState("");
  useEffect(() => { svc.distribusi(idAnalisis).then(setD).catch((e) => setErr(e.message)); }, [idAnalisis]);
  if (err) return <Card title="Distribusi Varian" dot="ind"><p className="mut">{err}</p></Card>;
  if (!d) return <Card title="Distribusi Varian" dot="ind"><p className="mut">Memuat grafik...</p></Card>;
  if (!d.kromosom.length) return null;
  return (
    <div className="grid2" style={{ gridTemplateColumns: "1fr 1fr" }}>
      <Card title="Varian per Kromosom" dot="ind"><BarH data={d.kromosom} /></Card>
      <div>
        <Card title="Jenis Varian" dot="ind"><BarH data={d.jenis} /></Card>
        <Card title="Distribusi Kualitas (QUAL)" dot="ind"><Histogram qual={d.qual} /></Card>
      </div>
    </div>
  );
}
