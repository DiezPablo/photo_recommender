#!/usr/bin/env bash
# Publica ficheros generados en public/datos sin conflictos: los ficheros generados mandan, así que en vez
# de fusionar se parte siempre del último main remoto, se copian encima y se empuja (con reintentos por
# si otro workflow publica a la vez).
# Uso: publicar.sh "mensaje de commit" fichero1 [fichero2 ...]   (rutas de origen; se copian a public/datos/)
set -euo pipefail
mensaje="$1"; shift
tmp=$(mktemp -d)
for f in "$@"; do
  [ -f "$f" ] || { echo "No existe $f: nada que publicar"; exit 0; }
  cp "$f" "$tmp/"
done
git config user.name "github-actions"
git config user.email "github-actions@users.noreply.github.com"
for intento in 1 2 3 4 5; do
  git fetch -q origin main
  git reset -q --hard origin/main
  mkdir -p public/datos
  cp "$tmp"/* public/datos/
  git add public/datos
  if git diff --cached --quiet; then echo "Sin cambios"; exit 0; fi
  git commit -q -m "$mensaje"
  if git push -q origin HEAD:main; then echo "Publicado: $mensaje"; exit 0; fi
  sleep $((intento * 5))
done
echo "No se pudo publicar tras 5 intentos"; exit 1
