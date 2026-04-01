"""
SCiPNET — Site Map v1.0
App standalone — nécessite une session active (session.dat)
Fonctionnalités :
  - Choix du style de site (industriel, souterrain, arctique, désertique)
  - Carte interactive avec salles personnalisées
  - Glisser-déposer pour placer les modules
  - Clic droit pour supprimer/renommer
"""
import sys, json, random, math
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QFrame, QScrollArea,
    QDialog, QLineEdit, QSplitter, QListWidget, QListWidgetItem,
    QInputDialog, QMenu,
)
from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, pyqtSignal, QSize
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush, QFont,
    QPainterPath, QLinearGradient, QRadialGradient,
)

sys.path.insert(0, "/opt/scipnet")
from scipnet_common import (
    BG, BG2, BG3, WIN_BG, BORDER, BORDER_B,
    WHITE, DIM, DARK, CYAN, CYAN_D, RED, YELLOW, GREEN,
    MONO, NIVEAU_LABELS, NIVEAU_COLORS,
    F, S, DataStore, ScipnetWindow, check_clearance, load_barlow,
)

# ══════════════════════════════════════════════════════════════════════════════
#  STYLES DE SITE
# ══════════════════════════════════════════════════════════════════════════════
SITE_STYLES = {
    "Industriel": {
        "bg_color"   : "#0a0a0f",
        "grid_color" : "#1a1a2e",
        "room_bg"    : "#0d1117",
        "room_border": "#2a4a7a",
        "accent"     : "#00d4ff",
        "desc"       : "Structure en acier et béton. Éclairage fluorescent.",
    },
    "Souterrain": {
        "bg_color"   : "#050a05",
        "grid_color" : "#0d1a0d",
        "room_bg"    : "#0a120a",
        "room_border": "#2a5a2a",
        "accent"     : "#22bb44",
        "desc"       : "Excavation profonde. Roche et béton renforcé.",
    },
    "Arctique": {
        "bg_color"   : "#050a12",
        "grid_color" : "#0d1a2e",
        "room_bg"    : "#080f1a",
        "room_border": "#3a5a8a",
        "accent"     : "#88ccff",
        "desc"       : "Installation polaire. Isolation thermique renforcée.",
    },
    "Désertique": {
        "bg_color"   : "#120a05",
        "grid_color" : "#1e1205",
        "room_bg"    : "#140e06",
        "room_border": "#6a4a1a",
        "accent"     : "#f5a020",
        "desc"       : "Base enterrée sous le sable. Chaleur extrême.",
    },
    "Maritime": {
        "bg_color"   : "#050a12",
        "grid_color" : "#081220",
        "room_bg"    : "#060e1a",
        "room_border": "#1a4a6a",
        "accent"     : "#0088cc",
        "desc"       : "Plateforme offshore. Résistance à la corrosion.",
    },
    "Orbital": {
        "bg_color"   : "#020205",
        "grid_color" : "#0a0a15",
        "room_bg"    : "#050510",
        "room_border": "#3a2a6a",
        "accent"     : "#cc44ff",
        "desc"       : "Station spatiale. Gravité artificielle.",
    },
}

# Types de salles disponibles
ROOM_TYPES = {
    "Confinement"    : {"icon": "⊠", "color": "#cc3333"},
    "Recherche"      : {"icon": "⚗", "color": "#00d4ff"},
    "Sécurité"       : {"icon": "⊕", "color": "#f5d020"},
    "Médical"        : {"icon": "✚", "color": "#22bb44"},
    "Administration" : {"icon": "◈", "color": "#6a6a6a"},
    "Génie"          : {"icon": "⚙", "color": "#ff8800"},
    "Classe-D"       : {"icon": "◉", "color": "#883333"},
    "Armurerie"      : {"icon": "⊗", "color": "#cc5500"},
    "Centrale"       : {"icon": "⚡", "color": "#ffdd00"},
    "Archives"       : {"icon": "📋", "color": "#5588aa"},
    "Cafétéria"      : {"icon": "☕", "color": "#886644"},
    "Entrée"         : {"icon": "▷",  "color": "#44aa44"},
}

