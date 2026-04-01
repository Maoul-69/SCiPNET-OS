"""
SCiPNET — Fichiers v1.0
App standalone — nécessite une session active (session.dat)
"""
import sys, re, platform
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QListWidget, QListWidgetItem, QLabel,
    QPushButton, QSplitter, QTabWidget, QLineEdit, QFileDialog,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

sys.path.insert(0, "/opt/scipnet")
from scipnet_common import (
    BG, BG2, BG3, WIN_BG, BORDER, BORDER_B,
    WHITE, DIM, DARK, CYAN, CYAN_D, RED, YELLOW, GREEN,
    MONO, NIVEAU_LABELS, NIVEAU_COLORS,
    F, S, DataStore, ScipnetWindow, check_clearance, load_barlow,
)

CLASS_NIVEAU = {
    "SAFE":1,"NEUTRALIZED":1,"EXPLAINED":1,
    "EUCLIDE":2,"KETER":3,"THAUMIEL":4,"APOLLYON":4,"ARCHON":4,
}
_SCP_INDEX: dict = {}

class FilesWidget(QWidget):
    def __init__(self, login: str, niveau: int, parent=None):
        super().__init__(parent)
        self.login   = login
        self.niveau  = niveau
        state        = DataStore.load("fichiers_state.dat", {})
        self.cur     = Path(state.get("cur", str(Path.home())))
        self._show_hidden = state.get("show_hidden", False)
        self._last_file   = state.get("last_file", None)
        self._build()

    def _save_state(self):
        DataStore.save("fichiers_state.dat", {
            "cur": str(self.cur),
            "show_hidden": self._show_hidden,
            "last_file": self._last_file,
        })

    def _build(self):
        self.setStyleSheet(f"background:{WIN_BG};")
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        tabs = QTabWidget()
        tabs.setStyleSheet(
            f"QTabWidget::pane{{border:none;background:{WIN_BG};}}"
            f"QTabBar::tab{{background:{BG2};color:{DIM};font-family:'{MONO}';"
            f"font-size:9px;letter-spacing:2px;padding:7px 18px;"
            f"border:1px solid {BORDER};border-bottom:none;margin-right:2px;}}"
            f"QTabBar::tab:selected{{background:{WIN_BG};color:{WHITE};"
            f"border-bottom:2px solid {CYAN};}}"
        )
        tabs.addTab(self._build_explorer(), "📂  FICHIERS RP")
        tabs.addTab(self._build_scp_list(), "◈  SCPs")
        self._scp_loaded = False
        tabs.currentChanged.connect(self._on_tab)
        root.addWidget(tabs, 1)

    def _build_explorer(self):
        w = QWidget(); w.setStyleSheet(f"background:{WIN_BG};")
        v = QVBoxLayout(w); v.setContentsMargins(0,0,0,0); v.setSpacing(0)
        top = QWidget(); top.setFixedHeight(40)
        top.setStyleSheet(f"background:{BG2};border-bottom:1px solid {BORDER};")
        th = QHBoxLayout(top); th.setContentsMargins(14,0,14,0); th.setSpacing(8)
        self.path_lbl = QLabel(str(self.cur))
        self.path_lbl.setStyleSheet(S(WHITE,9,ls=0))
        th.addWidget(QLabel("📂", styleSheet=f"color:{YELLOW};font-size:14px;background:transparent;"))
        th.addWidget(self.path_lbl, 1)
        hid = QPushButton("⊘  CACHÉS")
        hid.setCheckable(True); hid.setChecked(self._show_hidden)
        hid.setStyleSheet(
            f"QPushButton{{background:{BG3};color:{DARK};font-family:'{MONO}';"
            f"font-size:9px;letter-spacing:2px;padding:5px 10px;border:1px solid {BORDER};}}"
            f"QPushButton:checked{{color:{YELLOW};border:1px solid {YELLOW};}}"
        )
        hid.toggled.connect(lambda c: (setattr(self,'_show_hidden',c), self._save_state(), self._refresh()))
        th.addWidget(hid)
        btn = QPushButton("CHOISIR DOSSIER")
        btn.setStyleSheet(
            f"QPushButton{{background:{BG3};color:{CYAN};font-family:'{MONO}';"
            f"font-size:9px;letter-spacing:2px;padding:5px 12px;border:1px solid {BORDER_B};}}"
        )
        btn.clicked.connect(self._choose)
        th.addWidget(btn); v.addWidget(top)
        sp = QSplitter(Qt.Orientation.Horizontal)
        sp.setStyleSheet(f"QSplitter::handle{{background:{BORDER};width:1px;}}")
        lw = QWidget(); lv = QVBoxLayout(lw); lv.setContentsMargins(0,0,0,0); lv.setSpacing(0)
        self.flist = QListWidget()
        self.flist.setStyleSheet(
            f"QListWidget{{background:{WIN_BG};color:{WHITE};font-family:'{MONO}';"
            f"font-size:11px;border:none;padding:6px;}}"
            f"QListWidget::item{{padding:5px 10px;border-bottom:1px solid {BORDER};}}"
            f"QListWidget::item:selected{{background:{BORDER_B};}}"
        )
        self.flist.setFont(F(11))
        self.flist.itemClicked.connect(self._click)
        self.flist.itemDoubleClicked.connect(self._dclick)
        lv.addWidget(self.flist); sp.addWidget(lw)
        rw = QWidget(); rv = QVBoxLayout(rw); rv.setContentsMargins(0,0,0,0); rv.setSpacing(0)
        vh = QWidget(); vh.setFixedHeight(34)
        vh.setStyleSheet(f"background:{BG2};border-bottom:1px solid {BORDER};")
        vhh = QHBoxLayout(vh); vhh.setContentsMargins(14,0,14,0)
        self.file_title = QLabel("— AUCUN FICHIER —")
        self.file_title.setStyleSheet(S(DIM,9,bold=True,ls=2))
        vhh.addWidget(self.file_title); rv.addWidget(vh)
        self.viewer = QTextEdit(); self.viewer.setReadOnly(True)
        self.viewer.setStyleSheet(
            f"background:transparent;color:{WHITE};font-family:'{MONO}';"
            f"font-size:11px;border:none;padding:16px;"
        )
        self.viewer.setFont(F(11)); rv.addWidget(self.viewer, 1)
        sp.addWidget(rw); sp.setSizes([280,600]); v.addWidget(sp, 1)
        self._refresh()
        if self._last_file:
            p = Path(self._last_file)
            if p.is_file(): self._open(p)
        return w

    def _build_scp_list(self):
        w = QWidget(); w.setStyleSheet(f"background:{WIN_BG};")
        v = QVBoxLayout(w); v.setContentsMargins(0,0,0,0); v.setSpacing(0)
        top = QWidget(); top.setFixedHeight(40)
        top.setStyleSheet(f"background:{BG2};border-bottom:1px solid {BORDER};")
        th = QHBoxLayout(top); th.setContentsMargins(14,0,14,0); th.setSpacing(8)
        th.addWidget(QLabel("◈", styleSheet=f"color:{RED};font-size:14px;background:transparent;"))
        self._scp_search = QLineEdit()
        self._scp_search.setPlaceholderText("Filtrer : numéro, titre, classe…")
        self._scp_search.setStyleSheet(
            f"QLineEdit{{background:{BG3};color:{WHITE};font-family:'{MONO}';"
            f"font-size:10px;border:1px solid {BORDER_B};padding:3px 8px;}}"
        )
        pal = self._scp_search.palette()
        pal.setColor(pal.ColorRole.Text, QColor(WHITE))
        pal.setColor(pal.ColorRole.Base, QColor(BG3))
        self._scp_search.setPalette(pal)
        self._scp_search.setFont(F(10))
        self._scp_search.textChanged.connect(self._filter_scps)
        th.addWidget(self._scp_search, 1)
        self._scp_count = QLabel(""); self._scp_count.setStyleSheet(S(DIM,8,ls=1))
        th.addWidget(self._scp_count); v.addWidget(top)
        sp2 = QSplitter(Qt.Orientation.Horizontal)
        self._scp_list = QListWidget()
        self._scp_list.setStyleSheet(
            f"QListWidget{{background:{WIN_BG};color:{WHITE};font-family:'{MONO}';"
            f"font-size:10px;border:none;padding:4px;}}"
            f"QListWidget::item{{padding:4px 10px;border-bottom:1px solid {BORDER};}}"
            f"QListWidget::item:selected{{background:{BORDER_B};}}"
        )
        self._scp_list.setFont(F(10))
        self._scp_list.itemClicked.connect(self._scp_clicked)
        sp2.addWidget(self._scp_list)
        self._scp_detail = QTextEdit(); self._scp_detail.setReadOnly(True)
        self._scp_detail.setStyleSheet(
            f"background:{WIN_BG};color:{WHITE};font-family:'{MONO}';"
            f"font-size:10px;border:none;padding:14px;border-left:1px solid {BORDER};"
        )
        sp2.addWidget(self._scp_detail); sp2.setSizes([260,620]); v.addWidget(sp2, 1)
        return w

    def _on_tab(self, idx):
        if idx == 1 and not self._scp_loaded:
            self._scp_loaded = True
            self._load_scps()

    def _load_scps(self):
        if not _SCP_INDEX: return
        self._scp_list.setUpdatesEnabled(False)
        self._scp_list.clear()
        CLASS_COL = {"safe":"#22bb44","euclid":"#f5d020","keter":"#cc3333",
                     "thaumiel":"#00d4ff","neutralized":"#888888","apollyon":"#cc00ff"}
        items = sorted(_SCP_INDEX.items())
        for key, data in items:
            tags = data.get("tags",[])
            cls  = next((t for t in tags if t.lower() in CLASS_COL), "safe")
            col  = CLASS_COL.get(cls.lower(), DIM)
            title = data.get("title","") or ""
            label = f"{key.upper():<14} {title[:40]}"
            it = QListWidgetItem(label)
            it.setData(Qt.ItemDataRole.UserRole, key)
            it.setForeground(QColor(col))
            self._scp_list.addItem(it)
        self._scp_list.setUpdatesEnabled(True)
        self._scp_count.setText(f"{len(items)} SCP")

    def _filter_scps(self, text):
        q = text.strip().lower()
        self._scp_list.setUpdatesEnabled(False)
        visible = 0
        for i in range(self._scp_list.count()):
            it = self._scp_list.item(i)
            hide = bool(q) and q not in (it.data(Qt.ItemDataRole.UserRole) or "").lower() and q not in it.text().lower()
            it.setHidden(hide)
            if not hide: visible += 1
        self._scp_list.setUpdatesEnabled(True)
        self._scp_count.setText(f"{visible} SCP")

    def _scp_clicked(self, it):
        key = it.data(Qt.ItemDataRole.UserRole)
        if not key or key not in _SCP_INDEX: return
        data = _SCP_INDEX[key]
        tags = data.get("tags",[])
        CLASS_COL = {"safe":"#22bb44","euclid":"#f5d020","keter":"#cc3333",
                     "thaumiel":"#00d4ff","neutralized":"#888888","apollyon":"#cc00ff"}
        cls     = next((t for t in tags if t.lower() in CLASS_COL), "inconnu")
        cls_col = CLASS_COL.get(cls.lower(), DIM)
        cls_norm = {"euclid":"EUCLIDE"}.get(cls.lower(), cls.upper())
        req = CLASS_NIVEAU.get(cls_norm, 1)
        if self.niveau < req:
            self._scp_detail.setHtml(
                f"<div style='font-family:{MONO};font-size:10px;'>"
                f"<span style='color:{RED};font-size:16px;font-weight:600;'>⊘ ACCÈS REFUSÉ</span><br><br>"
                f"<span style='color:{DIM};'>Classe : </span><span style='color:{cls_col};font-weight:600;'>{cls_norm}</span><br>"
                f"<span style='color:{DIM};'>Niveau requis : </span><span style='color:{WHITE};'>{req}</span></div>"
            ); return
        title = data.get("title","") or "[ REDACTED ]"
        url   = data.get("url","")
        rating = data.get("rating","?")
        other_tags = [t for t in tags if t.lower() not in CLASS_COL][:10]
        tags_html = " ".join(f"<span style='background:{BORDER};color:{DIM};padding:1px 5px;font-size:8px;'>{t}</span>" for t in other_tags)
        self._scp_detail.setHtml(f"""
<div style='font-family:{MONO};font-size:10px;line-height:1.8;'>
<span style='color:{WHITE};font-size:17px;font-weight:600;letter-spacing:2px;'>{key.upper()}</span><br>
<span style='color:{DIM};'>{title}</span><br><br>
<span style='color:{cls_col};font-size:15px;font-weight:600;letter-spacing:3px;'>{cls_norm}</span><br><br>
<span style='color:{DIM};'>Rating : </span><span style='color:{YELLOW};'>+{rating}</span><br><br>
{tags_html}<br><br>
<span style='color:{CYAN};'>{url}</span></div>""")

    def _is_hidden(self, path: Path) -> bool:
        if path.name.startswith("."): return True
        if platform.system() == "Windows":
            try:
                import ctypes
                attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
                if attrs != -1 and (attrs & 2): return True
            except: pass
        return False

    def _refresh(self):
        self.flist.setUpdatesEnabled(False); self.flist.clear()
        try:
            if self.cur.parent != self.cur:
                it = QListWidgetItem("  ↑  ..")
                it.setData(Qt.ItemDataRole.UserRole, str(self.cur.parent))
                it.setForeground(QColor(CYAN)); self.flist.addItem(it)
            try: entries = sorted(self.cur.iterdir(), key=lambda p:(not p.is_dir(),p.name.lower()))
            except PermissionError: return
            for e in entries:
                hidden = self._is_hidden(e)
                if hidden and not self._show_hidden: continue
                if e.is_dir():
                    label = f"  📁  {e.name}/"; col = QColor("#556677") if hidden else QColor(DIM)
                elif e.suffix.lower() in (".txt",".md",".docx",".doc"):
                    label = f"  📄  {e.name}"; col = QColor(DIM) if hidden else QColor(WHITE)
                else: continue
                it = QListWidgetItem(label)
                it.setData(Qt.ItemDataRole.UserRole, str(e))
                it.setForeground(col); self.flist.addItem(it)
        finally: self.flist.setUpdatesEnabled(True)

    def _click(self, it):
        p = Path(it.data(Qt.ItemDataRole.UserRole))
        if p.is_file(): self._open(p)

    def _dclick(self, it):
        p = Path(it.data(Qt.ItemDataRole.UserRole))
        if p.is_dir():
            self.cur = p; self.path_lbl.setText(str(p))
            self._save_state(); self._refresh()

    def _choose(self):
        d = QFileDialog.getExistingDirectory(self, "Dossier RP", str(self.cur))
        if d: self.cur = Path(d); self.path_lbl.setText(d); self._save_state(); self._refresh()

    def _detect_class(self, text: str):
        for pat in [r"classe\s*(?:de\s+confinement)?\s*[:\-]\s*(\w+)",
                    r"object\s+class\s*[:\-]\s*(\w+)", r"class\s*[:\-]\s*(\w+)"]:
            m = re.search(pat, text.lower())
            if m:
                raw = m.group(1).upper()
                norm = {"EUCLID":"EUCLIDE","APOLLYON":"THAUMIEL"}.get(raw,raw)
                req = CLASS_NIVEAU.get(norm)
                if req: return norm, req
        for cls in ["THAUMIEL","APOLLYON","KETER","EUCLIDE","EUCLID","SAFE","NEUTRALIZED"]:
            if cls in text.upper():
                norm = {"EUCLID":"EUCLIDE","APOLLYON":"THAUMIEL"}.get(cls,cls)
                return norm, CLASS_NIVEAU.get(norm,1)
        return None, 1

    def _open(self, path: Path):
        self.file_title.setText(path.name.upper())
        self._last_file = str(path); self._save_state()
        suffix = path.suffix.lower()
        try:
            if suffix in (".txt",".md"):
                text = None
                for enc in ("utf-8","utf-8-sig","latin-1","cp1252"):
                    try: text = path.read_text(encoding=enc); break
                    except: continue
                if text is None: text = path.read_bytes().decode("utf-8",errors="replace")
                self._render(text)
            elif suffix in (".docx",".doc"):
                try:
                    import docx; doc = docx.Document(str(path))
                    lines = []
                    for para in doc.paragraphs:
                        if para.style.name.startswith("Heading"): lines.append(f"\n=== {para.text.upper()} ===")
                        else: lines.append(para.text)
                    self._render("\n".join(lines))
                except ImportError: self._render("[python-docx non installé]\npip install python-docx")
                except Exception as e: self._render(f"[Erreur .docx]\n{e}")
            else: self._render(f"[Format non supporté : {suffix}]")
        except Exception as e: self._render(f"[Erreur]\n{e}")

    def _render(self, text: str):
        detected_class, req = self._detect_class(text)
        if detected_class and self.niveau < req:
            import random; rng = random.Random(42)
            redacted = "<br>".join(f"<span style='color:{DARK};'>{'█'*rng.randint(12,55)}</span>" for _ in range(18))
            self.viewer.setHtml(f"<div style='font-family:{MONO};font-size:11px;'>"
                f"<span style='color:{RED};font-size:18px;font-weight:600;'>⊘  ACCÈS REFUSÉ</span><br><br>{redacted}</div>"); return
        lines = []
        for line in text.splitlines():
            e = line.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            if e.startswith("==="): c = CYAN
            elif "KETER" in e.upper(): c = RED
            elif any(k in e.upper() for k in ["EUCLIDE","EUCLID"]): c = YELLOW
            elif any(k in e.upper() for k in ["SAFE","THAUMIEL","NEUTRALIZED"]): c = GREEN
            elif "APOLLYON" in e.upper(): c = "#cc00ff"
            elif "██" in e or "REDACTED" in e: c = DARK
            else: c = WHITE
            lines.append(f"<span style='color:{c};'>{e}</span>")
        self.viewer.setHtml(f"<div style='font-family:{MONO};font-size:11px;line-height:1.65;'>"+"<br>".join(lines)+"</div>")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    load_barlow()
    login, niveau, nom_affiche = check_clearance("Fichiers")
    win = ScipnetWindow("Fichiers", login, niveau, nom_affiche, width=1000, height=650)
    widget = FilesWidget(login, niveau)
    win.set_content(widget)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
