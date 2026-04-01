#!/usr/bin/env python3
"""
SCiPNET — Session Autostart
S'exécute au démarrage de la session KDE.
Lit le compte Linux connecté, vérifie dans users.dat,
et sauvegarde la session pour les apps standalone.

Si le compte Linux n'existe pas dans users.dat,
crée automatiquement un compte N1 avec le mot de passe
égal au login (changeable ensuite dans Paramètres).
"""
import sys, os, json, getpass
from pathlib import Path

sys.path.insert(0, "/opt/scipnet")

try:
    from cryptography.fernet import Fernet
    HAS_FERNET = True
except ImportError:
    HAS_FERNET = False

# ── DataStore minimal (sans Qt) ───────────────────────────────────────────────
class _Store:
    _DIR  = Path.home() / ".scipnet"
    _KEY  = None

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

    @classmethod
    def check_mdp(cls, mdp: str, stored: str) -> bool:
        import hashlib
        if len(stored) == 64:
            return hashlib.sha256(mdp.encode("utf-8")).hexdigest() == stored
        return mdp == stored

# ── Comptes par défaut ────────────────────────────────────────────────────────
DEFAULT_USERS = {
    "agent13"   : {"mdp": _Store.hash_mdp("keter"),      "niveau": 1},
    "dr.rights" : {"mdp": _Store.hash_mdp("euclide"),    "niveau": 2},
    "dr.bright" : {"mdp": _Store.hash_mdp("everything"), "niveau": 3},
    "admin"     : {"mdp": _Store.hash_mdp("O5-CONSEIL"), "niveau": 5},
}

NIVEAU_LABELS = {
    1: "MINIMAL", 2: "RESTREINT", 3: "CONFIDENTIEL",
    4: "SECRET",  5: "TOP SECRET",
}

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # Récupérer le compte Linux connecté
    linux_user = getpass.getuser().lower()

    # Charger les utilisateurs SCiPNET
    users = _Store.load("users.dat", None)
    if users is None:
        _Store.save("users.dat", DEFAULT_USERS)
        users = DEFAULT_USERS

    # Chercher le compte Linux dans users.dat
    if linux_user in users:
        niveau = users[linux_user].get("niveau", 1)
        login  = linux_user
    else:
        # Compte Linux non trouvé → créer automatiquement N1
        # avec mdp = login (l'utilisateur peut le changer dans Paramètres)
        users[linux_user] = {
            "mdp"   : _Store.hash_mdp(linux_user),
            "niveau": 1,
        }
        _Store.save("users.dat", users)
        niveau = 1
        login  = linux_user

    # Sauvegarder la session
    _Store.save("session.dat", {
        "login" : login,
        "niveau": niveau,
    })

    # Log pour debug
    log_path = _Store.dir() / "autostart.log"
    log_path.write_text(
        f"SCiPNET Autostart\n"
        f"Compte Linux : {linux_user}\n"
        f"Login SCiPNET : {login}\n"
        f"Niveau : {niveau} — {NIVEAU_LABELS.get(niveau,'?')}\n",
        encoding="utf-8"
    )

if __name__ == "__main__":
    main()
