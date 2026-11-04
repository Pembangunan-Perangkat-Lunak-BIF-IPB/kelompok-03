"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getUser } from "../lib/session";
export default function Home() {
  const r = useRouter();
  useEffect(() => { r.replace(getUser() ? "/unggah" : "/login"); }, [r]);
  return null;
}
