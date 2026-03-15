"""
Windows-Firewall: Port automatisch öffnen/schließen.

Verwendet netsh advfirewall. Nur unter Windows relevant.
Bei network/public wird der Server-Port beim Start geöffnet und beim Shutdown geschlossen.
"""
import subprocess

RULE_NAME = "LocalPhotoFrame"


def open_firewall_port(port):
    """Fügt eine eingehende Firewall-Regel für den angegebenen TCP-Port hinzu."""

    try:

        subprocess.run([
            "netsh",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            f"name={RULE_NAME}_{port}",
            "dir=in",
            "action=allow",
            "protocol=TCP",
            f"localport={port}"
        ], check=True)

        print(f"[Firewall] Port {port} geöffnet")

    except Exception as e:

        print("[Firewall] Fehler beim Öffnen:", e)



def close_firewall_port(port):
    """Entfernt die Firewall-Regel für den angegebenen Port."""

    try:

        subprocess.run([
            "netsh",
            "advfirewall",
            "firewall",
            "delete",
            "rule",
            f"name={RULE_NAME}_{port}"
        ], check=True)

        print(f"[Firewall] Port {port} geschlossen")

    except Exception as e:

        print("[Firewall] Fehler beim Schließen:", e)