"""
SCiPNET — Base SCP v1.0
App standalone — nécessite une session active (session.dat)
"""
import sys, threading, urllib.request, json
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QLabel, QPushButton,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen

sys.path.insert(0, "/opt/scipnet")
from scipnet_common import (
    BG, BG2, BG3, WIN_BG, BORDER, BORDER_B,
    WHITE, DIM, DARK, CYAN, CYAN_D, RED, YELLOW, GREEN,
    MONO, NIVEAU_LABELS, NIVEAU_COLORS,
    F, S, DataStore, ScipnetWindow, check_clearance, load_barlow,
)

_SCP_API   = "https://scp-data.tedivm.com/data/scp/items/index.json"
_SCP_INDEX: dict = {}

CLASS_COLORS = {
    "safe":"#22bb44","euclid":"#f5d020","keter":"#cc3333",
    "thaumiel":"#00d4ff","neutralized":"#888888","apollyon":"#ff00ff","archon":"#ff8800",
}
CLASS_NIVEAU = {
    "SAFE":1,"NEUTRALIZED":1,"EXPLAINED":1,
    "EUCLIDE":2,"KETER":3,"THAUMIEL":4,"APOLLYON":4,"ARCHON":4,
}

def _fetch_index(callback):
    def _run():
        global _SCP_INDEX
        try:
            with urllib.request.urlopen(_SCP_API, timeout=8) as r:
                _SCP_INDEX = json.loads(r.read().decode())
            callback(True, "")
        except Exception as e:
            callback(False, str(e))
    threading.Thread(target=_run, daemon=True).start()

def _get_scp(number: str, callback):
    def _run():
        raw = number.strip()
        # Essayer plusieurs formats : scp-173, scp-049, scp-3000
        candidates = []
        if raw.isdigit():
            n = int(raw)
            candidates = [
                f"scp-{raw}",           # exact
                f"scp-{n}",             # sans zéros
                f"scp-{n:03d}",         # 3 chiffres
                f"scp-{n:04d}",         # 4 chiffres
            ]
        else:
            candidates = [f"scp-{raw}", raw]
        num = raw
        if _SCP_INDEX:
            for c in candidates:
                if c and c in _SCP_INDEX:
                    callback(_SCP_INDEX[c], None); return
            # Recherche partielle
            for key in _SCP_INDEX:
                if raw in key:
                    callback(_SCP_INDEX[key], None); return
            callback(None, f"SCP-{num} introuvable"); return
        try:
            with urllib.request.urlopen(_SCP_API, timeout=8) as r:
                idx = json.loads(r.read().decode())
            for c in candidates:
                if c and c in idx:
                    callback(idx[c], None); return
            callback(None, f"SCP-{num} introuvable")
        except Exception as e:
            callback(None, str(e))
    threading.Thread(target=_run, daemon=True).start()


class SpinnerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60,60)
        self._angle = 0
        self._timer = QTimer(self, interval=30, timeout=self._tick)
        self.hide()

    def start(self): self._timer.start(); self.show()
    def stop(self):  self._timer.stop();  self.hide()
    def _tick(self): self._angle = (self._angle + 8) % 360; self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(RED), 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(8, 8, 44, 44, self._angle*16, 270*16)


