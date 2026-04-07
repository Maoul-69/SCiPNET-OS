#!/usr/bin/env python3
"""
SCiPNET — Assistant de première configuration
Se lance UNE SEULE FOIS au premier démarrage de session.
Demande : nom complet, titre, niveau de clairance, site d'affectation.
Crée ensuite le compte dans users.dat et sauvegarde la session.
"""
import sys, os, getpass, json
from pathlib import Path

sys.path.insert(0, "/opt/scipnet")

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QFrame,
    QStackedWidget, QTextEdit,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QFont, QPalette

try:
    from cryptography.fernet import Fernet
    HAS_FERNET = True
except ImportError:
    HAS_FERNET = False

# ── Palette ───────────────────────────────────────────────────────────────────
BG       = "#080808"
BG2      = "#0e0e0e"
BG3      = "#161616"
BORDER   = "#242424"
BORDER_B = "#333333"
WHITE    = "#efefef"
DIM      = "#6a6a6a"
DARK     = "#383838"
CYAN     = "#00d4ff"
CYAN_D   = "#003d4d"
RED      = "#cc3333"
YELLOW   = "#f5d020"
GREEN    = "#22bb44"
MONO     = "Courier New"

NIVEAU_LABELS = {1:"MINIMAL", 2:"RESTREINT", 3:"CONFIDENTIEL", 4:"SECRET", 5:"TOP SECRET"}
NIVEAU_COLORS = {1:"#6a6a6a", 2:"#f5d020", 3:"#ff8800", 4:"#cc3333", 5:"#cc00ff"}

TITRES = [
    "Agent", "Chercheur", "Docteur", "Professeur", "Directeur",
    "Commandant", "Ingénieur", "Médecin", "Analyste",
    "Coordinateur", "Superviseur",
]

SITES = [
    "AYIN", "ALPHA", "BETA", "GAMMA", "DELTA", "EPSILON",
    "ZETA", "ETA", "THETA", "IOTA", "KAPPA", "LAMBDA",
    "MU", "NU", "XI", "OMICRON", "PI", "RHO", "SIGMA",
    "TAU", "UPSILON", "PHI", "CHI", "PSI", "OMEGA",
]

# ── DataStore minimal ─────────────────────────────────────────────────────────
class _Store:
    _DIR = Path.home() / ".scipnet"
    _KEY = None

    @classmethod
    def dir(cls) -> Path:
        cls._DIR.mkdir(parents=True, exist_ok=True)
        return cls._DIR

    @classmethod
    def key(cls) -> bytes:
        if cls._KEY is None:
            kf = cls.dir() / "key.bin"
            if kf.exists():
                cls._KEY = kf.read_bytes()
            else:
                cls._KEY = Fernet.generate_key() if HAS_FERNET else b""
                kf.write_bytes(cls._KEY)
        return cls._KEY

    @classmethod
    def cipher(cls):
        if HAS_FERNET and cls.key():
            return Fernet(cls.key())
        return None

    @classmethod
    def load(cls, filename: str, default):
        p = cls.dir() / filename
        if not p.exists(): return default
        try:
            raw = p.read_bytes()
            c = cls.cipher()
            if c:
                try: raw = c.decrypt(raw)
                except: pass
            return json.loads(raw.decode("utf-8"))
        except:
            return default

    @classmethod
    def save(cls, filename: str, data):
        p = cls.dir() / filename
        raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        c = cls.cipher()
        p.write_bytes(c.encrypt(raw) if c else raw)

    @classmethod
    def hash_mdp(cls, mdp: str) -> str:
        import hashlib
        return hashlib.sha256(mdp.encode("utf-8")).hexdigest()

def F(size=11, bold=False) -> QFont:
    f = QFont(MONO, size); f.setBold(bold); return f

def S(color=WHITE, size=11, bold=False, ls=1, bg="transparent") -> str:
    w = "600" if bold else "400"
    return (f"color:{color};font-family:'{MONO}';font-size:{size}px;"
            f"font-weight:{w};letter-spacing:{ls}px;background:{bg};")