# ══════════════════════════════════════════════════════════════════════════════
#  SALLE (donnée)
# ══════════════════════════════════════════════════════════════════════════════
class Room:
    def __init__(self, x: int, y: int, w: int = 120, h: int = 80,
                 name: str = "Salle", room_type: str = "Recherche", room_id: str = ""):
        self.x    = x
        self.y    = y
        self.w    = w
        self.h    = h
        self.name = name
        self.type = room_type
        self.id   = room_id or f"room_{random.randint(1000,9999)}"

    def rect(self) -> QRect:
        return QRect(self.x, self.y, self.w, self.h)

    def contains(self, px: int, py: int) -> bool:
        return self.rect().contains(px, py)

    def to_dict(self) -> dict:
        return {"id":self.id,"x":self.x,"y":self.y,"w":self.w,"h":self.h,
                "name":self.name,"type":self.type}

    @classmethod
    def from_dict(cls, d: dict) -> "Room":
        return cls(d["x"],d["y"],d.get("w",120),d.get("h",80),
                   d.get("name","Salle"),d.get("type","Recherche"),d.get("id",""))


# ══════════════════════════════════════════════════════════════════════════════
#  CANVAS DE LA CARTE
# ══════════════════════════════════════════════════════════════════════════════
class MapCanvas(QWidget):
    room_selected  = pyqtSignal(object)   # Room | None
    rooms_changed  = pyqtSignal()

    GRID = 20  # taille de la grille en pixels

    def __init__(self, style_name: str = "Industriel", parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._style_name = style_name
        self._style      = SITE_STYLES[style_name]
        self._rooms: list[Room] = []
        self._selected: Room | None = None
        self._drag_room: Room | None = None
        self._drag_offset = QPoint()
        self._resize_room: Room | None = None
        self._resize_corner = ""
        self._placing_type: str | None = None   # type en cours de placement

        # Décoration : labels et connexions
        self._show_grid    = True
        self._show_labels  = True

        self.setStyleSheet(f"background:{self._style['bg_color']};")

    def set_style(self, style_name: str):
        self._style_name = style_name
        self._style = SITE_STYLES[style_name]
        self.setStyleSheet(f"background:{self._style['bg_color']};")
        self.update()

    def set_placing(self, room_type: str | None):
        """Active le mode placement d'une salle."""
        self._placing_type = room_type
        if room_type:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def snap(self, v: int) -> int:
        return round(v / self.GRID) * self.GRID

    # ── Dessin ────────────────────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        st = self._style

        # Fond
        p.fillRect(self.rect(), QColor(st["bg_color"]))

        # Grille
        if self._show_grid:
            p.setPen(QPen(QColor(st["grid_color"]), 1))
            for x in range(0, self.width(), self.GRID):
                p.drawLine(x, 0, x, self.height())
            for y in range(0, self.height(), self.GRID):
                p.drawLine(0, y, self.width(), y)

        # Connexions entre salles (lignes simples)
        p.setPen(QPen(QColor(st["accent"]).darker(200), 1, Qt.PenStyle.DotLine))
        centers = [(r.x + r.w//2, r.y + r.h//2) for r in self._rooms]
        for i in range(len(centers)-1):
            p.drawLine(centers[i][0], centers[i][1], centers[i+1][0], centers[i+1][1])

        # Salles
        for room in self._rooms:
            self._draw_room(p, room, room is self._selected)

        p.end()

    def _draw_room(self, p: QPainter, room: Room, selected: bool):
        st     = self._style
        rtype  = ROOM_TYPES.get(room.type, ROOM_TYPES["Recherche"])
        accent = rtype["color"]
        icon   = rtype["icon"]
        r      = room.rect()

        # Fond de la salle
        p.fillRect(r, QColor(st["room_bg"]))

        # Bordure
        border_col = accent if selected else st["room_border"]
        pen = QPen(QColor(border_col), 2 if selected else 1)
        p.setPen(pen)
        p.drawRect(r)

        # Coin coloré (indicateur de type)
        corner = QRect(r.x(), r.y(), 6, r.height())
        p.fillRect(corner, QColor(accent))

        if self._show_labels:
            # Icône
            p.setPen(QColor(accent))
            p.setFont(QFont(MONO, 14))
            icon_rect = QRect(r.x()+12, r.y()+4, 24, 24)
            p.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, icon)

            # Nom
            p.setPen(QColor(WHITE))
            p.setFont(QFont(MONO, 8))
            name_rect = QRect(r.x()+12, r.y()+26, r.width()-20, r.height()-32)
            p.drawText(name_rect,
                       Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                       room.name)

            # Type
            p.setPen(QColor(accent).darker(120))
            p.setFont(QFont(MONO, 7))
            type_rect = QRect(r.x()+12, r.y()+r.height()-16, r.width()-16, 14)
            p.drawText(type_rect,
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       room.type.upper())

        # Poignée de redimensionnement (coin bas-droit)
        if selected:
            handle = QRect(r.right()-8, r.bottom()-8, 8, 8)
            p.fillRect(handle, QColor(accent))

    # ── Interactions souris ───────────────────────────────────────────────────
    def mousePressEvent(self, e):
        x, y = e.position().x(), e.position().y()

        if e.button() == Qt.MouseButton.RightButton:
            self._right_click(int(x), int(y), e.globalPosition().toPoint())
            return

        if e.button() == Qt.MouseButton.LeftButton:
            # Mode placement
            if self._placing_type:
                sx, sy = self.snap(int(x)-60), self.snap(int(y)-40)
                room = Room(sx, sy, 120, 80,
                            f"Salle {len(self._rooms)+1}",
                            self._placing_type)
                self._rooms.append(room)
                self._selected = room
                self.room_selected.emit(room)
                self.rooms_changed.emit()
                self._save()
                self.update()
                return

            # Sélection / drag
            clicked = self._room_at(int(x), int(y))
            if clicked:
                # Vérifier si c'est la poignée de resize
                r = clicked.rect()
                handle = QRect(r.right()-10, r.bottom()-10, 10, 10)
                if handle.contains(int(x), int(y)):
                    self._resize_room   = clicked
                    self._resize_corner = "br"
                else:
                    self._drag_room   = clicked
                    self._drag_offset = QPoint(int(x)-clicked.x, int(y)-clicked.y)
                self._selected = clicked
                self.room_selected.emit(clicked)
            else:
                self._selected = None
                self.room_selected.emit(None)
            self.update()

    def mouseMoveEvent(self, e):
        x, y = int(e.position().x()), int(e.position().y())
        if self._drag_room:
            self._drag_room.x = self.snap(x - self._drag_offset.x())
            self._drag_room.y = self.snap(y - self._drag_offset.y())
            self.update()
        elif self._resize_room:
            r = self._resize_room
            r.w = max(80, self.snap(x - r.x))
            r.h = max(60, self.snap(y - r.y))
            self.update()

    def mouseReleaseEvent(self, e):
        if self._drag_room or self._resize_room:
            self.rooms_changed.emit()
            self._save()
        self._drag_room   = None
        self._resize_room = None

    def mouseDoubleClickEvent(self, e):
        x, y = int(e.position().x()), int(e.position().y())
        room = self._room_at(x, y)
        if room:
            name, ok = QInputDialog.getText(self, "Renommer", "Nom de la salle :", text=room.name)
            if ok and name.strip():
                room.name = name.strip()
                self.rooms_changed.emit()
                self._save()
                self.update()

    def _right_click(self, x: int, y: int, gpos: QPoint):
        room = self._room_at(x, y)
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{BG2};color:{WHITE};font-family:'{MONO}';font-size:10px;"
            f"border:1px solid {BORDER_B};}}"
            f"QMenu::item{{padding:6px 20px;}}"
            f"QMenu::item:selected{{background:{BORDER_B};}}"
        )
        if room:
            rename_act = menu.addAction("✏  Renommer")
            menu.addSeparator()
            # Sous-menu type
            type_menu = menu.addMenu("⚙  Changer le type")
            type_menu.setStyleSheet(menu.styleSheet())
            for t in ROOM_TYPES:
                a = type_menu.addAction(f"{ROOM_TYPES[t]['icon']}  {t}")
                a.setData(("type", t))
            menu.addSeparator()
            del_act = menu.addAction("✕  Supprimer")
        else:
            menu.addAction("Clic gauche : sélectionner/déplacer").setEnabled(False)
            menu.addAction("Double-clic : renommer").setEnabled(False)

        action = menu.exec(gpos)
        if action and room:
            if action.text().startswith("✕"):
                self._rooms.remove(room)
                if self._selected is room:
                    self._selected = None
                    self.room_selected.emit(None)
                self.rooms_changed.emit(); self._save(); self.update()
            elif action.text().startswith("✏"):
                name, ok = QInputDialog.getText(self, "Renommer", "Nom :", text=room.name)
                if ok and name.strip():
                    room.name = name.strip()
                    self.rooms_changed.emit(); self._save(); self.update()
            elif action.data() and action.data()[0] == "type":
                room.type = action.data()[1]
                self.rooms_changed.emit(); self._save(); self.update()

    def _room_at(self, x: int, y: int) -> Room | None:
        for room in reversed(self._rooms):
            if room.contains(x, y):
                return room
        return None

    # ── Persistance ───────────────────────────────────────────────────────────
    def _save(self):
        DataStore.save("sitemap.dat", {
            "style": self._style_name,
            "rooms": [r.to_dict() for r in self._rooms],
        })

    def load(self):
        data = DataStore.load("sitemap.dat", None)
        if data:
            self._style_name = data.get("style", "Industriel")
            self._style = SITE_STYLES.get(self._style_name, SITE_STYLES["Industriel"])
            self.setStyleSheet(f"background:{self._style['bg_color']};")
            self._rooms = [Room.from_dict(d) for d in data.get("rooms", [])]
        else:
            self._add_default_rooms()

    def _add_default_rooms(self):
        """Salles par défaut pour un nouveau site."""
        defaults = [
            (40,  40,  160, 80,  "Entrée principale",   "Entrée"),
            (240, 40,  120, 80,  "Poste de sécurité",   "Sécurité"),
            (40,  160, 200, 100, "Zone de confinement", "Confinement"),
            (280, 160, 160, 100, "Laboratoire A",       "Recherche"),
            (40,  300, 120, 80,  "Infirmerie",          "Médical"),
            (200, 300, 140, 80,  "Salle de contrôle",   "Administration"),
            (380, 300, 100, 80,  "Centrale",            "Centrale"),
        ]
        for x,y,w,h,name,t in defaults:
            self._rooms.append(Room(x,y,w,h,name,t))


# ══════════════════════════════════════════════════════════════════════════════
#  PANNEAU LATÉRAL
# ══════════════════════════════════════════════════════════════════════════════
class SidePanel(QWidget):
    place_room  = pyqtSignal(str)
    style_changed = pyqtSignal(str)
    toggle_grid   = pyqtSignal(bool)
    toggle_labels = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setStyleSheet(f"background:{BG2};border-right:1px solid {BORDER};")
        self._build()

    def _build(self):
        v = QVBoxLayout(self); v.setContentsMargins(0,0,0,0); v.setSpacing(0)

        # ── Style du site ─────────────────────────────────────────────────────
        hdr = QLabel("  STYLE DU SITE")
        hdr.setStyleSheet(f"color:{DIM};font-family:'{MONO}';font-size:8px;"
                          f"letter-spacing:3px;padding:12px 12px 6px;background:{BG3};")
        v.addWidget(hdr)

        self._style_combo = QComboBox()
        self._style_combo.addItems(list(SITE_STYLES.keys()))
        self._style_combo.setStyleSheet(
            f"QComboBox{{background:{BG3};color:{WHITE};font-family:'{MONO}';"
            f"font-size:10px;border:none;border-bottom:1px solid {BORDER};padding:8px 12px;}}"
            f"QComboBox QAbstractItemView{{background:{BG2};color:{WHITE};"
            f"border:1px solid {BORDER};selection-background-color:{CYAN_D};}}"
        )
        self._style_combo.currentTextChanged.connect(self._on_style)
        v.addWidget(self._style_combo)

        self._style_desc = QLabel("")
        self._style_desc.setWordWrap(True)
        self._style_desc.setStyleSheet(f"color:{DARK};font-family:'{MONO}';font-size:8px;"
                                        f"padding:6px 12px;background:{BG3};")
        v.addWidget(self._style_desc)
        self._on_style(self._style_combo.currentText())

        sep1 = QFrame(); sep1.setFixedHeight(1)
        sep1.setStyleSheet(f"background:{BORDER};"); v.addWidget(sep1)

        # ── Modules à placer ─────────────────────────────────────────────────
        hdr2 = QLabel("  AJOUTER UNE SALLE")
        hdr2.setStyleSheet(f"color:{DIM};font-family:'{MONO}';font-size:8px;"
                           f"letter-spacing:3px;padding:12px 12px 6px;background:transparent;")
        v.addWidget(hdr2)

        self._active_btn: QPushButton | None = None
        for rtype, info in ROOM_TYPES.items():
            btn = QPushButton(f"  {info['icon']}  {rtype}")
            btn.setCheckable(True)
            btn.setStyleSheet(
                f"QPushButton{{background:transparent;color:{DIM};font-family:'{MONO}';"
                f"font-size:10px;text-align:left;padding:7px 14px;border:none;"
                f"border-left:3px solid transparent;}}"
                f"QPushButton:hover{{color:{WHITE};background:{BG3};}}"
                f"QPushButton:checked{{color:{info['color']};background:{BG3};"
                f"border-left:3px solid {info['color']};}}"
            )
            btn.clicked.connect(lambda _, t=rtype, b=btn: self._on_place(t, b))
            v.addWidget(btn)

        v.addStretch()
        sep2 = QFrame(); sep2.setFixedHeight(1)
        sep2.setStyleSheet(f"background:{BORDER};"); v.addWidget(sep2)

        # ── Options ──────────────────────────────────────────────────────────
        hdr3 = QLabel("  OPTIONS")
        hdr3.setStyleSheet(f"color:{DIM};font-family:'{MONO}';font-size:8px;"
                           f"letter-spacing:3px;padding:8px 12px 4px;background:transparent;")
        v.addWidget(hdr3)

        def mk_toggle(label, signal, default=True):
            btn = QPushButton(f"  {'✓' if default else '○'}  {label}")
            btn.setCheckable(True); btn.setChecked(default)
            btn.setStyleSheet(
                f"QPushButton{{background:transparent;color:{DIM};font-family:'{MONO}';"
                f"font-size:9px;text-align:left;padding:6px 14px;border:none;}}"
                f"QPushButton:checked{{color:{CYAN};}}"
                f"QPushButton:hover{{color:{WHITE};}}"
            )
            def _on(checked, b=btn, lbl=label, sig=signal):
                b.setText(f"  {'✓' if checked else '○'}  {lbl}")
                sig.emit(checked)
            btn.toggled.connect(_on)
            return btn

        v.addWidget(mk_toggle("Grille",  self.toggle_grid,   True))
        v.addWidget(mk_toggle("Labels",  self.toggle_labels, True))
        v.addSpacing(8)

        # Bouton vider
        clear_btn = QPushButton("  ✕  TOUT EFFACER")
        clear_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{DARK};font-family:'{MONO}';"
            f"font-size:9px;text-align:left;padding:6px 14px;border:none;}}"
            f"QPushButton:hover{{color:{RED};}}"
        )
        clear_btn.clicked.connect(self._on_clear)
        v.addWidget(clear_btn)
        v.addSpacing(8)

    def _on_style(self, name: str):
        desc = SITE_STYLES.get(name, {}).get("desc", "")
        self._style_desc.setText(desc)
        self.style_changed.emit(name)

    def _on_place(self, rtype: str, btn: QPushButton):
        if self._active_btn and self._active_btn is not btn:
            self._active_btn.setChecked(False)
        self._active_btn = btn if btn.isChecked() else None
        self.place_room.emit(rtype if btn.isChecked() else "")

    def _on_clear(self):
        from PyQt6.QtWidgets import QMessageBox
        box = QMessageBox(self)
        box.setWindowTitle("Confirmer")
        box.setText("Effacer toutes les salles ?")
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setStyleSheet(f"background:{BG2};color:{WHITE};font-family:'{MONO}';")
        if box.exec() == QMessageBox.StandardButton.Yes:
            # Signal géré par le widget parent via clear_btn
            pass

    def deselect_all_buttons(self):
        if self._active_btn:
            self._active_btn.setChecked(False)
            self._active_btn = None

    def get_style(self) -> str:
        return self._style_combo.currentText()

    def set_style(self, name: str):
        idx = self._style_combo.findText(name)
        if idx >= 0:
            self._style_combo.setCurrentIndex(idx)


