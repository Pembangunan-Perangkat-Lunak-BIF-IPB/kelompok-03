import Link from "next/link";

export default function Nav() {
  return (
    <header className="nav">
      <Link href="/" className="brand">Human GVC</Link>
      <nav>
        <Link href="/sampel">Sampel</Link>
        <Link href="/analisis">Analisis</Link>
        <Link href="/login">Masuk</Link>
      </nav>
    </header>
  );
}
