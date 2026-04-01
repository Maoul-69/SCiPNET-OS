"""
SCiPNET — Personnel v1.0
App standalone — nécessite une session active (session.dat)
"""
import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QScrollArea,
    QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QColor, QDrag

sys.path.insert(0, "/opt/scipnet")
from scipnet_common import (
    BG, BG2, BG3, WIN_BG, BORDER, BORDER_B,
    WHITE, DIM, DARK, CYAN, CYAN_D, RED, YELLOW, GREEN,
    MONO, NIVEAU_LABELS, NIVEAU_COLORS,
    F, S, hsep, DataStore, ScipnetWindow, check_clearance, load_barlow,
)

ETATS = ["NOMINAL","ALERTE","RISQUE ÉLEVÉ","CONFINEMENT","ÉVACUATION"]
ETAT_COLORS = {
    "NOMINAL":"#22bb44","ALERTE":"#f5d020",
    "RISQUE ÉLEVÉ":"#ff8800","CONFINEMENT":"#cc3333","ÉVACUATION":"#cc00ff",
}

def _load_personnel():
    cfg = DataStore.load("config.dat", {})
    return cfg.get("personnel", [
        {"id":"sec","nom":"Sécurité",      "role":"MTF / Gardiens",    "effectif":42,"max":60, "etat":"NOMINAL"},
        {"id":"sci","nom":"Recherche",     "role":"Chercheurs",        "effectif":31,"max":40, "etat":"NOMINAL"},
        {"id":"med","nom":"Médical",       "role":"Médecins / Infirm.","effectif":14,"max":20, "etat":"NOMINAL"},
        {"id":"eng","nom":"Génie",         "role":"Techniciens",       "effectif":18,"max":25, "etat":"NOMINAL"},
        {"id":"adm","nom":"Administration","role":"Agents admin.",     "effectif": 8,"max":12, "etat":"NOMINAL"},
        {"id":"dcl","nom":"Classe-D",      "role":"Sujets de test",   "effectif":23,"max":50, "etat":"NOMINAL"},
    ])

def _save_personnel(data: list):
    cfg = DataStore.load("config.dat", {})
    cfg["personnel"] = data
    DataStore.save("config.dat", cfg)