# ══════════════════════════════════════════════════════════════════════════════
#  PANNEAU INFO SALLE
# ══════════════════════════════════════════════════════════════════════════════
class RoomInfoPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.setStyleSheet(f"background:{BG3};border-top:1px solid {BORDER};")
        h = QHBoxLayout(self); h.setContentsMargins(16,0,16,0); h.setSpacing(20)

        self._icon  = QLabel("◈")
        self._icon.setStyleSheet(f"color:{CYAN};font-size:22px;background:transparent;")
        self._name  = QLabel("— Aucune salle sélectionnée —")
        self._name.setStyleSheet(S(DIM, 11, ls=1))
        self._type  = QLabel("")
        self._type.setStyleSheet(S(DARK, 9, ls=2))
        self._pos   = QLabel("")
        self._pos.setStyleSheet(S(DARK, 8, ls=0))

        info_v = QVBoxLayout(); info_v.setSpacing(2)
        info_v.addWidget(self._name)
        info_v.addWidget(self._type)

        h.addWidget(self._icon)
        h.addLayout(info_v, 1)
        h.addWidget(self._pos)

        self._hint = QLabel("Clic gauche : placer/déplacer  |  Double-clic : renommer  |  Clic droit : options")
        self._hint.setStyleSheet(S(DARK, 8, ls=0))
        h.addWidget(self._hint)

    def update_room(self, room):
        if room is None:
            self._icon.setText("◈")
            self._icon.setStyleSheet(f"color:{CYAN};font-size:22px;background:transparent;")
            self._name.setText("— Aucune salle sélectionnée —")
            self._name.setStyleSheet(S(DIM, 11, ls=1))
            self._type.setText("")
            self._pos.setText("")
        else:
            rtype = ROOM_TYPES.get(room.type, ROOM_TYPES["Recherche"])
            self._icon.setText(rtype["icon"])
            self._icon.setStyleSheet(f"color:{rtype['color']};font-size:22px;background:transparent;")
            self._name.setText(room.name)
            self._name.setStyleSheet(S(WHITE, 12, bold=True, ls=1))
            self._type.setText(room.type.upper())
            self._type.setStyleSheet(f"color:{rtype['color']};font-family:'{MONO}';font-size:9px;letter-spacing:3px;background:transparent;")
            self._pos.setText(f"x:{room.x}  y:{room.y}  {room.w}×{room.h}")


