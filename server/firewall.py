"""Firewall: Windows netsh, andere Systeme ohne Änderung."""
import platform
import subprocess

RULE_NAME = "LocalPhotoFrame"


def open_firewall_port(port: int) -> None:
    if platform.system() != "Windows":
        print("[Firewall] Übersprungen (kein Windows). Port:", port)
        return
    try:
        subprocess.run(
            [
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name={RULE_NAME}_{port}",
                "dir=in", "action=allow", "protocol=TCP",
                f"localport={port}",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"[Firewall] Port {port} geöffnet")
    except Exception as e:
        print("[Firewall] Fehler beim Öffnen:", e)


def close_firewall_port(port: int) -> None:
    if platform.system() != "Windows":
        return
    try:
        subprocess.run(
            [
                "netsh", "advfirewall", "firewall", "delete", "rule",
                f"name={RULE_NAME}_{port}",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"[Firewall] Port {port} geschlossen")
    except Exception as e:
        print("[Firewall] Fehler beim Schließen:", e)
