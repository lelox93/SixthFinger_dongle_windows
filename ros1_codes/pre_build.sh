#!/bin/bash

# Definizione delle sequenze di escape ANSI per colori e stili
bold=$(tput bold)
orange=$(tput setaf 3)
red=$(tput setaf 1)
green=$(tput setaf 2)  # colore verde per i messaggi di successo
reset=$(tput sgr0)

# Funzione per creare la regola udev
create_udev_rule() {
    local UDEV_RULE_FILE="/etc/udev/rules.d/99-ttyusb.rules"

    if [ -f "$UDEV_RULE_FILE" ]; then
        echo "${orange}${bold}Il file di regole udev $UDEV_RULE_FILE esiste già. Non è necessario creare una nuova regola.${reset}"
    else
        echo "Creazione della regola udev per i dispositivi TTY..."
        sudo bash -c "echo 'SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"303a\", ATTRS{idProduct}==\"1001\", MODE=\"0666\"' > $UDEV_RULE_FILE"
        reload_udev_rules
        echo "${green}${bold}Regola udev creata con successo per i dispositivi TTY.${reset}"
    fi
}

# Funzione per ricaricare le regole udev
reload_udev_rules() {
    echo "Ricaricamento delle regole udev..."
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    echo "${green}${bold}Regole udev ricaricate con successo.${reset}"
}

# Funzione per controllare e installare libudev se necessario
install_libudev() {
    if ldconfig -p | grep -q libudev; then
        echo "${orange}${bold}libudev è già installata.${reset}"
    else
        echo "libudev non è installata. Provo a installarla..."

        if command -v apt-get >/dev/null 2>&1; then
            sudo apt-get update
            sudo apt-get install -y libudev-dev
        elif command -v yum >/dev/null 2>&1; then
            sudo yum install -y systemd-devel
        elif command -v pacman >/dev/null 2>&1; then
            sudo pacman -Sy --noconfirm systemd
        else
            echo "${red}${bold}Non è stato trovato un gestore di pacchetti compatibile. Per favore, installa libudev manualmente.${reset}"
            exit 1
        fi

        if ldconfig -p | grep -q libudev; then
            echo "${orange}${bold}libudev è stata installata con successo.${reset}"
        else
            echo "${red}${bold}Errore durante l'installazione di libudev.${reset}"
            exit 1
        fi
    fi
}

# Funzione principale
main() {
    create_udev_rule
    install_libudev
    echo "Operazioni completate."
}

# Eseguire la funzione principale
main
