import "./globals.css";
import Nav from "../components/Nav";

export const metadata = {
  title: "Human GVC",
  description: "Platform variant calling berbasis web",
};

export default function RootLayout({ children }) {
  return (
    <html lang="id">
      <body>
        <Nav />
        <main>{children}</main>
      </body>
    </html>
  );
}
