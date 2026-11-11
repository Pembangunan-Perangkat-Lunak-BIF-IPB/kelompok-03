"use client";
import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { svc } from "../../lib/api";
import { Alert } from "../../components/ui";
import AuthCard from "../../components/AuthCard";

function Isi() {
  const token = useSearchParams().get("token");
  const [s, setS] = useState({ t: "info", m: "Memverifikasi email Anda..." }); const sudah = useRef(false);
  useEffect(() => {
    if (sudah.current) return; sudah.current = true;   // cegah panggilan ganda (React Strict Mode)
    if (!token) return setS({ t: "err", m: "Tautan verifikasi tidak lengkap." });
    svc.verifikasi(token).then((d) => setS({ t: "ok", m: d.pesan })).catch((e) => setS({ t: "err", m: e.message }));
  }, [token]);
  return (
    <AuthCard title="Verifikasi email">
      <Alert type={s.t}>{s.m}</Alert>
      <div className="alt"><Link href="/login"><b>Ke halaman masuk</b></Link></div>
    </AuthCard>
  );
}
export default function Verifikasi() { return <Suspense fallback={null}><Isi /></Suspense>; }
