#!/usr/bin/env python3
"""
SCiPNET — Systeme d'Armement Strategique v1.0
Niveau requis : N4 (site uniquement) ou N5 (acces complet)
USAGE STRICTEMENT ROLEPLAY
"""
import sys, json, random, hashlib, time
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit,
    QStackedWidget, QFrame, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSlot
from PyQt6.QtGui import QColor, QPainter, QPen, QLinearGradient, QFont
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
sys.path.insert(0, "/opt/scipnet")
from scipnet_common import (
    BG, BG2, BG3, WIN_BG, BORDER, BORDER_B,
    WHITE, DIM, DARK, CYAN, CYAN_D, RED, YELLOW, GREEN,
    MONO, NIVEAU_LABELS, NIVEAU_COLORS,
    F, S, DataStore, ScipnetWindow, check_clearance, load_barlow,
)

# Token de securite genere aleatoirement au premier lancement
def _get_or_create_token() -> str:
    cfg = DataStore.load("armes_config.dat", {})
    if "token" not in cfg:
        cfg["token"] = str(random.randint(100000000, 999999999))
        DataStore.save("armes_config.dat", cfg)
    return cfg["token"]

def _log_action(action: str, login: str, details: str = ""):
    logs = DataStore.load("armes_log.dat", [])
    logs.append({
        "date": datetime.now().isoformat(),
        "login": login,
        "action": action,
        "details": details,
    })
    DataStore.save("armes_log.dat", logs[-200:])

def _force_evacuation(login: str):
    """Force l'etat EVACUATION sur le site."""
    cfg = DataStore.load("config.dat", {})
    cfg["site_etat"] = "EVACUATION"
    personnel = cfg.get("personnel", [])
    for d in personnel:
        d["etat"] = "EVACUATION"
    cfg["personnel"] = personnel
    DataStore.save("config.dat", cfg)
    _log_action("EVACUATION_FORCEE", login, "Suite au lancement d'une frappe strategique")

# Globe 3D HTML/WebGL via CesiumJS
GLOBE_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>SCiPNET Targeting System</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
html, body { width:100%; height:100%; background:#000; overflow:hidden; }
#cesiumContainer { width:100%; height:100%; }
#target-info {
    position:absolute; top:10px; right:10px;
    background:rgba(0,0,0,0.8); border:1px solid #00d4ff;
    color:#00d4ff; font-family:'Courier New'; font-size:11px;
    padding:10px 14px; min-width:200px;
}
#crosshair {
    position:absolute; top:50%; left:50%;
    transform:translate(-50%,-50%);
    color:#cc3333; font-size:24px; pointer-events:none;
    display:none;
}
#status {
    position:absolute; bottom:10px; left:50%;
    transform:translateX(-50%);
    background:rgba(0,0,0,0.8); border:1px solid #cc3333;
    color:#cc3333; font-family:'Courier New'; font-size:10px;
    padding:6px 14px; letter-spacing:2px;
    display:none;
}
</style>
<script src="https://cesium.com/downloads/cesiumjs/releases/1.111/Build/Cesium/Cesium.js"></script>
<link href="https://cesium.com/downloads/cesiumjs/releases/1.111/Build/Cesium/Widgets/widgets.css" rel="stylesheet">
</head>
<body>
<div id="cesiumContainer"></div>
<div id="target-info">
    <div style="color:#6a6a6a;letter-spacing:2px;margin-bottom:6px;">SYSTEME DE CIBLAGE</div>
    <div>Lat : <span id="lat">--</span></div>
    <div>Lon : <span id="lon">--</span></div>
    <div>Cible : <span id="location">--</span></div>
    <div style="margin-top:6px;color:#6a6a6a;">Cliquez sur la carte</div>
</div>
<div id="crosshair">⊕</div>
<div id="status">SYSTEME ARME - PRET AU LANCEMENT</div>
<script>
Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJlYTIzYzcwZC1lNmQ3LTRmZGEtYjliMS03ZGY2NjJkMTdkOGMiLCJpZCI6MjYwMDgsInNjb3BlcyI6WyJhc3IiXSwiaWF0IjoxNTg3MDY5MzE1fQ.MUhGxBJbJJjsJ7V8UPDa0_wjmRJrq_KQnr4p0WIgDmE';

