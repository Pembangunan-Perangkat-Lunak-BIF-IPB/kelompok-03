import Link from "next/link";
import { Card, Empty } from "./ui";
export default function NoActive({ error }) {
  return (
    <Card><Empty>
      <p>{error || "Belum ada analisis yang dipilih."}</p>
      <Link className="btn pri" href="/unggah">Mulai dari Unggah Data</Link>
    </Empty></Card>
  );
}
