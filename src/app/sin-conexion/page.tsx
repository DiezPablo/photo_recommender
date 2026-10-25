import type { Metadata } from "next";
import ListaGuardadas from "@/features/offline/ListaGuardadas";

export const metadata: Metadata = { title: "Sin conexión", robots: { index: false } };

// Sin red puede que el JavaScript de esta página no esté en el dispositivo (nunca se visitó): la lista de
// guardadas se pinta con un script en línea que no depende de React. Si React sí carga, la pinta
// ListaGuardadas y el script no toca nada (los dos sobre el mismo HTML rompen la hidratación).
const scriptGuardadas = `setTimeout(async function(){if(window.__guardadasReact)return;var ul=document.getElementById("guardadas");
if(!ul||!("caches" in window))return;try{var c=await caches.open("guardadas"),ks=await c.keys();if(!ks.length)return;ul.innerHTML="";
for(var k of ks){var r=await c.match(k),h=r?await r.text():"",m=/<title>([^<]*)<\\/title>/.exec(h),
t=(m?m[1]:k.url).replace(/ · Rasante$/,"").replace(/&amp;/g,"&"),li=document.createElement("li"),a=document.createElement("a");
a.href=new URL(k.url).pathname;a.textContent=t;li.appendChild(a);ul.appendChild(li)}}catch(e){}},1500)`;

export default function SinConexion() {
  return (
    <main className="calendario">
      <header className="titular">
        <p className="rotulo">Sin conexión</p>
        <h1>No hay cobertura</h1>
        <p className="entradilla">
          Esta página no está en el dispositivo. Puedes abrir las fichas que guardaste y las que visitaste hace poco;
          los mapas muestran las zonas que ya viste.
        </p>
      </header>
      <section className="seccion">
        <h2 className="rotulo">Guardadas en este dispositivo</h2>
        <ListaGuardadas />
        <script dangerouslySetInnerHTML={{ __html: scriptGuardadas }} />
      </section>
    </main>
  );
}