const viewer = new Cesium.Viewer('cesiumContainer', {
    animation: false, baseLayerPicker: false, fullscreenButton: false,
    geocoder: false, homeButton: false, infoBox: false,
    sceneModePicker: false, selectionIndicator: false,
    timeline: false, navigationHelpButton: false,
    creditContainer: document.createElement('div'),
    imageryProvider: new Cesium.TileMapServiceImageryProvider({
        url: Cesium.buildModuleUrl('Assets/Textures/NaturalEarthII'),
    }),
});

// Style sombre militaire
viewer.scene.backgroundColor = Cesium.Color.fromCssColorString('#000000');
viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString('#0a0a0f');
viewer.scene.globe.showGroundAtmosphere = false;
viewer.scene.skyBox.show = true;

let targetEntity = null;
let currentCoords = null;
let armed = false;

// Click handler
viewer.canvas.addEventListener('click', function(e) {
    const ray = viewer.camera.getPickRay(new Cesium.Cartesian2(e.clientX, e.clientY));
    const position = viewer.scene.globe.pick(ray, viewer.scene);
    if (!position) return;
    const cart = Cesium.Cartographic.fromCartesian(position);
    const lat = Cesium.Math.toDegrees(cart.latitude).toFixed(4);
    const lon = Cesium.Math.toDegrees(cart.longitude).toFixed(4);
    currentCoords = {lat: parseFloat(lat), lon: parseFloat(lon)};
    document.getElementById('lat').textContent = lat + ' deg';
    document.getElementById('lon').textContent = lon + ' deg';
    document.getElementById('crosshair').style.display = 'block';

    // Supprimer l'ancienne cible
    if (targetEntity) viewer.entities.remove(targetEntity);

    // Marquer la cible
    targetEntity = viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(parseFloat(lon), parseFloat(lat)),
        billboard: {
            image: data_uri_crosshair(),
            width: 32, height: 32,
        },
        label: {
            text: 'CIBLE',
            font: '12px Courier New',
            fillColor: Cesium.Color.fromCssColorString('#cc3333'),
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 2,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
            pixelOffset: new Cesium.Cartesian2(0, -20),
        },
    });

    // Envoyer les coordonnees au Python
    if (typeof qt !== 'undefined') {
        qt.coordsSelected(lat, lon);
    }
    window.currentLat = lat;
    window.currentLon = lon;
});

function data_uri_crosshair() {
    const canvas = document.createElement('canvas');
    canvas.width = 32; canvas.height = 32;
    const ctx = canvas.getContext('2d');
    ctx.strokeStyle = '#cc3333'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(16,2); ctx.lineTo(16,30); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(2,16); ctx.lineTo(30,16); ctx.stroke();
    ctx.beginPath(); ctx.arc(16,16,8,0,Math.PI*2); ctx.stroke();
    return canvas.toDataURL();
}

function setArmed(armed_state) {
    armed = armed_state;
    const status = document.getElementById('status');
    if (armed) { status.style.display='block'; }
    else { status.style.display='none'; }
}

function flyToCoords(lat, lon) {
    viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(parseFloat(lon), parseFloat(lat), 2000000),
        duration: 2,
    });
    // Simuler le click
    if (targetEntity) viewer.entities.remove(targetEntity);
    targetEntity = viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(parseFloat(lon), parseFloat(lat)),
        label: {
            text: 'CIBLE : ' + lat + ' / ' + lon,
            font: '12px Courier New',
            fillColor: Cesium.Color.fromCssColorString('#cc3333'),
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 2,
            verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
            pixelOffset: new Cesium.Cartesian2(0,-20),
        },
    });
    document.getElementById('lat').textContent = lat + ' deg';
    document.getElementById('lon').textContent = lon + ' deg';
    document.getElementById('crosshair').style.display='block';
    currentCoords = {lat:parseFloat(lat), lon:parseFloat(lon)};
    window.currentLat = lat; window.currentLon = lon;
}

