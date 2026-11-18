// Semua permintaan /api/* diteruskan ke backend di laptop ini.
// Dengan begitu pengguna dari internet cukup mengakses SATU alamat (port 3000).
module.exports = {
  reactStrictMode: true,
  experimental: { proxyTimeout: 600000 }, // 10 menit, agar unggah FASTQ besar tidak terputus
  async headers() {
    return [{ source: "/:path*", headers: [
      { key: "X-Frame-Options", value: "DENY" },
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "Referrer-Policy", value: "same-origin" },
    ] }];
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: "http://127.0.0.1:8000/api/:path*" }];
  },
};
