#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Pipeline d'automatisation GUI : pilote BikeCAD Pro pour EXPORTER EN SVG
# (vrais rendus BikeCAD, vectoriels) une liste de fichiers .bcad, en boucle.
#
# BikeCAD se bootstrappe correctement quand c'est LUI qui se lance → on le pilote
# via AppleScript (System Events) au lieu d'émuler son rendu (cf. memory).
#
# ⚠️  À lancer SUR TA MACHINE, avec l'écran déverrouillé. Autorise d'abord
#     Terminal/iTerm dans Réglages Système → Confidentialité → Accessibilité.
#     Regarde la 1re itération : si un libellé/délai cloche, ajuste les vars.
#
# Usage :  ./bikecad_batch_export.sh [DOSSIER_BCAD] [DOSSIER_SORTIE]
#   défaut : ~/BikeCAD_16.0_configuration/BIKE  →  tool/out_bikecad_svg/
# ─────────────────────────────────────────────────────────────────────────────
set -u

APP="$HOME/Downloads/BikeCadPRO/BikeCAD Pro 16.0.app"
PROC="BikeCAD Pro 16.0"                 # nom du process (cf. CFBundleName)
FILE_MENU="Fichier"                      # menu (FR). EN : "File"
OPEN_ITEM="Ouvrir un fichier BikeCAD"    # EN : "Open BikeCAD file" (vérifier via dump)
EXPORT_ITEM="Exporter SVG"               # EN : "Export SVG"

IN_DIR="${1:-$HOME/BikeCAD_16.0_configuration/BIKE}"
OUT_DIR="${2:-$(cd "$(dirname "$0")/.." && pwd)/out_bikecad_svg}"

# Délais (s) — à augmenter si ta machine/BikeCAD est lent
T_OPEN_MENU=0.6      # après clic menu, avant frappe chemin
T_LOAD=3.0          # temps de chargement + recalcul du vélo
T_EXPORT_DLG=0.8    # après clic Exporter SVG, avant frappe chemin
T_SAVE=2.0          # temps d'écriture du SVG
OPTIONS_DIALOG=false # mettre true si "Exporter SVG" ouvre une boîte d'options AVANT le chooser

mkdir -p "$OUT_DIR"
[ -d "$APP" ] || { echo "❌ App introuvable : $APP"; exit 1; }

echo "▶ Lancement de BikeCAD Pro…"
open -a "$APP"
sleep 6   # laisse le bootstrap (splash + init) se faire

click_menu_item () {  # $1 = libellé de l'item sous FILE_MENU
  osascript - "$1" <<'APPLESCRIPT'
on run argv
  set itemName to item 1 of argv
  tell application "System Events" to tell process (system attribute "BCPROC")
    set frontmost to true
    delay 0.3
    click menu item itemName of menu 1 of menu bar item (system attribute "BCFILEMENU") of menu bar 1
  end tell
end run
APPLESCRIPT
}

type_path_enter () {  # $1 = chemin à saisir dans le JFileChooser
  osascript - "$1" <<'APPLESCRIPT'
on run argv
  set p to item 1 of argv
  tell application "System Events" to tell process (system attribute "BCPROC")
    set frontmost to true
    delay 0.2
    keystroke "a" using command down   -- sélectionne le champ nom
    delay 0.1
    keystroke p
    delay 0.1
    key code 36                        -- Return (valide / navigue)
    delay 0.4
    key code 36                        -- 2e Return (confirme certains choosers)
  end tell
end run
APPLESCRIPT
}

export BCPROC="$PROC" BCFILEMENU="$FILE_MENU"
n=0
shopt -s nullglob
for f in "$IN_DIR"/*.bcad; do
  base="$(basename "$f" .bcad)"
  out="$OUT_DIR/$base.svg"
  echo "  • $base"
  # 1) Ouvrir le .bcad
  click_menu_item "$OPEN_ITEM";  sleep "$T_OPEN_MENU"
  type_path_enter "$f";          sleep "$T_LOAD"
  # 2) Exporter SVG
  click_menu_item "$EXPORT_ITEM"; sleep "$T_EXPORT_DLG"
  if [ "$OPTIONS_DIALOG" = true ]; then osascript -e 'tell application "System Events" to key code 36'; sleep 0.6; fi
  type_path_enter "$out";         sleep "$T_SAVE"
  [ -f "$out" ] && { echo "      ✓ $out"; n=$((n+1)); } || echo "      ⚠ pas trouvé $out (ajuster délais/libellés)"
done

echo ""
echo "$n SVG exportés dans $OUT_DIR"
echo "Si 0 : lance d'abord  ./scripts/bikecad_dump_menus.sh  pour vérifier les libellés de menu."
