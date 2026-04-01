"""
SCiPNET — Messagerie v1.0
Messagerie interne SCiPNET.
Adresse : titre.nom@site-xxxx.scipnet.scpf
Transport : fichiers dans ~/.scipnet/messages/
"""
import sys, os, json, threading, time, hashlib
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit,
    QListWidget, QListWidgetItem, QSplitter,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QTextCursor

sys.path.insert(0, "/opt/scipnet")
from scipnet_common import (
    BG, BG2, BG3, WIN_BG, BORDER, BORDER_B,
    WHITE, DIM, DARK, CYAN, CYAN_D, RED, YELLOW, GREEN,
    MONO, NIVEAU_LABELS, NIVEAU_COLORS,
    F, S, hsep, DataStore, ScipnetWindow, check_clearance, load_barlow,
)

def make_address(session: dict) -> str:
    titre = session.get("titre", "").lower().replace(" ", "-")
    nom   = session.get("nom", session.get("login", "agent")).lower()
    nom   = nom.replace(" ", "-").replace(".", "-")
    cfg   = DataStore.load("config.dat", {})
    site  = cfg.get("site_name", session.get("site", "ayin")).lower()
    if titre:
        return f"{titre}.{nom}@site-{site}.scipnet.scpf"
    return f"{nom}@site-{site}.scipnet.scpf"