def mk_input(placeholder="", pwd=False, width=None) -> QLineEdit:
    f = QLineEdit()
    f.setPlaceholderText(placeholder)
    if pwd: f.setEchoMode(QLineEdit.EchoMode.Password)
    if width: f.setFixedWidth(width)
    f.setStyleSheet(
        f"QLineEdit{{background:{BG3};color:{WHITE};font-family:'{MONO}';"
        f"font-size:12px;border:1px solid {BORDER_B};padding:8px 12px;"
        f"border-radius:2px;}}"
        f"QLineEdit:focus{{border:1px solid {CYAN};}}"
        f"QLineEdit::placeholder{{color:{DARK};}}"
    )
    pal = f.palette()
    pal.setColor(pal.ColorRole.Text, QColor(WHITE))
    pal.setColor(pal.ColorRole.Base, QColor(BG3))
    f.setPalette(pal)
    f.setFont(F(12))
    return f

def mk_combo(items: list, width=None) -> QComboBox:
    c = QComboBox()
    c.addItems(items)
    if width: c.setFixedWidth(width)
    c.setStyleSheet(
        f"QComboBox{{background:{BG3};color:{WHITE};font-family:'{MONO}';"
        f"font-size:12px;border:1px solid {BORDER_B};padding:8px 12px;border-radius:2px;}}"
        f"QComboBox::drop-down{{border:none;width:20px;}}"
        f"QComboBox::down-arrow{{color:{CYAN};}}"
        f"QComboBox QAbstractItemView{{background:{BG2};color:{WHITE};"
        f"border:1px solid {BORDER};selection-background-color:{CYAN_D};"
        f"font-family:'{MONO}';font-size:11px;}}"
    )
    return c

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 1 — Bienvenue
# ══════════════════════════════════════════════════════════════════════════════
class WelcomePage(QWidget):
    next_sig = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{BG};")
        v = QVBoxLayout(self)
        v.setContentsMargins(80, 60, 80, 60)
        v.setSpacing(0)
        v.addStretch()

        # Logo SCP
        logo = QLabel("☣")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(f"color:{CYAN};font-size:64px;background:transparent;letter-spacing:0;")
        v.addWidget(logo)
        v.addSpacing(30)

        # Titre
        title = QLabel("SCP FOUNDATION")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(S(WHITE, 28, bold=True, ls=8))
        v.addWidget(title)
        v.addSpacing(8)

        sub = QLabel("S E C U R E  ·  C O N T A I N  ·  P R O T E C T")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(S(DIM, 11, ls=4))
        v.addWidget(sub)
        v.addSpacing(40)

        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{BORDER_B};")
        v.addWidget(sep)
        v.addSpacing(40)

        # Texte d'accueil
        self._text = QLabel("")
        self._text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text.setWordWrap(True)
        self._text.setStyleSheet(S(DIM, 11, ls=1))
        v.addWidget(self._text)
        v.addSpacing(50)

        # Bouton continuer
        self._btn = QPushButton("INITIALISER L'ACCÈS  →")
        self._btn.setFixedHeight(44)
        self._btn.setStyleSheet(
            f"QPushButton{{background:{CYAN_D};color:{CYAN};font-family:'{MONO}';"
            f"font-size:11px;font-weight:600;letter-spacing:3px;border:1px solid {CYAN};"
            f"border-radius:2px;}}"
            f"QPushButton:hover{{background:{CYAN};color:{BG};}}"
        )
        self._btn.clicked.connect(self.next_sig.emit)
        self._btn.setVisible(False)
        v.addWidget(self._btn)
        v.addStretch()

        # Animation texte
        self._full = (
            "Bienvenue dans le réseau SCiPNET.\n\n"
            "Ce système est réservé au personnel autorisé\n"
            "de la Fondation SCP.\n\n"
            "Avant de continuer, vous devez enregistrer\n"
            "votre identité et votre niveau de clairance."
        )
        self._idx = 0
        QTimer.singleShot(800, self._type_text)

    def _type_text(self):
        if self._idx <= len(self._full):
            self._text.setText(self._full[:self._idx])
            self._idx += 1
            QTimer.singleShot(18, self._type_text)
        else:
            QTimer.singleShot(400, lambda: self._btn.setVisible(True))


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 2 — Formulaire d'enregistrement
# ══════════════════════════════════════════════════════════════════════════════
class RegisterPage(QWidget):
    done_sig = pyqtSignal(dict)

    def __init__(self, linux_user: str, parent=None):
        super().__init__(parent)
        self.linux_user = linux_user
        self.setStyleSheet(f"background:{BG};")
        v = QVBoxLayout(self)
        v.setContentsMargins(120, 50, 120, 50)
        v.setSpacing(0)

        # En-tête
        hdr = QLabel("ENREGISTREMENT DU PERSONNEL")
        hdr.setStyleSheet(S(CYAN, 13, bold=True, ls=4))
        v.addWidget(hdr)
        v.addSpacing(6)

        sub = QLabel(f"Compte système : {linux_user.upper()}")
        sub.setStyleSheet(S(DARK, 9, ls=2))
        v.addWidget(sub)
        v.addSpacing(30)

        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{BORDER};")
        v.addWidget(sep)
        v.addSpacing(30)

        # ── Champs ────────────────────────────────────────────────────────────
        def field_row(label: str, widget, hint=""):
            row = QWidget(); row.setStyleSheet("background:transparent;")
            rv = QVBoxLayout(row); rv.setContentsMargins(0,0,0,0); rv.setSpacing(4)
            lbl = QLabel(label); lbl.setStyleSheet(S(DIM, 9, ls=2))
            rv.addWidget(lbl); rv.addWidget(widget)
            if hint:
                h = QLabel(hint); h.setStyleSheet(S(DARK, 8, ls=0))
                rv.addWidget(h)
            return row

        # Nom complet
        self._nom = mk_input("ex : Martin, Jean-Baptiste")
        v.addWidget(field_row("NOM COMPLET", self._nom))
        v.addSpacing(16)

        # Titre / Statut
        self._titre = mk_combo(TITRES)
        v.addWidget(field_row("TITRE / STATUT", self._titre,
                              "Votre fonction au sein de la Fondation"))
        v.addSpacing(16)

        # Niveau de clairance
        niv_w = QWidget(); niv_w.setStyleSheet("background:transparent;")
        niv_h = QHBoxLayout(niv_w); niv_h.setContentsMargins(0,0,0,0); niv_h.setSpacing(12)
        self._niveau = mk_combo(
            [f"N{n} — {l}" for n, l in NIVEAU_LABELS.items() if n < 5]
        )  # N5 réservé au compte admin — sur demande
        self._niveau.currentIndexChanged.connect(self._update_niv_color)
        self._niv_dot = QLabel("●")
        self._niv_dot.setStyleSheet(f"color:{NIVEAU_COLORS[1]};font-size:16px;background:transparent;")
        niv_h.addWidget(self._niveau, 1); niv_h.addWidget(self._niv_dot)
        v.addWidget(field_row("NIVEAU DE CLAIRANCE", niv_w,
                             "N5 (O5) : sur demande auprès de l'administration"))
        v.addSpacing(16)

        # Site d'affectation
        self._site = mk_combo(SITES)
        v.addWidget(field_row("SITE D'AFFECTATION", self._site))
        v.addSpacing(16)

        # Mot de passe
        self._mdp = mk_input("Choisissez un mot de passe", pwd=True)
        self._mdp2 = mk_input("Confirmez le mot de passe", pwd=True)
        v.addWidget(field_row("MOT DE PASSE", self._mdp,
                              "Minimum 4 caractères"))
        v.addSpacing(8)
        v.addWidget(field_row("CONFIRMATION", self._mdp2))
        v.addSpacing(24)

        # Message erreur
        self._err = QLabel("")
        self._err.setStyleSheet(S(RED, 9, ls=1))
        self._err.setWordWrap(True)
        v.addWidget(self._err)
        v.addSpacing(8)

        # Bouton valider
        self._btn = QPushButton("VALIDER ET ACCÉDER AU SYSTÈME  →")
        self._btn.setFixedHeight(44)
        self._btn.setStyleSheet(
            f"QPushButton{{background:{CYAN_D};color:{CYAN};font-family:'{MONO}';"
            f"font-size:11px;font-weight:600;letter-spacing:3px;border:1px solid {CYAN};"
            f"border-radius:2px;}}"
            f"QPushButton:hover{{background:{CYAN};color:{BG};}}"
        )
        self._btn.clicked.connect(self._validate)
        v.addWidget(self._btn)
        v.addStretch()

    def _update_niv_color(self, idx):
        niv = idx + 1
        col = NIVEAU_COLORS.get(niv, DIM)
        self._niv_dot.setStyleSheet(f"color:{col};font-size:16px;background:transparent;")

    def _validate(self):
        nom   = self._nom.text().strip()
        titre = self._titre.currentText()
        niv   = self._niveau.currentIndex() + 1
        site  = self._site.currentText()
        mdp   = self._mdp.text()
        mdp2  = self._mdp2.text()

        if not nom:
            self._err.setText("Le nom complet est requis."); return
        if len(mdp) < 4:
            self._err.setText("Le mot de passe doit faire au moins 4 caractères."); return
        if mdp != mdp2:
            self._err.setText("Les mots de passe ne correspondent pas."); return

        self._err.setText("")
        self.done_sig.emit({
            "linux_user": self.linux_user,
            "nom"        : nom,
            "titre"      : titre,
            "niveau"     : niv,
            "site"       : site,
            "mdp"        : mdp,
        })


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 3 — Confirmation
# ══════════════════════════════════════════════════════════════════════════════
class ConfirmPage(QWidget):
    finish_sig = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{BG};")
        v = QVBoxLayout(self)
        v.setContentsMargins(80, 60, 80, 60)
        v.setSpacing(0)
        v.addStretch()

        check = QLabel("✓")
        check.setAlignment(Qt.AlignmentFlag.AlignCenter)
        check.setStyleSheet(f"color:{GREEN};font-size:64px;background:transparent;")
        v.addWidget(check)
        v.addSpacing(30)

        self._title = QLabel("ACCÈS AUTORISÉ")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setStyleSheet(S(GREEN, 22, bold=True, ls=6))
        v.addWidget(self._title)
        v.addSpacing(20)

        self._info = QLabel("")
        self._info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._info.setWordWrap(True)
        self._info.setStyleSheet(S(DIM, 11, ls=1))
        v.addWidget(self._info)
        v.addSpacing(40)

        self._btn = QPushButton("ACCÉDER AU BUREAU  →")
        self._btn.setFixedHeight(44)
        self._btn.setStyleSheet(
            f"QPushButton{{background:{CYAN_D};color:{CYAN};font-family:'{MONO}';"
            f"font-size:11px;font-weight:600;letter-spacing:3px;border:1px solid {CYAN};"
            f"border-radius:2px;}}"
            f"QPushButton:hover{{background:{CYAN};color:{BG};}}"
        )
        self._btn.clicked.connect(self.finish_sig.emit)
        v.addWidget(self._btn)
        v.addStretch()

    def set_data(self, data: dict):
        niv   = data["niveau"]
        ncol  = NIVEAU_COLORS.get(niv, DIM)
        self._info.setText(
            f"{data['titre']} {data['nom']}\n\n"
            f"Niveau de clairance : N{niv} — {NIVEAU_LABELS.get(niv,'?')}\n"
            f"Site d'affectation  : SITE-{data['site']}"
        )
        self._info.setStyleSheet(S(WHITE, 12, ls=1))