# ══════════════════════════════════════════════════════════════════════════════
#  WIDGET PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
class SiteMapWidget(QWidget):
    def __init__(self, login: str, niveau: int, nom_affiche: str, parent=None):
        super().__init__(parent)
        self.login       = login
        self.niveau      = niveau
        self.nom_affiche = nom_affiche
        self._build()

    def _build(self):
        self.setStyleSheet(f"background:{WIN_BG};")
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        # Corps principal
        body = QWidget(); body_h = QHBoxLayout(body)
        body_h.setContentsMargins(0,0,0,0); body_h.setSpacing(0)

        # Panneau latéral
        self._side = SidePanel()
        self._side.place_room.connect(self._on_place)
        self._side.style_changed.connect(self._on_style)
        self._side.toggle_grid.connect(self._on_grid)
        self._side.toggle_labels.connect(self._on_labels)
        body_h.addWidget(self._side)

        # Canvas scrollable
        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setStyleSheet(
            f"QScrollArea{{border:none;background:{BG};}}"
            f"QScrollBar:vertical{{background:{BG2};width:8px;}}"
            f"QScrollBar::handle:vertical{{background:{BORDER_B};border-radius:4px;}}"
            f"QScrollBar:horizontal{{background:{BG2};height:8px;}}"
            f"QScrollBar::handle:horizontal{{background:{BORDER_B};border-radius:4px;}}"
        )
        self._canvas = MapCanvas()
        self._canvas.setFixedSize(2000, 1500)
        self._canvas.room_selected.connect(self._on_room_select)
        self._canvas.rooms_changed.connect(self._on_rooms_changed)
        scroll.setWidget(self._canvas)
        body_h.addWidget(scroll, 1)

        root.addWidget(body, 1)

        # Panneau info bas
        self._info = RoomInfoPanel()
        root.addWidget(self._info)

        # Charger les données
        self._canvas.load()
        saved = DataStore.load("sitemap.dat", {})
        if "style" in saved:
            self._side.set_style(saved["style"])

    def _on_place(self, rtype: str):
        self._canvas.set_placing(rtype or None)

    def _on_style(self, name: str):
        self._canvas.set_style(name)

    def _on_grid(self, v: bool):
        self._canvas._show_grid = v
        self._canvas.update()

    def _on_labels(self, v: bool):
        self._canvas._show_labels = v
        self._canvas.update()

    def _on_room_select(self, room):
        self._info.update_room(room)
        # Désactiver le mode placement si on clique sur une salle existante
        if room:
            self._canvas.set_placing(None)
            self._side.deselect_all_buttons()

    def _on_rooms_changed(self):
        pass  # déjà sauvegardé dans le canvas


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    load_barlow()

    login, niveau, nom_affiche = check_clearance("Site Map")
    win = ScipnetWindow("Site Map", login, niveau, nom_affiche, width=1200, height=750)
    widget = SiteMapWidget(login, niveau, nom_affiche)
    win.set_content(widget)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
