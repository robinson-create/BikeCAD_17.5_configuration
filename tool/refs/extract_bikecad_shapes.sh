#!/usr/bin/env bash
# Pipeline d'extraction des FORMES STATIQUES de BikeCAD (carters moteur).
# Appelle le code de BikeCAD par réflexion → tracés SVG → refs/bikecad_shapes.json.
# Pré-requis : JDK 11 + BikeCAD Pro .app présents.
set -e
JDK=/opt/homebrew/opt/openjdk@11/bin
JAR="$HOME/Downloads/BikeCadPRO/BikeCAD Pro 16.0.app/Contents/Java/bikeCADPro.jar"
cd "$(dirname "$0")"
"$JDK/javac" -cp "$JAR" Extract.java
"$JDK/java" -Djava.awt.headless=true -cp "$JAR:." Extract basic.bafang getGArea,getGDet
echo "(adapter le post-traitement JSON selon besoin — cf. git log)"