class ScpDatabaseWidget(QWidget):
    def __init__(self, login: str, niveau: int, parent=None):
        super().__init__(parent)
        self.login  = login
        self.niveau = niveau
        self._build()
        self._load_index()

    def _build(self):
        self.setStyleSheet(f"background:{WIN_BG};")
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        # Barre recherche
        bar = QWidget(); bar.setFixedHeight(52)
        bar.setStyleSheet(f"background:{BG2};border-bottom:1px solid {BORDER};")
        h = QHBoxLayout(bar); h.setContentsMargins(16,0,16,0); h.setSpacing(10)

        h.addWidget(QLabel("◈  SCP N°", styleSheet=S(DIM,9,bold=True,ls=2)))

        self.inp = QLineEdit()
        self.inp.setPlaceholderText("173  /  682  /  049  …")
        self.inp.setFixedWidth(180)
        self.inp.setStyleSheet(
            f"QLineEdit{{background:{BG3};color:{WHITE};font-family:'{MONO}';"
            f"font-size:13px;border:1px solid {BORDER_B};padding:4px 10px;}}"
            f"QLineEdit:focus{{border:1px solid {CYAN};}}"
        )
        pal = self.inp.palette()
        pal.setColor(pal.ColorRole.Text, QColor(WHITE))
        pal.setColor(pal.ColorRole.Base, QColor(BG3))
        self.inp.setPalette(pal)
        self.inp.setFont(F(13))
        self.inp.returnPressed.connect(self._search)

        btn = QPushButton("RECHERCHER")
        btn.setStyleSheet(
            f"QPushButton{{background:{BG3};color:{CYAN};font-family:'{MONO}';"
            f"font-size:9px;font-weight:600;letter-spacing:2px;padding:6px 16px;"
            f"border:1px solid {BORDER_B};}}"
            f"QPushButton:hover{{background:{CYAN};color:{BG};}}"
        )
        btn.clicked.connect(self._search)

        self.status = QLabel("Connexion à l'index…")
        self.status.setStyleSheet(S(DIM,8,ls=1))

        h.addWidget(self.inp); h.addWidget(btn); h.addStretch(); h.addWidget(self.status)
        root.addWidget(bar)

        # Zone résultat
        self.result = QTextEdit(); self.result.setReadOnly(True)
        self.result.setStyleSheet(
            f"background:{WIN_BG};color:{WHITE};font-family:'{MONO}';"
            f"font-size:11px;border:none;padding:20px;"
        )
        self.result.setFont(F(11))
        self._placeholder()

        self._spinner = SpinnerWidget(self.result)
        root.addWidget(self.result, 1)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        ra = self.result
        self._spinner.move((ra.width()-60)//2, max((ra.height()-60)//2, 20))

    def _placeholder(self):
        self.result.setHtml(
            f"<div style='color:{DIM};font-family:{MONO};font-size:11px;"
            f"text-align:center;margin-top:80px;'>"
            f"Entrez un numéro de SCP pour consulter son dossier.<br><br>"
            f"<span style='color:{DARK};'>Exemples : 173, 682, 049, 096, 3000</span></div>"
        )

    def _load_index(self):
        def _cb(ok, err):
            if ok:
                self.status.setText(f"Index chargé — {len(_SCP_INDEX)} articles")
                self.status.setStyleSheet(S(GREEN,8,ls=1))
            else:
                self.status.setText(f"Hors ligne — {err[:40]}")
                self.status.setStyleSheet(S(RED,8,ls=1))
        _fetch_index(_cb)

    def _search(self):
        num = self.inp.text().strip()
        if not num: return
        self._spinner.start()
        self.result.setHtml(
            f"<div style='color:{DIM};font-family:{MONO};font-size:11px;margin-top:60px;'>"
            f"Interrogation de l'archive SCP-{num}…</div>"
        )
        _get_scp(num, lambda data, err: QTimer.singleShot(0, lambda: self._display(num, data, err)))

    def _display(self, num, data, err):
        self._spinner.stop()
        if err or not data:
            self.result.setHtml(
                f"<div style='font-family:{MONO};font-size:11px;'>"
                f"<span style='color:{RED};'>SCP-{num} : {err or 'introuvable'}</span></div>"
            ); return

        title   = data.get("title","[ TITRE REDACTED ]")
        tags    = data.get("tags",[])
        rating  = data.get("rating","?")
        scp_id  = data.get("scp",f"SCP-{num}")
        url     = data.get("url","")
        series  = data.get("series","?")
        created = (data.get("created_at","") or "")[:10] or "?"

        obj_class = "inconnu"; class_col = DIM
        for tag in tags:
            if tag.lower() in CLASS_COLORS:
                obj_class = tag.lower().upper()
                if obj_class == "EUCLID": obj_class = "EUCLIDE"
                class_col = CLASS_COLORS[tag.lower()]; break

        req = CLASS_NIVEAU.get(obj_class, 1)
        if self.niveau < req:
            import random; rng = random.Random(hash(num))
            redacted = "<br>".join(f"<span style='color:{DARK};'>{'█'*rng.randint(12,55)}</span>" for _ in range(15))
            self.result.setHtml(
                f"<div style='font-family:{MONO};font-size:11px;line-height:1.8;'>"
                f"<span style='color:{DIM};font-size:9px;letter-spacing:3px;'>DOSSIER SCiPNET</span><br>"
                f"<hr style='border:1px solid {BORDER};'>"
                f"<span style='color:{RED};font-size:18px;font-weight:600;'>⊘  ACCÈS REFUSÉ</span><br><br>"
                f"<span style='color:{DIM};'>Classe : </span><span style='color:{class_col};font-weight:600;'>{obj_class}</span><br>"
                f"<span style='color:{DIM};'>Niveau requis : </span><span style='color:{WHITE};'>{req} — {NIVEAU_LABELS.get(req,'?')}</span><br>"
                f"<span style='color:{DIM};'>Votre niveau  : </span><span style='color:{RED};'>{self.niveau} — {NIVEAU_LABELS.get(self.niveau,'?')}</span>"
                f"<hr style='border:1px solid {BORDER};'>{redacted}</div>"
            ); return

        filtered_tags = [t for t in tags if t.lower() not in CLASS_COLORS][:12]
        tags_html = " ".join(
            f"<span style='background:{BORDER};color:{DIM};padding:1px 5px;border-radius:2px;font-size:9px;'>{t}</span>"
            for t in filtered_tags
        )

        self.result.setHtml(f"""
<div style='font-family:{MONO};font-size:11px;line-height:1.8;'>
<span style='color:{DIM};font-size:9px;letter-spacing:3px;'>DOSSIER SCiPNET — NIVEAU {NIVEAU_LABELS.get(req,'?')}</span><br>
<hr style='border:1px solid {BORDER};margin:8px 0;'>
<span style='color:{WHITE};font-size:20px;font-weight:600;letter-spacing:2px;'>{scp_id}</span><br>
<span style='color:{DIM};font-size:13px;'>{title}</span><br><br>
<span style='color:{DIM};font-size:9px;letter-spacing:2px;'>CLASSE DE CONFINEMENT</span><br>
<span style='color:{class_col};font-size:18px;font-weight:600;letter-spacing:3px;'>{obj_class}</span><br><br>
<table style='color:{DIM};font-size:10px;'>
<tr><td style='padding:2px 20px 2px 0;color:{WHITE};'>SÉRIE</td><td>{series}</td></tr>
<tr><td style='padding:2px 20px 2px 0;color:{WHITE};'>CRÉÉ</td><td>{created}</td></tr>
<tr><td style='padding:2px 20px 2px 0;color:{WHITE};'>RATING</td><td style='color:{YELLOW};'>+{rating}</td></tr>
</table><br>
<span style='color:{DIM};font-size:9px;letter-spacing:2px;'>TAGS</span><br>
{tags_html}<br><br>
<span style='color:{DIM};font-size:9px;'>LIEN WIKI</span><br>
<span style='color:{CYAN};'>→ {url}</span>
</div>""")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    load_barlow()
    login, niveau, nom_affiche = check_clearance("Base SCP")
    win = ScipnetWindow("Base de Données SCP", login, niveau, nom_affiche, width=900, height=620)
    widget = ScpDatabaseWidget(login, niveau)
    win.set_content(widget)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
