# SCiPNET OS
**SCP Foundation Roleplay Operating System**

> ⚠️ **AVERTISSEMENT — USAGE ROLEPLAY UNIQUEMENT**
> Ce projet est un **système fictif à but ludique** inspiré de l'univers SCP Foundation.
> - La **messagerie** n'est pas un système de communication sécurisé — ne l'utilisez pas pour des échanges sensibles ou personnels.
> - Le **chiffrement** est fourni à titre illustratif — ne l'utilisez pas pour protéger de vrais documents confidentiels.
> - L'**ISO** n'est pas un OS professionnel ou sécurisé — ne l'utilisez pas comme système principal.
> - L'**app d'armement** est 100% fictive — elle ne contrôle rien de réel.

---

## Présentation

SCiPNET OS est un faux système d'exploitation inspiré de la [SCP Foundation](https://scp-wiki.net), conçu pour le jeu de rôle. Il tourne sur Linux (Kubuntu/Ubuntu) et propose une interface sombre style terminal avec plusieurs applications intégrées.

## Applications incluses

| App | Niveau requis | Description |
|-----|--------------|-------------|
| Terminal | N1 | Terminal CLI avec commandes SCP |
| Fichiers | N1 | Explorateur de fichiers RP + lecteur |
| Paramètres | N1 | Configuration du compte |
| Personnel | N2 | Gestion des départements du site |
| Chiffrement | N2 | Chiffrement de fichiers (Fernet) |
| Base SCP | N3 | Base de données SCP via API |
| Site Map | N3 | Carte interactive du site |
| Messagerie | N1 | Messagerie interne (réseau local) |
| Armement | N4/N5 | Système fictif de frappe stratégique |

## Installation

```bash
git clone https://github.com/[votre-compte]/scipnet-os.git
cd scipnet-os
sudo bash install.sh
```

Le script installe automatiquement :
- Les dépendances Python (PyQt6, cryptography...)
- Les apps dans `/opt/scipnet/`
- L'utilisateur Linux `scipnet`
- Le thème Plymouth de démarrage
- Les raccourcis bureau KDE

## Premier démarrage

1. Connectez-vous avec le compte Linux **scipnet** (mot de passe : `scipnet`)
2. Un wizard de configuration SCiPNET s'ouvre — remplissez vos informations (nom, titre, niveau, site)
3. Le bureau KDE se lance avec les apps SCiPNET

## Niveaux de clairance

| Niveau | Nom | Accès |
|--------|-----|-------|
| N1 | MINIMAL | Terminal, Fichiers, Messagerie |
| N2 | RESTREINT | + Personnel, Chiffrement |
| N3 | CONFIDENTIEL | + Base SCP, Site Map |
| N4 | SECRET | + Armement (site uniquement) |
| N5 | TOP SECRET | Accès complet |

## Structure du dépôt

```
scipnet-os/
├── install.sh              # Script d'installation
├── README.md               # Ce fichier
├── LICENSE                 # Creative Commons Universal (CC0 1.0)
├── scipnet_common.py       # Bibliothèque commune
├── scipnet-setup.py        # Wizard de première configuration
├── scipnet-autostart.py    # Autostart de session
├── scipnet-serveur-msg.py  # Serveur de messagerie
├── scp-logo.png            
└── apps/
    ├── scipnet-terminal.py
    ├── scipnet-fichiers.py
    ├── scipnet-base-scp.py
    ├── scipnet-personnel.py
    ├── scipnet-chiffrement.py
    ├── scipnet-site-map.py
    ├── scipnet-messagerie.py
    ├── scipnet-armement.py
    └── scipnet-parametres.py
```

## Dépendances

- Python 3.10+
- PyQt6
- python3-pyqt6.qtwebengine (pour l'app Armement)
- cryptography
- Kubuntu / Ubuntu 24.04 LTS recommandé

## Licence

**Creative Commons Universal (CC0 1.0 Public Domain Dedication)**

Ce projet est dédié au domaine public. Vous pouvez copier, modifier, distribuer et utiliser ce travail, même à des fins commerciales, sans demander permission.

Les données SCP utilisées proviennent de [scp-data.tedivm.com](https://scp-data.tedivm.com) sous licence CC BY-SA 3.0.

---

*"Secure. Contain. Protect."*
