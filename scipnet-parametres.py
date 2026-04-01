"""
SCiPNET — Paramètres v1.0
App standalone — nécessite une session active (session.dat)
"""
import sys, platform
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLabel, QPushButton, QLineEdit,
    QStackedWidget, QListWidget, QListWidgetItem, QComboBox, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

sys.path.insert(0, "/opt/scipnet")
from scipnet_common import (
    BG, BG2, BG3, WIN_BG, BORDER, BORDER_B,
    WHITE, DIM, DARK, CYAN, CYAN_D, RED, YELLOW, GREEN,
    MONO, NIVEAU_LABELS, NIVEAU_COLORS,
    F, S, hsep, DataStore, ScipnetWindow, check_clearance, load_barlow,
    load_users, clear_session,
)

USERS: dict = {}


class SettingsWidget(QWidget):
    def __init__(self, login: str, niveau: int, parent=None):
        super().__init__(parent)
        self.login  = login
        self.niveau = niveau
        global USERS
        USERS = load_users()
        self._build()

    def _build(self):
        self.setStyleSheet(f"background:{WIN_BG};")
        root = QHBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        # Sidebar
        sidebar = QWidget(); sidebar.setFixedWidth(180)
        sidebar.setStyleSheet(f"background:{BG2};border-right:1px solid {BORDER};")
        sv = QVBoxLayout(sidebar); sv.setContentsMargins(0,16,0,16); sv.setSpacing(2)
        sv.addWidget(QLabel("  PARAMÈTRES",
            styleSheet=f"color:{DIM};font-family:'{MONO}';font-size:8px;"
                       f"letter-spacing:3px;background:transparent;padding:0 0 10px 12px;"))

        self._stack = QStackedWidget()
        self._nav_btns = []

        sections = [
            ("⊙  Compte",    self._make_compte()),
            ("◈  Affichage", self._make_affichage()),
            ("⚙  Système",   self._make_systeme()),
            ("ℹ  À propos",  self._make_apropos()),
        ]
        if self.niveau >= 5:
            sections.insert(2, ("◉  Comptes", self._make_comptes()))

        for i, (label, widget) in enumerate(sections):
            btn = QPushButton(label); btn.setCheckable(True)
            btn.setStyleSheet(
                f"QPushButton{{background:transparent;color:{DIM};font-family:'{MONO}';"
                f"font-size:10px;letter-spacing:1px;text-align:left;padding:10px 16px;"
                f"border:none;border-left:2px solid transparent;}}"
                f"QPushButton:hover{{color:{WHITE};background:{BG3};}}"
                f"QPushButton:checked{{color:{WHITE};border-left:2px solid {CYAN};background:{BG3};}}"
            )
            btn.clicked.connect(lambda _, idx=i: self._switch(idx))
            sv.addWidget(btn); self._nav_btns.append(btn)
            self._stack.addWidget(widget)

        sv.addStretch(); root.addWidget(sidebar); root.addWidget(self._stack, 1)
        self._switch(0)

    def _switch(self, idx):
        self._stack.setCurrentIndex(idx)
        for i, b in enumerate(self._nav_btns): b.setChecked(i == idx)

    def _section_title(self, title):
        w = QWidget(); w.setStyleSheet(f"background:{BG2};border-bottom:1px solid {BORDER};")
        h = QHBoxLayout(w); h.setContentsMargins(20,12,20,12)
        h.addWidget(QLabel(title, styleSheet=S(WHITE,13,bold=True,ls=3))); return w

    def _row(self, label, value_widget=None, hint=""):
        w = QWidget(); w.setStyleSheet(f"background:transparent;border-bottom:1px solid {BORDER};")
        h = QHBoxLayout(w); h.setContentsMargins(20,12,20,12); h.setSpacing(12)
        lv = QVBoxLayout(); lv.setSpacing(2)
        lv.addWidget(QLabel(label, styleSheet=S(WHITE,10,ls=1)))
        if hint: lv.addWidget(QLabel(hint, styleSheet=S(DIM,8,ls=0)))
        h.addLayout(lv, 1)
        if value_widget: h.addWidget(value_widget)
        return w

    def _val(self, text, color=DIM):
        return QLabel(text, styleSheet=S(color,10,ls=1))

    # ── Compte ────────────────────────────────────────────────────────────────
    def _make_compte(self):
        w = QWidget(); w.setStyleSheet(f"background:{WIN_BG};")
        v = QVBoxLayout(w); v.setContentsMargins(0,0,0,0); v.setSpacing(0)
        v.addWidget(self._section_title("COMPTE"))
        v.addWidget(self._row("Identifiant", self._val(self.login.upper(), WHITE)))
        v.addWidget(self._row("Niveau de clairance",
            self._val(f"NIVEAU {self.niveau} — {NIVEAU_LABELS.get(self.niveau,'?')}",
                      NIVEAU_COLORS.get(self.niveau, DIM))))
        v.addWidget(self._row("Statut session", self._val("ACTIVE", GREEN)))

        cfg = DataStore.load("config.dat", {})
        site = cfg.get("site_name", "AYIN")
        v.addWidget(self._row("Site d'affectation", self._val(f"SITE-{site}", DIM)))

        # Changer mot de passe
        mdp_w = QWidget(); mdp_w.setStyleSheet("background:transparent;")
        mdp_h = QHBoxLayout(mdp_w); mdp_h.setContentsMargins(0,0,0,0); mdp_h.setSpacing(6)
        self._mdp_old = QLineEdit(); self._mdp_old.setPlaceholderText("Actuel")
        self._mdp_old.setEchoMode(QLineEdit.EchoMode.Password)
        self._mdp_new = QLineEdit(); self._mdp_new.setPlaceholderText("Nouveau")
        self._mdp_new.setEchoMode(QLineEdit.EchoMode.Password)
        for f in [self._mdp_old, self._mdp_new]:
            f.setFixedWidth(120)
            f.setStyleSheet(
                f"QLineEdit{{background:{BG3};color:{WHITE};font-family:'{MONO}';"
                f"font-size:10px;border:1px solid {BORDER};padding:3px 6px;}}"
                f"QLineEdit:focus{{border:1px solid {CYAN};}}"
            )
            pal = f.palette(); pal.setColor(pal.ColorRole.Text, QColor(WHITE))
            pal.setColor(pal.ColorRole.Base, QColor(BG3)); f.setPalette(pal)
            mdp_h.addWidget(f)
        chg_btn = QPushButton("CHANGER")
        chg_btn.setStyleSheet(
            f"QPushButton{{background:{BG3};color:{CYAN};font-family:'{MONO}';"
            f"font-size:9px;letter-spacing:2px;padding:4px 10px;border:1px solid {BORDER_B};}}"
            f"QPushButton:hover{{background:{CYAN};color:{BG};}}"
        )
        chg_btn.clicked.connect(self._change_mdp)
        mdp_h.addWidget(chg_btn)
        self._mdp_msg = QLabel(); self._mdp_msg.setStyleSheet(S(GREEN,8,ls=0))
        mdp_h.addWidget(self._mdp_msg)
        v.addWidget(self._row("Mot de passe", mdp_w, "Changer le mot de passe du compte"))

        logout_btn = QPushButton("  DÉCONNEXION")
        logout_btn.setStyleSheet(
            f"QPushButton{{background:{BG3};color:{RED};font-family:'{MONO}';"
            f"font-size:9px;letter-spacing:2px;padding:7px 16px;border:1px solid {RED};}}"
            f"QPushButton:hover{{background:{RED};color:{BG};}}"
        )
        logout_btn.clicked.connect(self._logout)
        v.addWidget(self._row("Session", logout_btn, "Ferme la session en cours"))
        v.addStretch(); return w

    def _change_mdp(self):
        old = self._mdp_old.text()
        new = self._mdp_new.text()
        users = load_users()
        login = self.login.lower()
        if login not in users:
            self._mdp_msg.setStyleSheet(S(RED,8,ls=0))
            self._mdp_msg.setText("Compte introuvable"); return
        if not DataStore.check_mdp(old, users[login].get("mdp","")):
            self._mdp_msg.setStyleSheet(S(RED,8,ls=0))
            self._mdp_msg.setText("Mot de passe incorrect"); return
        if len(new) < 4:
            self._mdp_msg.setStyleSheet(S(RED,8,ls=0))
            self._mdp_msg.setText("Trop court (min 4 chars)"); return
        users[login]["mdp"] = DataStore.hash_mdp(new)
        DataStore.save("users.dat", users)
        self._mdp_msg.setStyleSheet(S(GREEN,8,ls=0))
        self._mdp_msg.setText("✓ Modifié")
        self._mdp_old.clear(); self._mdp_new.clear()

    def _logout(self):
        clear_session()
        self.window().close()

    # ── Affichage ─────────────────────────────────────────────────────────────
    def _make_affichage(self):
        w = QWidget(); w.setStyleSheet(f"background:{WIN_BG};")
        v = QVBoxLayout(w); v.setContentsMargins(0,0,0,0); v.setSpacing(0)
        v.addWidget(self._section_title("AFFICHAGE"))

        cfg = DataStore.load("config.dat",{})
        site_w = QWidget(); site_w.setStyleSheet("background:transparent;")
        site_h = QHBoxLayout(site_w); site_h.setContentsMargins(0,0,0,0); site_h.setSpacing(6)
        self._site_inp = QLineEdit(cfg.get("site_name","AYIN"))
        self._site_inp.setFixedWidth(180)
        self._site_inp.setStyleSheet(
            f"QLineEdit{{background:{BG3};color:{WHITE};font-family:'{MONO}';"
            f"font-size:11px;border:1px solid {BORDER_B};padding:3px 8px;}}"
            f"QLineEdit:focus{{border:1px solid {CYAN};}}"
        )
        pal = self._site_inp.palette(); pal.setColor(pal.ColorRole.Text, QColor(WHITE))
        pal.setColor(pal.ColorRole.Base, QColor(BG3)); self._site_inp.setPalette(pal)
        apply_btn = QPushButton("APPLIQUER")
        apply_btn.setStyleSheet(
            f"QPushButton{{background:{BG3};color:{CYAN};font-family:'{MONO}';"
            f"font-size:9px;letter-spacing:2px;padding:5px 12px;border:1px solid {BORDER_B};}}"
            f"QPushButton:hover{{background:{CYAN};color:{BG};}}"
        )
        def _apply():
            val = self._site_inp.text().strip().upper()
            if val:
                cfg2 = DataStore.load("config.dat",{})
                cfg2["site_name"] = val
                DataStore.save("config.dat", cfg2)
        apply_btn.clicked.connect(_apply)
        site_h.addWidget(self._site_inp); site_h.addWidget(apply_btn)
        v.addWidget(self._row("Nom du site", site_w, "Remplace le nom du site dans toute l'interface"))
        v.addWidget(self._row("Thème",    self._val("SCiPNET DARK", DIM), "Seul thème disponible"))
        v.addWidget(self._row("Police",   self._val(MONO, DIM)))
        v.addStretch(); return w

    # ── Gestion des comptes (admin N5) ────────────────────────────────────────
    def _make_comptes(self):
        w = QWidget(); w.setStyleSheet(f"background:{WIN_BG};")
        v = QVBoxLayout(w); v.setContentsMargins(0,0,0,0); v.setSpacing(0)
        v.addWidget(self._section_title("GESTION DES COMPTES"))

        body = QWidget(); bv = QVBoxLayout(body); bv.setContentsMargins(20,12,20,12); bv.setSpacing(10)

        self._user_list = QListWidget()
        self._user_list.setStyleSheet(
            f"QListWidget{{background:{BG2};color:{WHITE};font-family:'{MONO}';"
            f"font-size:10px;border:1px solid {BORDER};padding:4px;}}"
            f"QListWidget::item{{padding:6px 10px;border-bottom:1px solid {BORDER};}}"
            f"QListWidget::item:selected{{background:{BORDER_B};}}"
        )
        self._user_list.setFont(F(10)); self._user_list.setFixedHeight(180)
        self._user_list.itemClicked.connect(self._on_user_select)
        bv.addWidget(self._user_list)

        form = QFrame(); form.setStyleSheet(f"QFrame{{background:{BG3};border:1px solid {BORDER};}}")
        fv = QVBoxLayout(form); fv.setContentsMargins(14,10,14,10); fv.setSpacing(8)
        fv.addWidget(QLabel("NOUVEAU / MODIFIER COMPTE", styleSheet=S(DIM,8,bold=True,ls=3)))

        def mk_field(lbl, ph="", pwd=False):
            row = QHBoxLayout(); row.setSpacing(8)
            l = QLabel(f"{lbl:<16}"); l.setStyleSheet(S(DIM,9,ls=1)); l.setFixedWidth(110)
            f = QLineEdit(); f.setPlaceholderText(ph)
            if pwd: f.setEchoMode(QLineEdit.EchoMode.Password)
            f.setStyleSheet(
                f"QLineEdit{{background:{BG2};color:{WHITE};font-family:'{MONO}';"
                f"font-size:10px;border:1px solid {BORDER};padding:4px 8px;}}"
                f"QLineEdit:focus{{border:1px solid {CYAN};}}"
            )
            pal = f.palette(); pal.setColor(pal.ColorRole.Text, QColor(WHITE))
            pal.setColor(pal.ColorRole.Base, QColor(BG2)); f.setPalette(pal)
            row.addWidget(l); row.addWidget(f, 1); return row, f

        r1, self._f_login = mk_field("Identifiant",   "ex: agent.smith")
        r2, self._f_mdp   = mk_field("Mot de passe",  "vide = inchangé", pwd=True)
        fv.addLayout(r1); fv.addLayout(r2)

        niv_row = QHBoxLayout(); niv_row.setSpacing(8)
        niv_lbl = QLabel("Niveau clairance"); niv_lbl.setStyleSheet(S(DIM,9,ls=1)); niv_lbl.setFixedWidth(110)
        self._f_niveau = QComboBox()
        self._f_niveau.setStyleSheet(
            f"QComboBox{{background:{BG2};color:{WHITE};font-family:'{MONO}';"
            f"font-size:10px;border:1px solid {BORDER};padding:4px 8px;}}"
            f"QComboBox QAbstractItemView{{background:{BG2};color:{WHITE};"
            f"border:1px solid {BORDER};selection-background-color:{CYAN_D};}}"
        )
        for niv, lbl in NIVEAU_LABELS.items():
            self._f_niveau.addItem(f"N{niv} — {lbl}", userData=niv)
        niv_row.addWidget(niv_lbl); niv_row.addWidget(self._f_niveau, 1); fv.addLayout(niv_row)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        def mk_btn(txt, col, cb):
            b = QPushButton(txt)
            b.setStyleSheet(
                f"QPushButton{{background:{BG2};color:{col};font-family:'{MONO}';"
                f"font-size:8px;letter-spacing:2px;padding:6px 14px;border:1px solid {BORDER_B};}}"
                f"QPushButton:hover{{background:{col};color:{BG};}}"
            )
            b.clicked.connect(cb); return b
        btn_row.addWidget(mk_btn("  CRÉER / MAJ", CYAN, self._user_save))
        btn_row.addWidget(mk_btn("  SUPPRIMER",   RED,  self._user_delete))
        btn_row.addWidget(mk_btn("  EFFACER",     DIM,  self._user_clear))
        btn_row.addStretch(); fv.addLayout(btn_row)

        self._user_msg = QLabel(); self._user_msg.setStyleSheet(S(GREEN,8,ls=1))
        self._user_msg.setWordWrap(True); fv.addWidget(self._user_msg)
        bv.addWidget(form); v.addWidget(body, 1)
        self._refresh_user_list(); return w

    def _refresh_user_list(self):
        users = load_users()
        self._user_list.clear()
        for login, u in sorted(users.items()):
            niv = u.get("niveau",1)
            col = NIVEAU_COLORS.get(niv, DIM)
            it = QListWidgetItem(f"  {login:<20} N{niv} — {NIVEAU_LABELS.get(niv,'?')}")
            it.setForeground(QColor(col)); self._user_list.addItem(it)

    def _on_user_select(self, it):
        login = it.text().strip().split()[0]
        self._f_login.setText(login)
        users = load_users()
        if login in users:
            niv = users[login].get("niveau",1)
            for i in range(self._f_niveau.count()):
                if self._f_niveau.itemData(i) == niv:
                    self._f_niveau.setCurrentIndex(i); break

    def _user_save(self):
        login = self._f_login.text().strip().lower()
        if not login: return
        users = load_users()
        mdp = self._f_mdp.text()
        niv = self._f_niveau.currentData()
        if login not in users:
            if not mdp:
                self._user_msg.setStyleSheet(S(RED,8,ls=1))
                self._user_msg.setText("Mot de passe requis pour un nouveau compte"); return
            users[login] = {"mdp": DataStore.hash_mdp(mdp), "niveau": niv}
        else:
            users[login]["niveau"] = niv
            if mdp: users[login]["mdp"] = DataStore.hash_mdp(mdp)
        DataStore.save("users.dat", users)
        self._refresh_user_list(); self._user_clear()
        self._user_msg.setStyleSheet(S(GREEN,8,ls=1))
        self._user_msg.setText(f"Compte '{login}' sauvegardé.")

    def _user_delete(self):
        login = self._f_login.text().strip().lower()
        if login == "admin":
            self._user_msg.setStyleSheet(S(RED,8,ls=1))
            self._user_msg.setText("Impossible de supprimer 'admin'."); return
        users = load_users()
        if login in users:
            del users[login]; DataStore.save("users.dat", users)
            self._refresh_user_list(); self._user_clear()
            self._user_msg.setStyleSheet(S(YELLOW,8,ls=1))
            self._user_msg.setText(f"Compte '{login}' supprimé.")
        else:
            self._user_msg.setStyleSheet(S(RED,8,ls=1))
            self._user_msg.setText(f"Compte '{login}' introuvable.")

    def _user_clear(self):
        self._f_login.clear(); self._f_mdp.clear()
        self._f_niveau.setCurrentIndex(0); self._user_msg.clear()

    # ── Système ───────────────────────────────────────────────────────────────
    def _make_systeme(self):
        w = QWidget(); w.setStyleSheet(f"background:{WIN_BG};")
        v = QVBoxLayout(w); v.setContentsMargins(0,0,0,0); v.setSpacing(0)
        v.addWidget(self._section_title("SYSTÈME"))
        v.addWidget(self._row("OS",          self._val("SCiPNET OS v5.1", WHITE)))
        v.addWidget(self._row("Plateforme",  self._val(f"{platform.system()} {platform.release()}", DIM)))
        v.addWidget(self._row("Python",      self._val(sys.version.split()[0], DIM)))
        v.addWidget(self._row("API SCP",     self._val("scp-data.tedivm.com", CYAN),
                              "Données SCP en temps réel"))
        v.addStretch(); return w

    # ── À propos ──────────────────────────────────────────────────────────────
    def _make_apropos(self):
        w = QWidget(); w.setStyleSheet(f"background:{WIN_BG};")
        v = QVBoxLayout(w); v.setContentsMargins(0,0,0,0); v.setSpacing(0)
        v.addWidget(self._section_title("À PROPOS"))
        txt = QTextEdit(); txt.setReadOnly(True)
        txt.setStyleSheet(f"background:transparent;color:{DIM};font-family:'{MONO}';font-size:10px;border:none;padding:20px;")
        txt.setFont(F(10))
        txt.setHtml(f"""
<div style='font-family:{MONO};font-size:10px;line-height:1.8;color:{DIM};'>
<span style='color:{CYAN};font-size:16px;font-weight:600;letter-spacing:3px;'>SCiPNET OS</span><br>
<span style='color:{WHITE};'>Version 5.1 — Edition Linux</span><br><br>
<span style='color:{BORDER_B};'>{'─'*40}</span><br><br>
<span style='color:{WHITE};'>SYSTÈME D'EXPLOITATION SÉCURISÉ</span><br>
Fondation SCP — Usage interne uniquement<br><br>
Composants : PyQt6, cryptography, scp-data.tedivm.com<br><br>
<span style='color:{RED};'>AVERTISSEMENT</span><br>
Accès réservé au personnel autorisé.<br>
Toute tentative d'intrusion sera consignée<br>
et transmise au Bureau de Sécurité O5.
</div>""")
        v.addWidget(txt, 1); return w


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    load_barlow()
    login, niveau, nom_affiche = check_clearance("Paramètres")
    win = ScipnetWindow("Paramètres", login, niveau, nom_affiche, width=800, height=580)
    widget = SettingsWidget(login, niveau)
    win.set_content(widget)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