class MessageStore:
    @classmethod
    def dir(cls) -> Path:
        d = DataStore.dir() / "messages"
        d.mkdir(exist_ok=True)
        return d

    @classmethod
    def inbox_dir(cls, address: str) -> Path:
        safe = address.replace("@","_at_").replace(".","-")
        d = cls.dir() / safe
        d.mkdir(exist_ok=True)
        return d

    @classmethod
    def send(cls, from_addr, to_addr, subject, body) -> bool:
        msg = {
            "id"     : hashlib.md5(f"{time.time()}{from_addr}".encode()).hexdigest()[:8],
            "from"   : from_addr, "to": to_addr,
            "subject": subject, "body": body,
            "date"   : datetime.now().isoformat(), "read": False,
        }
        try:
            ts = int(time.time()*1000)
            path = cls.inbox_dir(to_addr) / f"{ts}_{msg['id']}.json"
            path.write_text(json.dumps(msg, ensure_ascii=False, indent=2), encoding="utf-8")
            sent = cls.inbox_dir(from_addr+".sent")
            (sent/f"{ts}_{msg['id']}.json").write_text(
                json.dumps(msg, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except Exception as e:
            print(f"Erreur envoi: {e}"); return False

    @classmethod
    def get_inbox(cls, address, sent=False) -> list:
        d = cls.inbox_dir(address+(".sent" if sent else ""))
        msgs = []
        for f in sorted(d.glob("*.json"), reverse=True):
            try: msgs.append(json.loads(f.read_text(encoding="utf-8")))
            except: pass
        return msgs

    @classmethod
    def mark_read(cls, address, msg_id):
        for f in cls.inbox_dir(address).glob(f"*_{msg_id}.json"):
            try:
                m = json.loads(f.read_text()); m["read"] = True
                f.write_text(json.dumps(m, ensure_ascii=False, indent=2))
            except: pass

    @classmethod
    def delete(cls, address, msg_id):
        for f in cls.inbox_dir(address).glob(f"*_{msg_id}.json"):
            try: f.unlink()
            except: pass

    @classmethod
    def count_unread(cls, address) -> int:
        return sum(1 for m in cls.get_inbox(address) if not m.get("read", True))


class MessageList(QWidget):
    message_selected = pyqtSignal(dict)
    compose_sig      = pyqtSignal()

    def __init__(self, address, parent=None):
        super().__init__(parent)
        self.address = address
        self._sent = False
        self._build()
        self.refresh()

    def _build(self):
        self.setStyleSheet(f"background:{BG2};")
        v = QVBoxLayout(self); v.setContentsMargins(0,0,0,0); v.setSpacing(0)
        tab = QWidget(); tab.setFixedHeight(36)
        tab.setStyleSheet(f"background:{BG3};border-bottom:1px solid {BORDER};")
        th = QHBoxLayout(tab); th.setContentsMargins(8,0,8,0); th.setSpacing(4)
        self._ib = QPushButton("📥  REÇUS"); self._sb = QPushButton("📤  ENVOYÉS")
        for b in [self._ib, self._sb]:
            b.setCheckable(True)
            b.setStyleSheet(
                f"QPushButton{{background:transparent;color:{DIM};font-family:'{MONO}';"
                f"font-size:9px;letter-spacing:2px;padding:4px 10px;border:none;"
                f"border-bottom:2px solid transparent;}}"
                f"QPushButton:checked{{color:{CYAN};border-bottom:2px solid {CYAN};}}"
                f"QPushButton:hover{{color:{WHITE};}}")
        self._ib.setChecked(True)
        self._ib.clicked.connect(lambda: self._switch(False))
        self._sb.clicked.connect(lambda: self._switch(True))
        th.addWidget(self._ib); th.addWidget(self._sb); th.addStretch()
        cb = QPushButton("✉  NOUVEAU")
        cb.setStyleSheet(
            f"QPushButton{{background:{CYAN_D};color:{CYAN};font-family:'{MONO}';"
            f"font-size:9px;letter-spacing:2px;padding:4px 10px;border:1px solid {CYAN};}}"
            f"QPushButton:hover{{background:{CYAN};color:{BG};}}")
        cb.clicked.connect(self.compose_sig.emit)
        th.addWidget(cb); v.addWidget(tab)
        self._list = QListWidget()
        self._list.setStyleSheet(
            f"QListWidget{{background:{BG2};color:{WHITE};font-family:'{MONO}';"
            f"font-size:10px;border:none;padding:4px;}}"
            f"QListWidget::item{{padding:8px 10px;border-bottom:1px solid {BORDER};}}"
            f"QListWidget::item:selected{{background:{BORDER_B};}}"
            f"QListWidget::item:hover{{background:{BG3};}}")
        self._list.setFont(F(10))
        self._list.itemClicked.connect(self._on_select)
        v.addWidget(self._list, 1)
        self._status = QLabel(); self._status.setStyleSheet(S(DARK,8,ls=1))
        self._status.setContentsMargins(10,4,10,4); v.addWidget(self._status)

    def _switch(self, sent):
        self._sent = sent
        self._ib.setChecked(not sent); self._sb.setChecked(sent)
        self.refresh()

    def refresh(self):
        self._list.clear()
        msgs = MessageStore.get_inbox(self.address, sent=self._sent)
        for msg in msgs:
            is_read = msg.get("read", False)
            date    = msg.get("date","")[:16].replace("T"," ")
            who     = msg.get("from","?") if not self._sent else msg.get("to","?")
            subj    = msg.get("subject","(sans objet)")
            prefix  = "  " if is_read else "● "
            item = QListWidgetItem(f"{prefix}{who[:28]}\n  {subj[:32]}  —  {date}")
            item.setData(Qt.ItemDataRole.UserRole, msg)
            item.setForeground(QColor(DIM if is_read else WHITE))
            if not is_read: item.setFont(F(10, bold=True))
            self._list.addItem(item)
        unread = MessageStore.count_unread(self.address)
        self._status.setText(
            f"{len(msgs)} message{'s' if len(msgs)>1 else ''}  —  "
            f"{unread} non lu{'s' if unread>1 else ''}")

    def _on_select(self, item):
        msg = item.data(Qt.ItemDataRole.UserRole)
        if msg:
            MessageStore.mark_read(self.address, msg.get("id",""))
            item.setForeground(QColor(DIM)); item.setFont(F(10))
            item.setText(item.text().replace("● ","  ",1))
            self.message_selected.emit(msg)


class MessageViewer(QWidget):
    reply_sig  = pyqtSignal(str, str)
    delete_sig = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._msg = {}; self._build()

    def _build(self):
        self.setStyleSheet(f"background:{WIN_BG};")
        v = QVBoxLayout(self); v.setContentsMargins(0,0,0,0); v.setSpacing(0)
        hdr = QWidget(); hdr.setStyleSheet(f"background:{BG3};border-bottom:1px solid {BORDER};")
        hv = QVBoxLayout(hdr); hv.setContentsMargins(16,12,16,12); hv.setSpacing(4)
        self._subj = QLabel("—"); self._subj.setStyleSheet(S(WHITE,13,bold=True,ls=1))
        self._from = QLabel(""); self._from.setStyleSheet(S(DIM,9,ls=1))
        self._date = QLabel(""); self._date.setStyleSheet(S(DARK,8,ls=0))
        hv.addWidget(self._subj); hv.addWidget(self._from); hv.addWidget(self._date)
        btn_bar = QWidget(); btn_bar.setStyleSheet(f"background:{BG2};border-bottom:1px solid {BORDER};")
        bh = QHBoxLayout(btn_bar); bh.setContentsMargins(12,6,12,6); bh.setSpacing(8)
        def mkb(t,c,cb):
            b=QPushButton(t); b.setStyleSheet(
                f"QPushButton{{background:transparent;color:{c};font-family:'{MONO}';"
                f"font-size:9px;letter-spacing:2px;padding:4px 10px;border:1px solid {c};}}"
                f"QPushButton:hover{{background:{c};color:{BG};}}")
            b.clicked.connect(cb); return b
        self._rb = mkb("↩  RÉPONDRE", CYAN, self._reply)
        self._db = mkb("✕  SUPPRIMER", RED, self._delete)
        bh.addWidget(self._rb); bh.addWidget(self._db); bh.addStretch()
        v.addWidget(hdr); v.addWidget(btn_bar)
        self._body = QTextEdit(); self._body.setReadOnly(True)
        self._body.setStyleSheet(
            f"background:{WIN_BG};color:{WHITE};font-family:'{MONO}';"
            f"font-size:11px;border:none;padding:20px;")
        self._body.setFont(F(11))
        bp = self._body.palette()
        bp.setColor(bp.ColorRole.Text, QColor(WHITE))
        bp.setColor(bp.ColorRole.Base, QColor(WIN_BG))
        self._body.setPalette(bp)
        v.addWidget(self._body, 1)
        self._body.setHtml(
            f"<div style='color:{DARK};font-family:{MONO};font-size:11px;"
            f"text-align:center;margin-top:80px;'>Sélectionnez un message.</div>")
        self._rb.setEnabled(False); self._db.setEnabled(False)

    def show_message(self, msg):
        self._msg = msg
        self._subj.setText(msg.get("subject","(sans objet)"))
        self._from.setText(f"De : {msg.get('from','?')}  →  À : {msg.get('to','?')}")
        self._date.setText(msg.get("date","")[:16].replace("T"," "))
        body = msg.get("body","").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\n","<br>")
        sep = f"<span style='color:{BORDER_B};'>{'─'*60}</span>"
        self._body.setHtml(
            f"<div style='font-family:{MONO};font-size:11px;line-height:1.8;'>"
            f"{sep}<br><br>{body}</div>")
        self._rb.setEnabled(True); self._db.setEnabled(True)

    def _reply(self):
        if self._msg:
            self.reply_sig.emit(self._msg.get("from",""), "Re: "+self._msg.get("subject",""))

    def _delete(self):
        if self._msg:
            self.delete_sig.emit(self._msg.get("id",""))
            self._msg = {}
            self._body.setHtml(f"<div style='color:{DARK};font-family:{MONO};font-size:11px;"
                               f"text-align:center;margin-top:80px;'>Message supprimé.</div>")
            self._rb.setEnabled(False); self._db.setEnabled(False)


class ComposeWidget(QWidget):
    sent_sig   = pyqtSignal()
    cancel_sig = pyqtSignal()

    def __init__(self, from_addr, to_addr="", subject="", parent=None):
        super().__init__(parent)
        self.from_addr = from_addr; self._build(to_addr, subject)

    def _build(self, to_addr, subject):
        self.setStyleSheet(f"background:{WIN_BG};")
        v = QVBoxLayout(self); v.setContentsMargins(0,0,0,0); v.setSpacing(0)
        hdr = QWidget(); hdr.setFixedHeight(40)
        hdr.setStyleSheet(f"background:{BG3};border-bottom:1px solid {BORDER};")
        hh = QHBoxLayout(hdr); hh.setContentsMargins(16,0,16,0)
        hh.addWidget(QLabel("NOUVEAU MESSAGE", styleSheet=S(CYAN,10,bold=True,ls=3)))
        hh.addStretch()
        cl = QPushButton("✕  ANNULER"); cl.setStyleSheet(
            f"QPushButton{{background:transparent;color:{DARK};font-family:'{MONO}';"
            f"font-size:9px;letter-spacing:2px;border:none;padding:4px 8px;}}"
            f"QPushButton:hover{{color:{RED};}}")
        cl.clicked.connect(self.cancel_sig.emit); hh.addWidget(cl); v.addWidget(hdr)
        form = QWidget(); form.setStyleSheet(f"background:{BG2};border-bottom:1px solid {BORDER};")
        fv = QVBoxLayout(form); fv.setContentsMargins(16,8,16,8); fv.setSpacing(6)
        def row(lbl, w):
            r=QHBoxLayout(); r.setSpacing(10)
            l=QLabel(lbl); l.setStyleSheet(S(DIM,9,ls=2)); l.setFixedWidth(60)
            r.addWidget(l); r.addWidget(w,1); return r
        def inp(ph, val=""):
            f=QLineEdit(val); f.setPlaceholderText(ph)
            f.setStyleSheet(
                f"QLineEdit{{background:{BG3};color:{WHITE};font-family:'{MONO}';"
                f"font-size:10px;border:1px solid {BORDER};padding:4px 8px;}}"
                f"QLineEdit:focus{{border:1px solid {CYAN};}}")
            p=f.palette(); p.setColor(p.ColorRole.Text,QColor(WHITE))
            p.setColor(p.ColorRole.Base,QColor(BG3)); f.setPalette(p); return f
        fv.addLayout(row("De :", QLabel(self.from_addr, styleSheet=S(DIM,10,ls=0))))
        self._to   = inp("titre.nom@site-xxxx.scipnet.scpf", to_addr)
        self._subj = inp("Objet du message", subject)
        fv.addLayout(row("À :", self._to)); fv.addLayout(row("Objet :", self._subj))
        v.addWidget(form)
        self._body = QTextEdit(); self._body.setPlaceholderText("Rédigez votre message…")
        self._body.setStyleSheet(
            f"QTextEdit{{background:{WIN_BG};color:{WHITE};font-family:'{MONO}';"
            f"font-size:11px;border:none;padding:16px;}}")
        self._body.setFont(F(11))
        bp=self._body.palette(); bp.setColor(bp.ColorRole.Text,QColor(WHITE))
        bp.setColor(bp.ColorRole.Base,QColor(WIN_BG)); self._body.setPalette(bp)
        v.addWidget(self._body, 1)
        foot = QWidget(); foot.setFixedHeight(48)
        foot.setStyleSheet(f"background:{BG2};border-top:1px solid {BORDER};")
        fh = QHBoxLayout(foot); fh.setContentsMargins(16,0,16,0); fh.setSpacing(10)
        self._err = QLabel(); self._err.setStyleSheet(S(RED,9,ls=0)); fh.addWidget(self._err,1)
        sb = QPushButton("  ✉  ENVOYER"); sb.setFixedHeight(32)
        sb.setStyleSheet(
            f"QPushButton{{background:{CYAN_D};color:{CYAN};font-family:'{MONO}';"
            f"font-size:10px;font-weight:600;letter-spacing:3px;padding:0 20px;"
            f"border:1px solid {CYAN};}}"
            f"QPushButton:hover{{background:{CYAN};color:{BG};}}")
        sb.clicked.connect(self._send); fh.addWidget(sb); v.addWidget(foot)

    def _send(self):
        to=self._to.text().strip(); subj=self._subj.text().strip() or "(sans objet)"
        body=self._body.toPlainText().strip()
        if not to: self._err.setText("Destinataire requis."); return
        if not body: self._err.setText("Message vide."); return
        if MessageStore.send(self.from_addr, to, subj, body):
            self.sent_sig.emit()
        else:
            self._err.setText("Erreur lors de l'envoi.")


class MessagerieWidget(QWidget):
    def __init__(self, login, niveau, nom_affiche, parent=None):
        super().__init__(parent)
        self.login=login; self.niveau=niveau; self.nom_affiche=nom_affiche
        session = DataStore.load("session.dat", {})
        self.address = make_address(session)
        self._compose_view = None
        self._build()
        QTimer(self, interval=15000, timeout=lambda: self._msg_list.refresh()).start()

    def _build(self):
        self.setStyleSheet(f"background:{WIN_BG};")
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        addr_bar = QWidget(); addr_bar.setFixedHeight(36)
        addr_bar.setStyleSheet(f"background:{BG3};border-bottom:1px solid {BORDER};")
        ah = QHBoxLayout(addr_bar); ah.setContentsMargins(16,0,16,0); ah.setSpacing(12)
        ah.addWidget(QLabel("✉", styleSheet=f"color:{CYAN};font-size:14px;background:transparent;"))
        ah.addWidget(QLabel(self.address, styleSheet=S(CYAN,10,ls=1)), 1)
        unread = MessageStore.count_unread(self.address)
        self._unread_lbl = QLabel(f"{unread} non lu{'s' if unread>1 else ''}" if unread else "")
        self._unread_lbl.setStyleSheet(S(YELLOW,9,ls=1))
        ah.addWidget(self._unread_lbl)
        root.addWidget(addr_bar)
        self._body_w = QWidget()
        bv = QVBoxLayout(self._body_w); bv.setContentsMargins(0,0,0,0); bv.setSpacing(0)
        sp = QSplitter(Qt.Orientation.Horizontal)
        sp.setStyleSheet(f"QSplitter::handle{{background:{BORDER};width:1px;}}")
        self._msg_list = MessageList(self.address)
        self._msg_list.message_selected.connect(self._show_msg)
        self._msg_list.compose_sig.connect(lambda: self._compose())
        sp.addWidget(self._msg_list)
        self._viewer = MessageViewer()
        self._viewer.reply_sig.connect(self._compose)
        self._viewer.delete_sig.connect(self._delete)
        sp.addWidget(self._viewer); sp.setSizes([320,680])
        bv.addWidget(sp, 1); root.addWidget(self._body_w, 1)

    def _show_msg(self, msg):
        self._viewer.show_message(msg)
        unread = MessageStore.count_unread(self.address)
        self._unread_lbl.setText(f"{unread} non lu{'s' if unread>1 else ''}" if unread else "")

    def _compose(self, to="", subj=""):
        if self._compose_view:
            self._compose_view.deleteLater()
        self._compose_view = ComposeWidget(self.address, to, subj, self._body_w)
        self._compose_view.sent_sig.connect(self._sent)
        self._compose_view.cancel_sig.connect(lambda: self._compose_view.hide())
        self._compose_view.resize(self._body_w.size()); self._compose_view.show()
        self._compose_view.raise_()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._compose_view and self._compose_view.isVisible():
            self._compose_view.resize(self._body_w.size())

    def _sent(self):
        if self._compose_view: self._compose_view.hide()
        self._msg_list.refresh()

    def _delete(self, msg_id):
        MessageStore.delete(self.address, msg_id)
        self._msg_list.refresh()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    load_barlow()
    login, niveau, nom_affiche = check_clearance("Terminal")
    win = ScipnetWindow("Messagerie", login, niveau, nom_affiche, width=1100, height=680)
    widget = MessagerieWidget(login, niveau, nom_affiche)
    win.set_content(widget)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