# ── Envoi du profil au serveur central ───────────────────────────────────────
def _send_profile_to_server(data: dict):
    """Envoie le profil public au serveur SCiPNET central (optionnel)."""
    import socket, json as _json
    cfg = _Store.load("msg_config.dat", {})
    host = cfg.get("host", "")
    port = cfg.get("port", 9847)
    if not host:
        return  # Pas de serveur configuré, silencieux
    try:
        nom   = data.get("nom", "")
        titre = data.get("titre", "Agent")
        site  = data.get("site", "AYIN")
        login = data.get("linux_user", "")
        email = f"{titre.lower()}.{nom.lower().replace(' ','.')}@{site.lower()}.scpf"
        req = {
            "cmd"   : "register_profile",
            "login" : login,
            "nom"   : nom,
            "titre" : titre,
            "niveau": data.get("niveau", 1),
            "site"  : site,
            "email" : email,
        }
        s = socket.create_connection((host, port), timeout=5)
        s.sendall((_json.dumps(req) + "\n").encode("utf-8"))
        s.recv(1024)
        s.close()
    except Exception:
        pass  # Silencieux si le serveur est injoignable

# ══════════════════════════════════════════════════════════════════════════════
#  FENÊTRE PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════
class SetupWizard(QWidget):
    def __init__(self, linux_user: str):
        super().__init__()
        self.linux_user = linux_user
        self._data: dict = {}

        self.setWindowTitle("SCiPNET — Configuration initiale")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setStyleSheet(f"background:{BG};")

        # Layout principal avec QVBoxLayout
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._stack = QStackedWidget()
        root.addWidget(self._stack)

        self._p1 = WelcomePage()
        self._p2 = RegisterPage(linux_user)
        self._p3 = ConfirmPage()

        self._stack.addWidget(self._p1)
        self._stack.addWidget(self._p2)
        self._stack.addWidget(self._p3)

        self._p1.next_sig.connect(lambda: self._stack.setCurrentIndex(1))
        self._p2.done_sig.connect(self._on_register)
        self._p3.finish_sig.connect(self._finish)

        self.showFullScreen()

    def _on_register(self, data: dict):
        self._data = data
        self._save(data)
        self._p3.set_data(data)
        self._stack.setCurrentIndex(2)

    def _save(self, data: dict):
        """Sauvegarde le compte et la session."""
        linux_user = data["linux_user"]
        niveau     = data["niveau"]
        site       = data["site"]

        # Charger ou créer users.dat
        users = _Store.load("users.dat", {
            "agent13"  : {"mdp": _Store.hash_mdp("keter"),      "niveau": 1},
            "dr.rights": {"mdp": _Store.hash_mdp("euclide"),    "niveau": 2},
            "dr.bright": {"mdp": _Store.hash_mdp("everything"), "niveau": 3},
            "admin"    : {"mdp": _Store.hash_mdp("O5-CONSEIL"), "niveau": 5},
        })

        # Créer/mettre à jour le compte
        users[linux_user] = {
            "mdp"   : _Store.hash_mdp(data["mdp"]),
            "niveau": niveau,
            "nom"   : data["nom"],
            "titre" : data["titre"],
            "site"  : site,
        }
        _Store.save("users.dat", users)

        # Sauvegarder la session
        _Store.save("session.dat", {
            "login" : linux_user,
            "niveau": niveau,
            "nom"   : data["nom"],
            "titre" : data["titre"],
            "site"  : site,
        })

        # Sauvegarder le site dans config.dat
        cfg = _Store.load("config.dat", {})
        cfg["site_name"] = site
        _Store.save("config.dat", cfg)

        # Marquer la config comme faite
        (_Store.dir() / ".setup_done").write_text("done")
        # Envoyer le profil au serveur central (si configuré)
        _send_profile_to_server(data)

    def _finish(self):
        self.close()


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def already_setup() -> bool:
    return (_Store.dir() / ".setup_done").exists()

def main():
    # Si déjà configuré → juste mettre à jour la session et quitter
    linux_user = getpass.getuser().lower()

    if already_setup():
        # Recharger la session depuis users.dat
        users = _Store.load("users.dat", {})
        if linux_user in users:
            u = users[linux_user]
            _Store.save("session.dat", {
                "login" : linux_user,
                "niveau": u.get("niveau", 1),
                "nom"   : u.get("nom", linux_user),
                "titre" : u.get("titre", "Agent"),
                "site"  : u.get("site", "AYIN"),
            })
        return  # Pas d'interface, juste mettre à jour la session

    # Première fois → afficher le wizard
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    pal = QPalette()
    for r in [QPalette.ColorRole.Window, QPalette.ColorRole.Base]:
        pal.setColor(r, QColor(BG))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(WHITE))
    pal.setColor(QPalette.ColorRole.Text, QColor(WHITE))
    app.setPalette(pal)

    wizard = SetupWizard(linux_user)
    wizard.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
