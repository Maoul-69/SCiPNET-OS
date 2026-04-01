"""
SCiPNET — Chiffrement v1.0
App standalone — nécessite une session active (session.dat)
"""
import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLabel, QPushButton, QFileDialog, QListWidget, QListWidgetItem,
    QSplitter,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

sys.path.insert(0, "/opt/scipnet")
from scipnet_common import (
    BG, BG2, BG3, WIN_BG, BORDER, BORDER_B,
    WHITE, DIM, DARK, CYAN, CYAN_D, RED, YELLOW, GREEN,
    MONO, NIVEAU_LABELS, NIVEAU_COLORS,
    F, S, DataStore, ScipnetWindow, check_clearance, load_barlow,
)

try:
    from cryptography.fernet import Fernet
    HAS_FERNET = True
except ImportError:
    HAS_FERNET = False

EXT = ".scpenc"
TEXT_EXTS = {".txt",".md",".log",".csv",".json",".xml",".html",".htm",".ini",".cfg",".py",".js"}


class CryptoWidget(QWidget):
    def __init__(self, login: str, niveau: int, parent=None):
        super().__init__(parent)
        self.login   = login
        self.niveau  = niveau
        self._cur_file: Path | None = None
        self._is_encrypted = False
        self._build()

    def _is_text(self, path: Path) -> bool:
        name = path.name
        if name.endswith(EXT): name = name[:-len(EXT)]
        return Path(name).suffix.lower() in TEXT_EXTS

    def _build(self):
        self.setStyleSheet(f"background:{WIN_BG};")
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        sp = QSplitter(Qt.Orientation.Horizontal)
        sp.setStyleSheet(f"QSplitter::handle{{background:{BORDER};width:1px;}}")

        # ── Panneau gauche ────────────────────────────────────────────────────
        left = QWidget(); lv = QVBoxLayout(left); lv.setContentsMargins(0,0,0,0); lv.setSpacing(0)

        # Boutons d'action
        act = QWidget(); act.setFixedHeight(50)
        act.setStyleSheet(f"background:{BG2};border-bottom:1px solid {BORDER};")
        ah = QHBoxLayout(act); ah.setContentsMargins(12,0,12,0); ah.setSpacing(8)

        def mk_btn(txt, col, cb):
            b = QPushButton(txt)
            b.setStyleSheet(
                f"QPushButton{{background:{BG3};color:{col};font-family:'{MONO}';"
                f"font-size:9px;letter-spacing:2px;padding:6px 12px;"
                f"border:1px solid {BORDER_B};}}"
                f"QPushButton:hover{{background:{col};color:{BG};}}"
                f"QPushButton:disabled{{color:{DARK};border-color:{BORDER};}}"
            )
            b.clicked.connect(cb); return b

        self._open_btn  = mk_btn("📂 OUVRIR",    CYAN,      self._pick_file)
        self._enc_btn   = mk_btn("🔒 CHIFFRER",  "#aa44ff", self._encrypt)
        self._dec_btn   = mk_btn("🔓 DÉCHIFFRER",GREEN,     self._decrypt)
        self._scan_btn  = mk_btn("🔍 SCANNER",   YELLOW,    self._scan_folder)
        self._enc_btn.setEnabled(False)
        self._dec_btn.setEnabled(False)
        for b in [self._open_btn, self._enc_btn, self._dec_btn, self._scan_btn]:
            ah.addWidget(b)
        ah.addStretch(); lv.addWidget(act)

        # Liste fichiers chiffrés
        lv.addWidget(QLabel("  FICHIERS CHIFFRÉS",
            styleSheet=f"color:{DARK};font-family:'{MONO}';font-size:8px;letter-spacing:3px;"
                       f"padding:8px 12px 4px;background:{BG2};"))
        self._enc_list = QListWidget()
        self._enc_list.setStyleSheet(
            f"QListWidget{{background:{BG2};color:{WHITE};font-family:'{MONO}';"
            f"font-size:10px;border:none;padding:4px;}}"
            f"QListWidget::item{{padding:4px 10px;border-bottom:1px solid {BORDER};}}"
            f"QListWidget::item:selected{{background:{BORDER_B};}}"
        )
        self._enc_list.setFont(F(10))
        self._enc_list.itemDoubleClicked.connect(self._list_open)
        lv.addWidget(self._enc_list, 1); sp.addWidget(left)

        # ── Panneau droit ─────────────────────────────────────────────────────
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0,0,0,0); rv.setSpacing(0)

        hdr = QWidget(); hdr.setFixedHeight(40)
        hdr.setStyleSheet(f"background:{BG3};border-bottom:1px solid {BORDER};")
        hh = QHBoxLayout(hdr); hh.setContentsMargins(14,0,14,0); hh.setSpacing(8)
        self._editor_title = QLabel("— AUCUN FICHIER —")
        self._editor_title.setStyleSheet(S(DIM,9,bold=True,ls=2))
        hh.addWidget(self._editor_title, 1)
        self._save_btn = mk_btn("💾 ENREGISTRER", CYAN, self._save)
        self._save_btn.setEnabled(False)
        hh.addWidget(self._save_btn); rv.addWidget(hdr)

        self._status_lbl = QLabel()
        self._status_lbl.setStyleSheet(S(DIM,9,ls=0))
        self._status_lbl.setContentsMargins(14,6,14,6)
        rv.addWidget(self._status_lbl)

        self._path_lbl = QLabel("—")
        self._path_lbl.setStyleSheet(S(DARK,8,ls=0))
        self._path_lbl.setContentsMargins(14,0,14,6)
        rv.addWidget(self._path_lbl)

        self._editor = QTextEdit()
        self._editor.setStyleSheet(
            f"background:{WIN_BG};color:{WHITE};font-family:'{MONO}';"
            f"font-size:11px;border:none;padding:14px;"
        )
        self._editor.setFont(F(11)); rv.addWidget(self._editor, 1)

        # Log
        self._log = QTextEdit(); self._log.setReadOnly(True)
        self._log.setFixedHeight(80)
        self._log.setStyleSheet(
            f"background:{BG2};color:{DIM};font-family:'{MONO}';"
            f"font-size:9px;border:none;border-top:1px solid {BORDER};padding:6px;"
        )
        rv.addWidget(self._log); sp.addWidget(right)
        sp.setSizes([280, 620]); root.addWidget(sp, 1)

        if not HAS_FERNET:
            self._log_msg("cryptography non installé — pip install cryptography", RED)

    def _log_msg(self, msg: str, col=DIM):
        from datetime import datetime
        t = datetime.now().strftime("%H:%M:%S")
        self._log.append(f"<span style='color:{DARK};'>[{t}]</span> <span style='color:{col};'>{msg}</span>")

    def _pick_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir fichier", str(Path.home()))
        if path: self._load_file(Path(path))

    def _list_open(self, it):
        path = Path(it.data(Qt.ItemDataRole.UserRole))
        if path.exists(): self._load_file(path)

    def _load_file(self, path: Path):
        self._cur_file = path
        self._path_lbl.setText(str(path))
        fname  = path.name
        is_enc = path.suffix.lower() == EXT
        is_txt = self._is_text(path)
        self._is_encrypted = is_enc

        if is_enc:
            self._status_lbl.setText(f"🔒 CHIFFRÉ  —  {fname}")
            self._status_lbl.setStyleSheet(S("#aa44ff",9,ls=0))
            self._enc_btn.setEnabled(False); self._dec_btn.setEnabled(True)
            ok, text = self._decrypt_to_text(path)
            if not ok:
                self._editor.setPlainText(f"[ERREUR]\n{text}")
                self._editor.setReadOnly(True); self._save_btn.setEnabled(False)
            elif text is None:
                ext = Path(fname[:-len(EXT)]).suffix.upper()
                self._editor.setPlainText(
                    f"Fichier binaire {ext} chiffré.\n\n"
                    f"Cliquez sur 🔓 DÉCHIFFRER pour restaurer sur le disque."
                )
                self._editor.setReadOnly(True); self._save_btn.setEnabled(False)
            else:
                self._editor.setPlainText(text)
                self._editor.setReadOnly(False); self._save_btn.setEnabled(True)
                self._editor_title.setText(fname + "  [déchiffré en mémoire]")
        else:
            self._status_lbl.setText(f"🔓 NON CHIFFRÉ  —  {fname}")
            self._status_lbl.setStyleSheet(S(GREEN,9,ls=0))
            self._enc_btn.setEnabled(HAS_FERNET); self._dec_btn.setEnabled(False)
            if is_txt:
                self._editor.setPlainText(self._read_text(path))
                self._editor.setReadOnly(False); self._save_btn.setEnabled(True)
            else:
                ext = path.suffix.upper()
                self._editor.setPlainText(f"Fichier binaire {ext}.\n\nCliquez sur 🔒 CHIFFRER pour le chiffrer.")
                self._editor.setReadOnly(True); self._save_btn.setEnabled(False)
            self._editor_title.setText(fname)
        self._log_msg(f"Fichier chargé : {fname}", DIM)

    def _read_text(self, path: Path) -> str:
        for enc in ("utf-8","utf-8-sig","latin-1","cp1252"):
            try: return path.read_text(encoding=enc)
            except: continue
        return path.read_bytes().decode("utf-8", errors="replace")

    def _decrypt_to_text(self, path: Path) -> tuple[bool, str | None]:
        if not HAS_FERNET: return False, "cryptography non installé"
        try:
            cipher = DataStore._cipher()
            dec = cipher.decrypt(path.read_bytes())
            if not self._is_text(path): return True, None
            for enc in ("utf-8","utf-8-sig","latin-1","cp1252"):
                try: return True, dec.decode(enc)
                except: continue
            return True, dec.decode("utf-8", errors="replace")
        except Exception as e:
            return False, str(e)

    def _encrypt(self):
        if not self._cur_file or not HAS_FERNET: return
        try:
            cipher = DataStore._cipher()
            raw = self._cur_file.read_bytes()
            out = self._cur_file.with_suffix(self._cur_file.suffix + EXT)
            out.write_bytes(cipher.encrypt(raw))
            self._cur_file.unlink()
            self._log_msg(f"Chiffré → {out.name}", "#aa44ff")
            self._load_file(out); self._scan_folder()
        except Exception as e:
            self._log_msg(f"Erreur chiffrement : {e}", RED)

    def _decrypt(self):
        if not self._cur_file or not HAS_FERNET: return
        try:
            out = Path(str(self._cur_file)[:-len(EXT)])
            cipher = DataStore._cipher()
            decrypted = cipher.decrypt(self._cur_file.read_bytes())
            out.write_bytes(decrypted)
            self._cur_file.unlink()
            self._log_msg(f"Déchiffré → {out.name}", GREEN)
            self._load_file(out); self._scan_folder()
        except Exception as e:
            self._log_msg(f"Erreur déchiffrement : {e}", RED)

    def _save(self):
        if not self._cur_file or not self._is_text(self._cur_file): return
        text = self._editor.toPlainText()
        try:
            if self._is_encrypted:
                cipher = DataStore._cipher()
                self._cur_file.write_bytes(cipher.encrypt(text.encode("utf-8")))
                self._log_msg(f"Sauvegardé (chiffré) : {self._cur_file.name}", "#aa44ff")
            else:
                self._cur_file.write_text(text, encoding="utf-8")
                self._log_msg(f"Sauvegardé : {self._cur_file.name}", GREEN)
        except Exception as e:
            self._log_msg(f"Erreur sauvegarde : {e}", RED)

    def _scan_folder(self):
        folder = self._cur_file.parent if self._cur_file else Path.home()
        self._enc_list.clear()
        found = sorted(folder.rglob(f"*{EXT}"))
        for f in found:
            it = QListWidgetItem(f"🔒  {f.name}")
            it.setData(Qt.ItemDataRole.UserRole, str(f))
            it.setForeground(QColor("#aa44ff"))
            self._enc_list.addItem(it)
        if not found:
            it = QListWidgetItem("Aucun fichier chiffré trouvé")
            it.setForeground(QColor(DARK)); self._enc_list.addItem(it)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    load_barlow()
    login, niveau, nom_affiche = check_clearance("Chiffrement")
    win = ScipnetWindow("Chiffrement", login, niveau, nom_affiche, width=950, height=620)
    widget = CryptoWidget(login, niveau)
    win.set_content(widget)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