class DeptCard(QFrame):
    changed  = pyqtSignal()
    deleted  = pyqtSignal(object)
    drag_start = pyqtSignal(object)

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.data = data
        self.setStyleSheet(
            f"QFrame{{background:{BG2};border:1px solid {BORDER};"
            f"border-radius:3px;margin:2px 0;}}"
        )
        self._build()

    def _build(self):
        v = QVBoxLayout(self); v.setContentsMargins(0,0,0,0); v.setSpacing(0)

        # En-tête
        hdr = QWidget(); hdr.setFixedHeight(36)
        hdr.setStyleSheet(f"background:{BG3};border-bottom:1px solid {BORDER};")
        hh = QHBoxLayout(hdr); hh.setContentsMargins(10,0,10,0); hh.setSpacing(8)

        # Poignée drag
        grip = QLabel("⠿")
        grip.setStyleSheet(f"color:{DARK};font-size:16px;background:transparent;cursor:move;")
        grip.setCursor(Qt.CursorShape.SizeAllCursor)
        hh.addWidget(grip)

        # Nom éditable
        from PyQt6.QtWidgets import QLineEdit
        self._nom = QLineEdit(self.data.get("nom",""))
        self._nom.setStyleSheet(
            f"QLineEdit{{background:transparent;color:{WHITE};font-family:'{MONO}';"
            f"font-size:11px;font-weight:600;border:none;padding:0;}}"
            f"QLineEdit:focus{{border-bottom:1px solid {CYAN};}}"
        )
        pal = self._nom.palette()
        pal.setColor(pal.ColorRole.Text, QColor(WHITE))
        pal.setColor(pal.ColorRole.Base, QColor(BG3))
        self._nom.setPalette(pal)
        self._nom.setFont(F(11, bold=True))
        self._nom.textChanged.connect(lambda t: (self.data.update({"nom":t}), self.changed.emit()))
        hh.addWidget(self._nom, 1)

        # Bouton supprimer
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(22,22)
        del_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{DARK};font-size:12px;border:none;}}"
            f"QPushButton:hover{{color:{RED};}}"
        )
        del_btn.clicked.connect(lambda: self.deleted.emit(self))
        hh.addWidget(del_btn); v.addWidget(hdr)

        # Corps
        body = QWidget(); body.setStyleSheet(f"background:transparent;")
        bv = QVBoxLayout(body); bv.setContentsMargins(12,10,12,10); bv.setSpacing(8)

        # Rôle
        from PyQt6.QtWidgets import QLineEdit as QL2
        role_row = QHBoxLayout()
        role_row.addWidget(QLabel("Rôle", styleSheet=S(DIM,9,ls=1)))
        self._role = QL2(self.data.get("role",""))
        self._role.setStyleSheet(
            f"QLineEdit{{background:{BG3};color:{DIM};font-family:'{MONO}';"
            f"font-size:9px;border:1px solid {BORDER};padding:2px 6px;}}"
        )
        pal2 = self._role.palette()
        pal2.setColor(pal2.ColorRole.Text, QColor(DIM))
        pal2.setColor(pal2.ColorRole.Base, QColor(BG3))
        self._role.setPalette(pal2)
        self._role.textChanged.connect(lambda t: (self.data.update({"role":t}), self.changed.emit()))
        role_row.addWidget(self._role, 1); bv.addLayout(role_row)

        # Effectif
        eff_row = QHBoxLayout()
        eff_row.addWidget(QLabel("Effectif", styleSheet=S(DIM,9,ls=1)))
        self._eff = QSpinBox(); self._eff.setRange(0,9999)
        self._eff.setValue(self.data.get("effectif",0))
        self._eff.setStyleSheet(
            f"QSpinBox{{background:{BG3};color:{WHITE};font-family:'{MONO}';"
            f"font-size:10px;border:1px solid {BORDER};padding:2px 6px;}}"
        )
        self._eff.valueChanged.connect(lambda v: (self.data.update({"effectif":v}), self._update_bar(), self.changed.emit()))
        eff_row.addWidget(self._eff)
        eff_row.addWidget(QLabel("/", styleSheet=S(DIM,9,ls=0)))
        self._max = QSpinBox(); self._max.setRange(1,9999)
        self._max.setValue(self.data.get("max",1))
        self._max.setStyleSheet(self._eff.styleSheet())
        self._max.valueChanged.connect(lambda v: (self.data.update({"max":v}), self._update_bar(), self.changed.emit()))
        eff_row.addWidget(self._max); eff_row.addStretch(); bv.addLayout(eff_row)

        # Barre capacité
        self._bar_bg = QFrame(); self._bar_bg.setFixedHeight(4)
        self._bar_bg.setStyleSheet(f"background:{BORDER};border-radius:2px;")
        self._bar = QFrame(self._bar_bg); self._bar.setFixedHeight(4)
        self._bar.setStyleSheet(f"background:{GREEN};border-radius:2px;")
        bv.addWidget(self._bar_bg)
        self._update_bar()

        # État
        etat_row = QHBoxLayout()
        etat_row.addWidget(QLabel("État", styleSheet=S(DIM,9,ls=1)))
        self._etat = QComboBox()
        self._etat.addItems(ETATS)
        self._etat.setCurrentText(self.data.get("etat","NOMINAL"))
        self._etat.setStyleSheet(
            f"QComboBox{{background:{BG3};color:{WHITE};font-family:'{MONO}';"
            f"font-size:9px;border:1px solid {BORDER};padding:2px 6px;}}"
            f"QComboBox QAbstractItemView{{background:{BG2};color:{WHITE};"
            f"border:1px solid {BORDER};selection-background-color:{CYAN_D};}}"
        )
        self._etat.currentTextChanged.connect(lambda t: (self.data.update({"etat":t}), self._update_etat_color(), self.changed.emit()))
        etat_row.addWidget(self._etat,1)
        self._etat_dot = QLabel("●")
        self._etat_dot.setStyleSheet(f"color:{ETAT_COLORS.get(self.data.get('etat','NOMINAL'),GREEN)};font-size:10px;background:transparent;")
        etat_row.addWidget(self._etat_dot); bv.addLayout(etat_row)

        v.addWidget(body)

    def _update_bar(self):
        eff = self._eff.value(); mx = max(self._max.value(),1)
        ratio = min(eff/mx, 1.0)
        width = max(int(ratio * (self._bar_bg.width() or 200)), 4)
        self._bar.setFixedWidth(width)
        col = GREEN if ratio < 0.75 else (YELLOW if ratio < 0.9 else RED)
        self._bar.setStyleSheet(f"background:{col};border-radius:2px;")

    def _update_etat_color(self):
        col = ETAT_COLORS.get(self._etat.currentText(), GREEN)
        self._etat_dot.setStyleSheet(f"color:{col};font-size:10px;background:transparent;")

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._update_bar()


