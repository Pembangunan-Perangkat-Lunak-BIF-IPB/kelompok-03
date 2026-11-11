"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { NAV, PERAN_LABEL, sampelCode } from "../lib/constants";
import { getUser, clearSession, getActive, setActive } from "../lib/session";
import { svc } from "../lib/api";
import { FlaskIcon, StatusBadge } from "./ui";

export default function AppShell({ children }) {
  const path = usePathname(), router = useRouter();
  const [user, setUser] = useState(undefined);
  const [active, setAct] = useState(null);
  const [list, setList] = useState([]);
  const [open, setOpen] = useState(false);

  useEffect(() => { const u = getUser(); if (!u) router.replace("/login"); else setUser(u); }, [router]);
  useEffect(() => {
    const sync = () => setAct(getActive());
    sync(); window.addEventListener("gvc:active", sync); return () => window.removeEventListener("gvc:active", sync);
  }, []);
  // Akses halaman admin hanya untuk administrator (UC-07; NFR keamanan)
  useEffect(() => { if (user && path.startsWith("/admin") && user.peran !== "administrator") router.replace("/unggah"); }, [user, path, router]);

  async function toggle() {
    if (!open) { try { setList(await svc.listAnalisis()); } catch { setList([]); } }
    setOpen(!open);
  }
  if (!user) return null;
  if (path.startsWith("/admin") && user.peran !== "administrator") return null; // jangan render/panggil API admin untuk non-admin
  const items = NAV.filter((n) => !n.admin || user.peran === "administrator");
  const cur = NAV.find((n) => path.startsWith(n.href));
  const initials = user.nama.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();
  const act = list.find((a) => a.id_analisis === active);

  return (
    <div className="shell">
      <aside className="side">
        <div className="logo"><i><FlaskIcon /></i>Human GVC</div>
        <nav aria-label="Navigasi utama">
          {items.map((n) => (
            <Link key={n.href} href={n.href} className={`${path.startsWith(n.href) ? "on" : ""} ${n.admin ? "adm" : ""}`}>{n.label}</Link>
          ))}
        </nav>
        <div className="sp" />
        <button className="out" onClick={() => { clearSession(); router.replace("/login"); }}>Keluar</button>
      </aside>
      <div>
        <header className="top">
          <h1>{cur?.title}</h1>
          <div className="who">
            <div className="chip">
              <button onClick={toggle} aria-expanded={open}>{active ? `Analisis aktif #${active}` : "Belum ada analisis aktif"} ▾</button>
              {open && (
                <div className="menu">
                  <button onClick={() => { setActive(null); setOpen(false); router.push("/unggah"); }}><b>+ Analisis baru</b></button>
                  {list.length === 0 && <div className="mut" style={{ padding: ".6rem .7rem" }}>Belum ada riwayat analisis.</div>}
                  {list.map((a) => (
                    <button key={a.id_analisis} className={a.id_analisis === active ? "cur" : ""}
                      onClick={() => { setActive(a.id_analisis); setOpen(false); router.push(a.status === "draf" ? "/pengaturan" : a.status === "selesai" ? "/hasil" : "/status"); }}>
                      <span>#{a.id_analisis} · {a.sampel ? sampelCode(a.sampel.id_sampel, a.sampel.dibuat_pada) : "-"}<br /><small className="mut">{a.sampel?.nama_sampel}</small></span>
                      <StatusBadge status={a.status} />
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div><b>{user.nama}</b><small>{PERAN_LABEL[user.peran]}</small></div>
            <div className="av">{initials}</div>
          </div>
        </header>
        <div className="page">{children}</div>
      </div>
    </div>
  );
}
