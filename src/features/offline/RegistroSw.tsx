"use client";
// Registra el service worker (solo en producción: en desarrollo cachearía código a medio cambiar).
import { useEffect } from "react";

export default function RegistroSw() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production" || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }, []);
  return null;
}
