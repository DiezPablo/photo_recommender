// «Nubes ahora»: la última imagen del satélite MTG de EUMETSAT (GeoColour: color real de día, infrarrojo de
// noche; cada 10 min) sobre el mapa. Servicio WMS público, sin clave ni restricciones de acceso.
import type { Control, Map as LMap, TileLayer } from "leaflet";
import type { Leaflet } from "@/ui/mapa/useMapaBase";

const WMS = "https://view.eumetsat.int/geoserver/ows";
const CAPA = "mtg_fd:rgb_geocolour";
const REFRESCO_MS = 10 * 60 * 1000;

export function controlSatelite(L: Leaflet, m: LMap): Control {
  let capa: TileLayer.WMS | null = null;
  let reloj: ReturnType<typeof setInterval> | null = null;

  const Boton = L.Control.extend({
    onAdd() {
      const b = L.DomUtil.create("button", "boton-satelite");
      b.type = "button";
      b.textContent = "Nubes ahora";
      b.title = "Última imagen del satélite (EUMETSAT, cada 10 minutos)";
      b.setAttribute("aria-pressed", "false");
      L.DomEvent.disableClickPropagation(b);
      L.DomEvent.on(b, "click", () => {
        if (capa) {
          capa.remove();
          capa = null;
          if (reloj) clearInterval(reloj);
          b.setAttribute("aria-pressed", "false");
          return;
        }
        capa = L.tileLayer
          .wms(WMS, {
            layers: CAPA,
            format: "image/png",
            transparent: true,
            version: "1.3.0",
            opacity: 0.85,
            attribution: 'Satélite © <a href="https://view.eumetsat.int">EUMETSAT</a>',
            className: "capa-satelite",
          })
          .addTo(m);
        // la imagen cambia cada 10 min: se vuelve a pedir mientras esté activa
        reloj = setInterval(() => capa?.setParams({ _: String(Date.now()) } as never), REFRESCO_MS);
        b.setAttribute("aria-pressed", "true");
      });
      return b;
    },
    onRemove() {
      if (reloj) clearInterval(reloj);
    },
  });
  return new Boton({ position: "topright" }).addTo(m);
}
