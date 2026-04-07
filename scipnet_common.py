"""
SCiPNET — Bibliothèque commune
Partagée par toutes les apps standalone.
"""
import sys, os, json, hashlib, platform, tempfile, threading, urllib.request
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QFrame, QMainWindow, QHBoxLayout, QVBoxLayout, QMessageBox
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QFontDatabase, QColor, QPalette, QIcon, QPixmap

try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None

# ══════════════════════════════════════════════════════════════════════════════
#  PALETTE
# ══════════════════════════════════════════════════════════════════════════════
BG       = "#080808"
BG2      = "#0e0e0e"
BG3      = "#161616"
WIN_BG   = "#0d0d0d"
WIN_HDR  = "#141414"
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
GREEN_D  = "#0d4422"
MONO     = "Courier New"

# ══════════════════════════════════════════════════════════════════════════════
#  NIVEAUX
# ══════════════════════════════════════════════════════════════════════════════
NIVEAU_LABELS = {1:"MINIMAL", 2:"RESTREINT", 3:"CONFIDENTIEL", 4:"SECRET", 5:"TOP SECRET"}
NIVEAU_COLORS = {1:"#6a6a6a", 2:"#f5d020", 3:"#ff8800", 4:"#cc3333", 5:"#cc00ff"}
APP_NIVEAU    = {
    "Terminal":1, "Fichiers":1, "Personnel":2,
    "Chiffrement":2, "Base SCP":3, "Site Map":3, "Paramètres":1,
}

# ══════════════════════════════════════════════════════════════════════════════
#  DATASTORE
# ══════════════════════════════════════════════════════════════════════════════
class DataStore:
    _DIR: Path | None = None
    _KEY: bytes | None = None

    @classmethod
    def dir(cls) -> Path:
        if cls._DIR is None:
            base = Path.home()
            cls._DIR = base / ".scipnet"
            cls._DIR.mkdir(parents=True, exist_ok=True)
        return cls._DIR

    @classmethod
    def _key(cls) -> bytes:
        if cls._KEY is None:
            key_file = cls.dir() / "key.bin"
            if key_file.exists():
                cls._KEY = key_file.read_bytes()
            else:
                cls._KEY = Fernet.generate_key() if Fernet else b""
                key_file.write_bytes(cls._KEY)
        return cls._KEY

    @classmethod
    def _cipher(cls):
        if Fernet and cls._key():
            return Fernet(cls._key())
        return None

    @classmethod
    def save(cls, filename: str, data: dict | list):
        path = cls.dir() / filename
        raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        c = cls._cipher()
        path.write_bytes(c.encrypt(raw) if c else raw)

    @classmethod
    def load(cls, filename: str, default):
        path = cls.dir() / filename
        if not path.exists():
            return default
        try:
            raw = path.read_bytes()
            c = cls._cipher()
            if c:
                try: raw = c.decrypt(raw)
                except: pass
            return json.loads(raw.decode("utf-8"))
        except:
            return default

    @staticmethod
    def hash_mdp(mdp: str) -> str:
        return hashlib.sha256(mdp.encode("utf-8")).hexdigest()

    @staticmethod
    def check_mdp(mdp: str, stored: str) -> bool:
        if len(stored) == 64:
            return hashlib.sha256(mdp.encode("utf-8")).hexdigest() == stored
        return mdp == stored

# ══════════════════════════════════════════════════════════════════════════════
#  UTILISATEURS
# ══════════════════════════════════════════════════════════════════════════════
def load_users() -> dict:
    defaults = {
        "agent13"   : {"mdp": DataStore.hash_mdp("keter"),      "niveau": 1},
        "dr.rights" : {"mdp": DataStore.hash_mdp("euclide"),    "niveau": 2},
        "dr.bright" : {"mdp": DataStore.hash_mdp("everything"), "niveau": 3},
        "admin"     : {"mdp": DataStore.hash_mdp("O5-CONSEIL"), "niveau": 5},
    }
    stored = DataStore.load("users.dat", None)
    if stored is None:
        DataStore.save("users.dat", defaults)
        return defaults
    return stored

