#!/usr/bin/env bash
# Diagnostic : dump l'arborescence du menu "Fichier" de BikeCAD Pro (titres EXACTS).
# Sert à vérifier/ajuster les libellés utilisés par le pipeline d'export.
# Pré-requis : BikeCAD Pro lancé (au moins une fenêtre ouverte).
PROC="BikeCAD Pro 16.0"
osascript <<APPLESCRIPT
tell application "System Events"
  if not (exists process "$PROC") then return "Process '$PROC' introuvable — lance BikeCAD Pro d'abord."
  tell process "$PROC"
    set frontmost to true
    delay 0.5
    set out to ""
    repeat with mbi in menu bar items of menu bar 1
      set out to out & "▸ " & (name of mbi) & "\n"
      try
        repeat with mi in menu items of menu 1 of mbi
          try
            set out to out & "    - " & (name of mi) & "\n"
          end try
        end repeat
      end try
    end repeat
    return out
  end tell
end tell
APPLESCRIPT
