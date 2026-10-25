"""Aeropuertos españoles con METAR (código OACI → latitud, longitud)."""

AEROPUERTOS: dict[str, tuple[float, float]] = {
    "LEMD": (40.472, -3.561),  # Madrid-Barajas
    "LEGT": (40.294, -3.724),  # Getafe
    "LEBL": (41.297, 2.078),  # Barcelona
    "LEGE": (41.901, 2.760),  # Girona
    "LERS": (41.147, 1.167),  # Reus
    "LEZG": (41.666, -1.042),  # Zaragoza
    "LEHC": (42.083, -0.324),  # Huesca
    "LEPP": (42.770, -1.646),  # Pamplona
    "LELO": (42.461, -2.322),  # Logroño
    "LEVT": (42.883, -2.724),  # Vitoria
    "LEBB": (43.301, -2.911),  # Bilbao
    "LEXJ": (43.427, -3.820),  # Santander
    "LEAS": (43.564, -6.035),  # Asturias
    "LECO": (43.302, -8.377),  # A Coruña
    "LEST": (42.896, -8.415),  # Santiago
    "LEVX": (42.232, -8.627),  # Vigo
    "LELN": (42.589, -5.656),  # León
    "LEBG": (42.357, -3.620),  # Burgos
    "LEVD": (41.706, -4.852),  # Valladolid
    "LESA": (40.952, -5.502),  # Salamanca
    "LEBZ": (38.891, -6.821),  # Badajoz
    "LEAB": (38.948, -1.864),  # Albacete
    "LEVC": (39.489, -0.482),  # Valencia
    "LEAL": (38.282, -0.558),  # Alicante
    "LEMI": (37.803, -1.125),  # Región de Murcia
    "LEAM": (36.844, -2.370),  # Almería
    "LEGR": (37.189, -3.777),  # Granada
    "LEMG": (36.675, -4.499),  # Málaga
    "LEZL": (37.418, -5.893),  # Sevilla
    "LEJR": (36.745, -6.060),  # Jerez
    "LEPA": (39.552, 2.739),  # Palma
    "GCXO": (28.483, -16.342),  # Tenerife Norte
    "GCTS": (28.044, -16.573),  # Tenerife Sur
    "GCLP": (27.932, -15.387),  # Gran Canaria
    "GCRR": (28.946, -13.605),  # Lanzarote
}