def verify_user(login: str, mdp: str) -> tuple[bool, int]:
    """Retourne (ok, niveau). Vérifie dans users.dat."""
    users = load_users()
    login = login.strip().lower()
    if login not in users:
        return False, 0
    u = users[login]
    if DataStore.check_mdp(mdp, u.get("mdp", "")):
        return True, u.get("niveau", 1)
    return False, 0

# ══════════════════════════════════════════════════════════════════════════════
#  FONT BARLOW
# ══════════════════════════════════════════════════════════════════════════════
_FONT_CACHE = Path(tempfile.gettempdir()) / "BarlowCondensed.woff2"
_FONT_URL   = ("https://fonts.gstatic.com/s/barlowcondensed/v12/"
               "HTxwL3I-JCGChYJ8VI-L6OO_au7B497y_3HcuKECcrs.woff2")

def load_barlow():
    global MONO
    if not _FONT_CACHE.exists():
        try: urllib.request.urlretrieve(_FONT_URL, _FONT_CACHE)
        except: return
    fid = QFontDatabase.addApplicationFont(str(_FONT_CACHE))
    if fid >= 0:
        fams = QFontDatabase.applicationFontFamilies(fid)
        if fams: MONO = fams[0]

# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def F(size=11, bold=False) -> QFont:
    f = QFont(MONO, size); f.setBold(bold); return f

def S(color=WHITE, size=11, bold=False, ls=1, bg="transparent") -> str:
    w = "600" if bold else "400"
    return (f"color:{color};font-family:'{MONO}';font-size:{size}px;"
            f"font-weight:{w};letter-spacing:{ls}px;background:{bg};")

def hsep() -> QFrame:
    f = QFrame(); f.setFixedHeight(1)
    f.setStyleSheet(f"background:{BORDER};"); return f

# ══════════════════════════════════════════════════════════════════════════════
#  VÉRIFICATION CLAIRANCE AU LANCEMENT
# ══════════════════════════════════════════════════════════════════════════════
def check_clearance(app_name: str) -> tuple[str, int, str]:
    """
    Vérifie la session courante depuis session.dat.
    Retourne (login, niveau, nom_affiche) ou quitte si clairance insuffisante.
    nom_affiche = "Titre Nom" ex: "Dr. Martin Jean"
    """
    session = DataStore.load("session.dat", None)
    if not session:
        _show_error(f"Aucune session active.\nLancez SCiPNET d'abord.")
        sys.exit(1)

    login  = session.get("login", "")
    niveau = session.get("niveau", 0)
    requis = APP_NIVEAU.get(app_name, 1)

    titre = session.get("titre", "")
    nom   = session.get("nom", login)
    if titre and nom:
        nom_affiche = f"{titre} {nom}"
    elif nom:
        nom_affiche = nom
    else:
        nom_affiche = login

    if niveau < requis:
        _show_error(
            f"Accès refusé — {app_name}\n\n"
            f"Niveau requis : {requis} — {NIVEAU_LABELS.get(requis,'?')}\n"
            f"Votre niveau  : {niveau} — {NIVEAU_LABELS.get(niveau,'?')}"
        )
        sys.exit(1)

    return login, niveau, nom_affiche

def save_session(login: str, niveau: int):
    """Sauvegarde la session active (appelé par Principal.py au login)."""
    DataStore.save("session.dat", {"login": login, "niveau": niveau})

def clear_session():
    """Efface la session (appelé au logout)."""
    p = DataStore.dir() / "session.dat"
    if p.exists(): p.unlink()

def _show_error(msg: str):
    app = QApplication.instance() or QApplication(sys.argv)
    box = QMessageBox()
    box.setWindowTitle("SCiPNET — Accès refusé")
    box.setText(msg)
    box.setStyleSheet(f"background:{BG2};color:{WHITE};font-family:'{MONO}';")
    box.exec()

