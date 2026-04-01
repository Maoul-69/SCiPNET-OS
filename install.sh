#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
#  SCiPNET OS — Script d'installation automatique
#  SCP Foundation Roleplay Operating System
#  Licence : Creative Commons Universal (CC0 1.0)
# ═══════════════════════════════════════════════════════════════════════════════

set -e
RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'

log()  { echo -e "${CYAN}[SCiPNET]${NC} $1"; }
ok()   { echo -e "${GREEN}[  OK  ]${NC} $1"; }
warn() { echo -e "${YELLOW}[ WARN ]${NC} $1"; }
err()  { echo -e "${RED}[ERROR ]${NC} $1"; exit 1; }

echo ""
echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       SCiPNET OS — Installation       ║${NC}"
echo -e "${CYAN}║    SCP Foundation Roleplay System      ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
echo ""

# ── Vérifications ─────────────────────────────────────────────────────────────
[ "$EUID" -ne 0 ] && err "Lance ce script avec sudo : sudo bash install.sh"
command -v python3 &>/dev/null || err "Python3 requis. Installe-le avec : sudo apt install python3"

log "Vérification des dépendances système..."
apt-get update -qq
apt-get install -y -qq \
    python3 python3-pyqt6 python3-cryptography python3-pip \
    python3-pyqt6.qtwebengine \
    fonts-liberation imagemagick icoutils \
    xorg openbox unclutter plymouth plymouth-themes \
    curl wget 2>/dev/null || warn "Certains paquets optionnels non disponibles"
ok "Dépendances installées"

# ── Dossier d'installation ────────────────────────────────────────────────────
INSTALL_DIR="/opt/scipnet"
log "Création du dossier d'installation : $INSTALL_DIR"
mkdir -p "$INSTALL_DIR/apps"
chmod 755 "$INSTALL_DIR"

# ── Copie des fichiers ────────────────────────────────────────────────────────
log "Copie des fichiers SCiPNET..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Fichier commun (requis par toutes les apps)
cp "$SCRIPT_DIR/scipnet_common.py" "$INSTALL_DIR/"

# Apps utilisateur (pas admin, pas serveur, pas Principal.py)
APPS=(
    "scipnet-terminal.py"
    "scipnet-fichiers.py"
    "scipnet-base-scp.py"
    "scipnet-personnel.py"
    "scipnet-chiffrement.py"
    "scipnet-site-map.py"
    "scipnet-messagerie.py"
    "scipnet-armement.py"
    "scipnet-parametres.py"
)
for app in "${APPS[@]}"; do
    if [ -f "$SCRIPT_DIR/apps/$app" ]; then
        cp "$SCRIPT_DIR/apps/$app" "$INSTALL_DIR/apps/"
        chmod +x "$INSTALL_DIR/apps/$app"
        ok "Installé : $app"
    else
        warn "Non trouvé : $app (ignoré)"
    fi
done

# Setup wizard et autostart
for f in "scipnet-setup.py" "scipnet-autostart.py"; do
    if [ -f "$SCRIPT_DIR/$f" ]; then
        cp "$SCRIPT_DIR/$f" "$INSTALL_DIR/"
        chmod +x "$INSTALL_DIR/$f"
    fi
done

# Logo / icône
if [ -f "$SCRIPT_DIR/scp-logo.png" ]; then
    cp "$SCRIPT_DIR/scp-logo.png" "$INSTALL_DIR/"
    ok "Logo SCP copié"
elif [ -f "$SCRIPT_DIR/icons8-scp-foundation-32.ico" ]; then
    icotool -x "$SCRIPT_DIR/icons8-scp-foundation-32.ico" \
        -o "$INSTALL_DIR/" 2>/dev/null || true
    if ls "$INSTALL_DIR/"*.png 1>/dev/null 2>&1; then
        mv "$INSTALL_DIR/"*.png "$INSTALL_DIR/scp-logo.png"
        convert -resize 1920x1080 xc:black "$INSTALL_DIR/scp-logo.png" \
            -gravity center -composite "$INSTALL_DIR/wallpaper.png" 2>/dev/null || \
            cp "$INSTALL_DIR/scp-logo.png" "$INSTALL_DIR/wallpaper.png"
        ok "Logo SCP converti"
    fi
fi

chown -R root:root "$INSTALL_DIR"
chmod -R 755 "$INSTALL_DIR"

# ── Utilisateur Linux scipnet ─────────────────────────────────────────────────
echo ""
log "Configuration de l'utilisateur Linux 'scipnet'..."
if ! id "scipnet" &>/dev/null; then
    useradd -m -s /bin/bash -G video,audio,input scipnet
    echo "scipnet:scipnet" | chpasswd
    ok "Utilisateur 'scipnet' créé (mdp Linux : scipnet)"
else
    ok "Utilisateur 'scipnet' déjà existant"
fi

# ── Autostart KDE ────────────────────────────────────────────────────────────
log "Configuration de l'autostart KDE..."
mkdir -p /home/scipnet/.config/autostart
cat > /home/scipnet/.config/autostart/scipnet-setup.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=SCiPNET Setup
Exec=python3 /opt/scipnet/scipnet-setup.py
Hidden=false
X-KDE-autostart-enabled=true
EOF
chown -R scipnet:scipnet /home/scipnet/.config/
ok "Autostart configuré"

# ── Fichiers .desktop pour le bureau ─────────────────────────────────────────
log "Création des raccourcis bureau..."
mkdir -p /home/scipnet/Desktop