class PersonnelWidget(QWidget):
    def __init__(self, login: str, niveau: int, parent=None):
        super().__init__(parent)
        self.login   = login
        self.niveau  = niveau
        self._personnel = _load_personnel()
        self._cards: list[DeptCard] = []
        self._build()

    def _build(self):
        self.setStyleSheet(f"background:{WIN_BG};")
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        # Barre stats globale
        self._stats_bar = QWidget(); self._stats_bar.setFixedHeight(40)
        self._stats_bar.setStyleSheet(f"background:{BG2};border-bottom:1px solid {BORDER};")
        sh = QHBoxLayout(self._stats_bar); sh.setContentsMargins(16,0,16,0); sh.setSpacing(20)
        self._total_lbl = QLabel(); self._total_lbl.setStyleSheet(S(WHITE,9,ls=1))
        self._etat_lbl  = QLabel(); self._etat_lbl.setStyleSheet(S(GREEN,9,ls=1))
        sh.addWidget(self._total_lbl); sh.addWidget(self._etat_lbl); sh.addStretch()
        add_btn = QPushButton("+ AJOUTER MODULE")
        add_btn.setStyleSheet(
            f"QPushButton{{background:{BG3};color:{CYAN};font-family:'{MONO}';"
            f"font-size:9px;letter-spacing:2px;padding:5px 12px;border:1px solid {BORDER_B};}}"
            f"QPushButton:hover{{background:{CYAN};color:{BG};}}"
        )
        add_btn.clicked.connect(self._add_dept)
        sh.addWidget(add_btn); root.addWidget(self._stats_bar)

        # Zone scrollable
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea{{border:none;background:{WIN_BG};}}"
                             f"QScrollBar:vertical{{background:{BG2};width:6px;}}"
                             f"QScrollBar::handle:vertical{{background:{BORDER_B};border-radius:3px;}}")
        inner = QWidget(); inner.setStyleSheet(f"background:{WIN_BG};")
        self._cards_lay = QVBoxLayout(inner)
        self._cards_lay.setContentsMargins(16,16,16,16); self._cards_lay.setSpacing(8)
        self._cards_lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        for dept in self._personnel:
            self._add_card(dept)

        self._cards_lay.addStretch()
        scroll.setWidget(inner); root.addWidget(scroll, 1)
        self._update_stats()

    def _add_card(self, data: dict):
        card = DeptCard(data)
        card.changed.connect(self._on_change)
        card.deleted.connect(self._delete_card)
        self._cards_lay.insertWidget(self._cards_lay.count()-1, card)
        self._cards.append(card)

    def _add_dept(self):
        import random
        new_id = f"dept_{random.randint(1000,9999)}"
        data = {"id":new_id,"nom":"Nouveau Département","role":"Rôle",
                "effectif":0,"max":10,"etat":"NOMINAL"}
        self._personnel.append(data)
        self._add_card(data)
        self._on_change()

    def _delete_card(self, card: DeptCard):
        if card.data in self._personnel:
            self._personnel.remove(card.data)
        if card in self._cards:
            self._cards.remove(card)
        card.deleteLater()
        self._on_change()

    def _on_change(self):
        _save_personnel(self._personnel)
        self._update_stats()

    def _update_stats(self):
        total   = sum(d.get("effectif",0) for d in self._personnel)
        max_tot = sum(d.get("max",0) for d in self._personnel)
        etats   = [d.get("etat","NOMINAL") for d in self._personnel]
        priority = ["ÉVACUATION","CONFINEMENT","RISQUE ÉLEVÉ","ALERTE","NOMINAL"]
        getat   = next((e for e in priority if e in etats), "NOMINAL")
        gcol    = ETAT_COLORS.get(getat, GREEN)
        self._total_lbl.setText(f"PERSONNEL : {total} / {max_tot}")
        self._etat_lbl.setText(f"ÉTAT : {getat}")
        self._etat_lbl.setStyleSheet(f"color:{gcol};font-family:'{MONO}';font-size:9px;letter-spacing:1px;background:transparent;")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    load_barlow()
    login, niveau, nom_affiche = check_clearance("Personnel")
    win = ScipnetWindow("Personnel", login, niveau, nom_affiche, width=800, height=650)
    widget = PersonnelWidget(login, niveau)
    win.set_content(widget)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
