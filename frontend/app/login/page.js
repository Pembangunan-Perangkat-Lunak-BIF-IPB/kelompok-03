export default function Masuk() {
  return (
    <>
      <h1>Masuk</h1>
      <p className="lead">Autentikasi akan diimplementasikan pada tahap integrasi (Minggu 8).</p>
      <section className="panel">
        <form>
          <label>Email<input type="email" disabled placeholder="nama@ipb.ac.id" /></label>
          <label>Kata sandi<input type="password" disabled /></label>
          <button disabled>Masuk</button>
        </form>
      </section>
    </>
  );
}