declare -A APP_NAMES=(
    ["terminal"]="Terminal SCiPNET"
    ["fichiers"]="Fichiers"
    ["base-scp"]="Base de Données SCP"
    ["personnel"]="Personnel"
    ["chiffrement"]="Chiffrement"
    ["site-map"]="Site Map"
    ["messagerie"]="Messagerie"
    ["armement"]="Armement"
    ["parametres"]="Paramètres"
)
declare -A APP_COMMENTS=(
    ["terminal"]="Terminal de commande SCiPNET"
    ["fichiers"]="Explorateur de fichiers RP"
    ["base-scp"]="Base de données SCP Foundation"
    ["personnel"]="Gestion du personnel du site"
    ["chiffrement"]="Chiffrement de fichiers"
    ["site-map"]="Carte interactive du site"
    ["messagerie"]="Messagerie interne SCiPNET"
    ["armement"]="Système d'armement stratégique"
    ["parametres"]="Paramètres du compte"
)

for key in "${!APP_NAMES[@]}"; do
    cat > "/home/scipnet/Desktop/scipnet-${key}.desktop" << EOF
[Desktop Entry]
Type=Application
Name=${APP_NAMES[$key]}
Comment=${APP_COMMENTS[$key]}
Exec=python3 /opt/scipnet/apps/scipnet-${key}.py
Icon=/opt/scipnet/scp-logo.png
Terminal=false
Categories=SCiPNET;
EOF
    chmod +x "/home/scipnet/Desktop/scipnet-${key}.desktop"
done

chown -R scipnet:scipnet /home/scipnet/Desktop/
ok "Raccourcis bureau créés"

# ── Plymouth theme ────────────────────────────────────────────────────────────
log "Installation du thème Plymouth..."
mkdir -p /usr/share/plymouth/themes/scipnet
cat > /usr/share/plymouth/themes/scipnet/scipnet.script << 'PLYM'
Window.SetBackgroundTopColor(0.03,0.03,0.03);
Window.SetBackgroundBottomColor(0.0,0.0,0.0);
logo = Image("scipnet-logo.png");
if (logo) {
    s = Sprite(logo);
    s.SetX(Window.GetWidth()/2 - logo.GetWidth()/2);
    s.SetY(Window.GetHeight()/2 - logo.GetHeight()/2 - 60);
}
t = Image.Text("S C i P N E T", 0.0, 0.83, 1.0, 1);
ts = Sprite(t);
ts.SetX(Window.GetWidth()/2 - t.GetWidth()/2);
ts.SetY(Window.GetHeight()/2 + 60);
s2 = Image.Text("Secure. Contain. Protect.", 0.4, 0.4, 0.4, 1);
ss2 = Sprite(s2);
ss2.SetX(Window.GetWidth()/2 - s2.GetWidth()/2);
ss2.SetY(Window.GetHeight()/2 + 90);
msg_sprite = Sprite();
msg_sprite.SetPosition(Window.GetWidth()/2 - 200, Window.GetHeight()-60, 0);
fun message_callback(text) {
    m = Image.Text(text, 0.0, 0.83, 1.0, 1);
    msg_sprite.SetImage(m);
    msg_sprite.SetX(Window.GetWidth()/2 - m.GetWidth()/2);
}
Plymouth.SetMessageFunction(message_callback);
PLYM

cat > /usr/share/plymouth/themes/scipnet/scipnet.plymouth << 'PLYM'
[Plymouth Theme]
Name=SCiPNET
Description=SCP Foundation SCiPNET OS
ModuleName=script
[script]
ImageDir=/usr/share/plymouth/themes/scipnet
ScriptFile=/usr/share/plymouth/themes/scipnet/scipnet.script
PLYM

if [ -f "$INSTALL_DIR/scp-logo.png" ]; then
    cp "$INSTALL_DIR/scp-logo.png" /usr/share/plymouth/themes/scipnet/scipnet-logo.png
fi

update-alternatives --install /usr/share/plymouth/themes/default.plymouth \
    default.plymouth /usr/share/plymouth/themes/scipnet/scipnet.plymouth 100 2>/dev/null || true
update-alternatives --set default.plymouth \
    /usr/share/plymouth/themes/scipnet/scipnet.plymouth 2>/dev/null || true
update-initramfs -u 2>/dev/null || warn "update-initramfs ignoré"
ok "Thème Plymouth installé"

# ── GRUB silencieux ───────────────────────────────────────────────────────────
log "Configuration GRUB..."
if [ -f /etc/default/grub ]; then
    sed -i 's/GRUB_TIMEOUT=.*/GRUB_TIMEOUT=0/' /etc/default/grub
    grep -q "GRUB_TIMEOUT_STYLE" /etc/default/grub || \
        echo 'GRUB_TIMEOUT_STYLE=hidden' >> /etc/default/grub
    sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT=.*/GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"/' /etc/default/grub
    update-grub 2>/dev/null || true
    ok "GRUB configuré"
fi

# ── Résumé ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}    SCiPNET OS installé avec succès !${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${WHITE}Apps installées :${NC} /opt/scipnet/apps/"
echo -e "  ${WHITE}Compte Linux    :${NC} scipnet / scipnet"
echo -e "  ${WHITE}Compte SCiPNET  :${NC} admin / [votre mot de passe]"
echo ""
echo -e "  ${YELLOW}Au premier démarrage de la session 'scipnet',${NC}"
echo -e "  ${YELLOW}un wizard de configuration SCiPNET s'ouvrira.${NC}"
echo ""
echo -e "  ${CYAN}Pour la messagerie, lancez le serveur sur UN seul PC :${NC}"
echo -e "  python3 /opt/scipnet/scipnet-serveur-msg.py"
echo ""
