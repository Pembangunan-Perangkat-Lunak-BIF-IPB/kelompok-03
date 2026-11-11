import { FlaskIcon } from "./ui";
// Bingkai halaman akun (masuk, daftar, verifikasi, lupa/atur ulang sandi)
export default function AuthCard({ title, sub, children, onSubmit }) {
  const Tag = onSubmit ? "form" : "div";
  return (
    <div className="login">
      <Tag className="card" onSubmit={onSubmit}>
        <div className="logo"><i><FlaskIcon /></i>Human GVC</div>
        {title && <h1>{title}</h1>}{sub && <p className="sub">{sub}</p>}
        {children}
      </Tag>
    </div>
  );
}