# ══════════════════════════════════════════════════════════════════════════════
#  FENÊTRE DE BASE POUR APPS STANDALONE
# ══════════════════════════════════════════════════════════════════════════════
class ScipnetWindow(QMainWindow):
    """Fenêtre de base pour toutes les apps SCiPNET standalone."""

    def __init__(self, title: str, login: str, niveau: int, nom_affiche: str = "",
                 width=900, height=620, parent=None):
        super().__init__(parent)
        self.login        = login
        self.niveau       = niveau
        self.nom_affiche  = nom_affiche or login
        self._title       = title

        self.setWindowTitle(f"SCiPNET — {title}")
        self.resize(width, height)

        # Icône
        ico = Path("/opt/scipnet/scp-logo.png")
        if ico.exists():
            self.setWindowIcon(QIcon(str(ico)))

        # Palette sombre globale
        pal = QPalette()
        for role in [QPalette.ColorRole.Window, QPalette.ColorRole.Base,
                     QPalette.ColorRole.AlternateBase]:
            pal.setColor(role, QColor(BG))
        pal.setColor(QPalette.ColorRole.WindowText, QColor(WHITE))
        pal.setColor(QPalette.ColorRole.Text,       QColor(WHITE))
        self.setPalette(pal)
        self.setStyleSheet(f"background:{BG};color:{WHITE};font-family:'{MONO}';")

        # Barre de titre custom
        self._build_titlebar()

    def _build_titlebar(self):
        """Barre de titre style SCiPNET avec infos utilisateur."""
        bar = QWidget()
        bar.setFixedHeight(36)
        bar.setStyleSheet(
            f"background:{WIN_HDR};border-bottom:1px solid {BORDER_B};"
        )
        h = QHBoxLayout(bar); h.setContentsMargins(14, 0, 8, 0); h.setSpacing(8)

        # Logo + titre
        logo = QLabel("◈")
        logo.setStyleSheet(f"color:{CYAN};font-size:14px;background:transparent;")
        title_lbl = QLabel(f"SCiPNET  —  {self._title.upper()}")
        title_lbl.setStyleSheet(S(WHITE, 10, bold=True, ls=3))

        h.addWidget(logo)
        h.addWidget(title_lbl)
        h.addStretch()

        # Infos utilisateur
        ncol = NIVEAU_COLORS.get(self.niveau, DIM)
        display_name = self.nom_affiche if self.nom_affiche != self.login else self.login.upper()
        user_lbl = QLabel(
            f"{display_name}  |  N{self.niveau} — {NIVEAU_LABELS.get(self.niveau,'?')}"
        )
        user_lbl.setStyleSheet(f"color:{ncol};font-family:'{MONO}';font-size:8px;letter-spacing:2px;background:transparent;")
        h.addWidget(user_lbl)

        # Séparateur
        sep = QFrame(); sep.setFixedWidth(1); sep.setFixedHeight(20)
        sep.setStyleSheet(f"background:{BORDER_B};")
        h.addWidget(sep)

        # Horloge
        self._clk = QLabel()
        self._clk.setStyleSheet(S(DIM, 9, ls=1))
        QTimer(self, interval=1000, timeout=self._tick).start()
        self._tick()
        h.addWidget(self._clk)

        # Widget central avec barre + contenu
        central = QWidget()
        v = QVBoxLayout(central); v.setContentsMargins(0,0,0,0); v.setSpacing(0)
        v.addWidget(bar)

        # Zone de contenu (à remplir par les sous-classes)
        self._content_area = QWidget()
        self._content_area.setStyleSheet(f"background:{WIN_BG};")
        v.addWidget(self._content_area, 1)

        self.setCentralWidget(central)

    def set_content(self, widget: QWidget):
        """Définit le widget de contenu principal."""
        lay = QVBoxLayout(self._content_area)
        lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)
        lay.addWidget(widget)

    def _tick(self):
        self._clk.setText(datetime.now().strftime("%H:%M:%S"))
