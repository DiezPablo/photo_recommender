import Link from "next/link";

export default function NoEncontrado() {
  return (
    <main className="prosa">
      <h1>No encontrado</h1>
      <p>
        Ese spot o día no existe (los spots se actualizan cada mes). <Link href="/">Volver al ranking</Link>.
      </p>
    </main>
  );
}