function launchAnimation(lat, lon) {
    // Animation de trajectoire
    const start = Cesium.Cartesian3.fromDegrees(2.3, 48.8, 0); // Paris comme base
    const target = Cesium.Cartesian3.fromDegrees(parseFloat(lon), parseFloat(lat), 0);
    const mid = Cesium.Cartesian3.midpoint(start, target, new Cesium.Cartesian3());
    // Flash rouge
    viewer.scene.backgroundColor = Cesium.Color.fromCssColorString('#330000');
    setTimeout(() => { viewer.scene.backgroundColor = Cesium.Color.BLACK; }, 500);
    setTimeout(() => { viewer.scene.backgroundColor = Cesium.Color.fromCssColorString('#330000'); }, 1000);
    setTimeout(() => { viewer.scene.backgroundColor = Cesium.Color.BLACK; }, 1500);
}
</script>
</body>
</html>"""

class LaunchWidget(QWidget):
    """Widget de sequence de lancement."""
    def __init__(self, login, niveau, nom_affiche, parent=None):
        super().__init__(parent)
        self.login = login; self.niveau = niveau; self.nom_affiche = nom_affiche
        self._target_lat = ""; self._target_lon = ""
        self._armed = False
        self._token = _get_or_create_token()
        self._build()

    def _build(self):
        self.setStyleSheet(f"background:{WIN_BG};")
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        # Barre d'etat
        status_bar = QWidget(); status_bar.setFixedHeight(40)
        status_bar.setStyleSheet(f"background:{BG2};border-bottom:1px solid {BORDER};")
        sh = QHBoxLayout(status_bar); sh.setContentsMargins(16,0,16,0); sh.setSpacing(16)
        self._status_lbl = QLabel("SYSTEME HORS LIGNE  |  AUTHENTIFICATION REQUISE")
        self._status_lbl.setStyleSheet(S(DIM,9,bold=True,ls=2))
        sh.addWidget(self._status_lbl, 1)
        self._level_lbl = QLabel(f"NIVEAU {self.niveau}  |  {NIVEAU_LABELS.get(self.niveau,'?')}")
        self._level_lbl.setStyleSheet(S(NIVEAU_COLORS.get(self.niveau,DIM),9,ls=2))
        sh.addWidget(self._level_lbl)
        root.addWidget(status_bar)

        # Zone principale
        main = QHBoxLayout(); main.setContentsMargins(0,0,0,0); main.setSpacing(0)

        # Globe
        self._globe = QWebEngineView()
        self._globe.setHtml(GLOBE_HTML)
        main.addWidget(self._globe, 1)

        # Panneau de controle
        ctrl = QWidget(); ctrl.setFixedWidth(320)
        ctrl.setStyleSheet(f"background:{BG2};border-left:1px solid {BORDER};")
        cv = QVBoxLayout(ctrl); cv.setContentsMargins(0,0,0,0); cv.setSpacing(0)

        # Titre
        hdr = QWidget(); hdr.setFixedHeight(48)
        hdr.setStyleSheet(f"background:{BG3};border-bottom:1px solid {BORDER};")
        hh = QHBoxLayout(hdr); hh.setContentsMargins(16,0,16,0)
        hh.addWidget(QLabel("CONTROLE DE FRAPPE",
            styleSheet=S(RED,10,bold=True,ls=3)))
        cv.addWidget(hdr)

        # Contenu scroll
        body = QWidget(); body.setStyleSheet(f"background:transparent;")
        bv = QVBoxLayout(body); bv.setContentsMargins(16,16,16,16); bv.setSpacing(10)

        # Coordonnees
        bv.addWidget(QLabel("COORDONNEES CIBLE",styleSheet=S(DIM,8,bold=True,ls=2)))
        coords_row = QHBoxLayout(); coords_row.setSpacing(6)
        self._lat_i = self._inp("Latitude (ex: 48.8566)")
        self._lon_i = self._inp("Longitude (ex: 2.3522)")
        coords_row.addWidget(self._lat_i); coords_row.addWidget(self._lon_i)
        bv.addLayout(coords_row)

        target_btn = QPushButton("LOCALISER SUR LE GLOBE")
        target_btn.setStyleSheet(
            f"QPushButton{{background:{BG3};color:{CYAN};font-family:'{MONO}';"
            f"font-size:9px;letter-spacing:2px;padding:6px;border:1px solid {BORDER_B};}}"
            f"QPushButton:hover{{background:{CYAN};color:{BG};}}"
        )
        target_btn.clicked.connect(self._locate)
        bv.addWidget(target_btn)

        bv.addWidget(self._sep())

        # Token
        bv.addWidget(QLabel("CODE D'AUTORISATION",styleSheet=S(DIM,8,bold=True,ls=2)))
        bv.addWidget(QLabel(f"Token actif : {self._token}",styleSheet=S(DARK,8,ls=0)))
        self._token_i = self._inp("Code numerique a 9 chiffres")
        bv.addWidget(self._token_i)

        # MdP
        bv.addWidget(QLabel("MOT DE PASSE COMPTE",styleSheet=S(DIM,8,bold=True,ls=2)))
        self._mdp_i = self._inp("Mot de passe", pwd=True)
        bv.addWidget(self._mdp_i)

        bv.addWidget(self._sep())

        # Bouton armer
        self._arm_btn = QPushButton("  ⚠  ARMER LE SYSTEME")
        self._arm_btn.setStyleSheet(
            f"QPushButton{{background:{BG3};color:{YELLOW};font-family:'{MONO}';"
            f"font-size:10px;font-weight:600;letter-spacing:3px;padding:10px;"
            f"border:2px solid {YELLOW};}}"
            f"QPushButton:hover{{background:{YELLOW};color:{BG};}}"
        )
        self._arm_btn.clicked.connect(self._arm)
        bv.addWidget(self._arm_btn)

        # Bouton lancer
        self._launch_btn = QPushButton("  ⊗  LANCER LA FRAPPE")
        self._launch_btn.setEnabled(False)
        self._launch_btn.setStyleSheet(
            f"QPushButton{{background:{BG3};color:{DARK};font-family:'{MONO}';"
            f"font-size:10px;font-weight:600;letter-spacing:3px;padding:10px;"
            f"border:2px solid {DARK};}}"
            f"QPushButton:disabled{{color:{DARK};border-color:{DARK};}}"
            f"QPushButton:enabled{{color:{RED};border-color:{RED};}}"
            f"QPushButton:enabled:hover{{background:{RED};color:{BG};}}"
        )
        self._launch_btn.clicked.connect(self._launch)
        bv.addWidget(self._launch_btn)

        # Message
        self._msg = QLabel("")
        self._msg.setStyleSheet(S(DIM,8,ls=0)); self._msg.setWordWrap(True)
        bv.addWidget(self._msg)

        bv.addWidget(self._sep())

        # Journal local
        bv.addWidget(QLabel("JOURNAL",styleSheet=S(DARK,8,bold=True,ls=2)))
        self._log = QTextEdit(); self._log.setReadOnly(True)
        self._log.setFixedHeight(120)
        self._log.setStyleSheet(
            f"background:{BG3};color:{DIM};font-family:'{MONO}';"
            f"font-size:8px;border:none;padding:6px;"
        )
        bv.addWidget(self._log)
        bv.addStretch()
        cv.addWidget(body, 1)
        main.addWidget(ctrl)

        root_w = QWidget(); root_w.setLayout(main)
        root.addWidget(root_w, 1)

    def _inp(self, ph="", pwd=False):
        f = QLineEdit(); f.setPlaceholderText(ph)
        if pwd: f.setEchoMode(QLineEdit.EchoMode.Password)
        f.setStyleSheet(
            f"QLineEdit{{background:{BG3};color:{WHITE};font-family:'{MONO}';"
            f"font-size:10px;border:1px solid {BORDER_B};padding:5px 8px;}}"
            f"QLineEdit:focus{{border:1px solid {CYAN};}}"
        )
        pal = f.palette(); pal.setColor(pal.ColorRole.Text, QColor(WHITE))
        pal.setColor(pal.ColorRole.Base, QColor(BG3)); f.setPalette(pal)
        return f

    def _sep(self):
        f = QFrame(); f.setFixedHeight(1)
        f.setStyleSheet(f"background:{BORDER};"); return f

    def _log_msg(self, msg, col=DIM):
        t = datetime.now().strftime("%H:%M:%S")
        self._log.append(f"<span style='color:{DARK};'>[{t}]</span> <span style='color:{col};'>{msg}</span>")

    def _locate(self):
        lat = self._lat_i.text().strip()
        lon = self._lon_i.text().strip()
        if not lat or not lon:
            self._msg.setText("Entrez des coordonnees valides."); return
        try:
            float(lat); float(lon)
        except ValueError:
            self._msg.setText("Format invalide. Ex: 48.8566 / 2.3522"); return
        self._target_lat = lat; self._target_lon = lon
        self._globe.page().runJavaScript(f"flyToCoords('{lat}', '{lon}');")
        self._log_msg(f"Cible localisee : {lat} / {lon}", YELLOW)
        self._msg.setText("")

    def _arm(self):
        token = self._token_i.text().strip()
        mdp   = self._mdp_i.text().strip()
        lat   = self._lat_i.text().strip()
        lon   = self._lon_i.text().strip()

        if not lat or not lon:
            self._msg.setStyleSheet(S(RED,8,ls=0))
            self._msg.setText("Coordonnees manquantes."); return

        if token != self._token:
            self._msg.setStyleSheet(S(RED,8,ls=0))
            self._msg.setText("Code d'autorisation invalide.")
            _log_action("TENTATIVE_ARMEMENT_ECHEC", self.login, f"Token invalide : {token}")
            return

        # Verifier le mdp
        users = DataStore.load("users.dat", {})
        u = users.get(self.login, {})
        if not DataStore.check_mdp(mdp, u.get("mdp","")):
            self._msg.setStyleSheet(S(RED,8,ls=0))
            self._msg.setText("Mot de passe incorrect.")
            _log_action("TENTATIVE_ARMEMENT_ECHEC", self.login, "Mot de passe incorrect")
            return

        # Verification niveau : N4 = site uniquement, N5 = tout
        if self.niveau == 4:
            self._msg.setStyleSheet(S(YELLOW,8,ls=0))
            self._msg.setText("Niveau 4 : frappe autorisee sur site local uniquement.")
        
        self._armed = True
        self._arm_btn.setEnabled(False)
        self._launch_btn.setEnabled(True)
        self._status_lbl.setText("SYSTEME ARME  |  EN ATTENTE DE CONFIRMATION")
        self._status_lbl.setStyleSheet(S(RED,9,bold=True,ls=2))
        self._globe.page().runJavaScript("setArmed(true);")
        self._log_msg("Systeme arme. En attente de lancement.", RED)
        _log_action("SYSTEME_ARME", self.login, f"Cible : {lat} / {lon}")

    def _launch(self):
        if not self._armed: return
        lat = self._target_lat; lon = self._target_lon
        if not lat or not lon:
            lat = self._lat_i.text().strip(); lon = self._lon_i.text().strip()

        # Confirmation finale
        box = QMessageBox(self)
        box.setWindowTitle("CONFIRMATION FINALE")
        box.setText(
            f"LANCEMENT IMMINANT\n\n"
            f"Cible : {lat} / {lon}\n"
            f"Operateur : {self.nom_affiche}\n\n"
            f"Cette action est IRREVERSIBLE.\n"
            f"Confirmer le lancement ?"
        )
        box.setStyleSheet(f"background:{BG2};color:{RED};font-family:'{MONO}';")
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.button(QMessageBox.StandardButton.Yes).setText("CONFIRMER")
        box.button(QMessageBox.StandardButton.No).setText("ANNULER")
        if box.exec() != QMessageBox.StandardButton.Yes:
            return

        # LANCEMENT
        self._globe.page().runJavaScript(f"launchAnimation('{lat}', '{lon}');")
        self._status_lbl.setText("FRAPPE EN COURS  |  VECTEUR LANCE")
        self._status_lbl.setStyleSheet(S("#cc00ff",9,bold=True,ls=2))
        self._launch_btn.setEnabled(False)
        self._log_msg(f"FRAPPE LANCEE vers {lat} / {lon}", "#cc00ff")
        _log_action("FRAPPE_LANCEE", self.login, f"Cible : {lat} / {lon}")

        # Forcer evacuation du site
        _force_evacuation(self.login)
        self._log_msg("EVACUATION DU SITE DECLENCHEE", RED)

        # Sequence de fin
        QTimer.singleShot(3000, self._post_launch)

    def _post_launch(self):
        self._status_lbl.setText("FRAPPE EXECUTEE  |  IMPACT CONFIRME")
        self._armed = False
        self._arm_btn.setEnabled(True)
        # Regenerer un nouveau token
        cfg = DataStore.load("armes_config.dat", {})
        cfg["token"] = str(random.randint(100000000, 999999999))
        DataStore.save("armes_config.dat", cfg)
        self._token = cfg["token"]
        self._log_msg(f"Nouveau token genere : {self._token}", CYAN)
        self._token_i.clear(); self._mdp_i.clear()


def main():
    app = QApplication(sys.argv); app.setStyle("Fusion"); load_barlow()
    login, niveau, nom_affiche = check_clearance("Parametres")  # utilise Params pour verif

    # Verification niveau minimum N4
    if niveau < 4:
        box = QMessageBox(); box.setWindowTitle("Acces refuse")
        box.setText(f"Niveau 4 requis minimum.\nVotre niveau : {niveau}")
        box.setStyleSheet(f"background:#0e0e0e;color:#efefef;font-family:'Courier New';")
        box.exec(); sys.exit(1)

    win = ScipnetWindow("Systeme d'Armement", login, niveau, nom_affiche, width=1200, height=750)
    widget = LaunchWidget(login, niveau, nom_affiche)
    win.set_content(widget); win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
