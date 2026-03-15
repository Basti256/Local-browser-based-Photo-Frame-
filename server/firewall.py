import subprocess


RULE_NAME = "WeddingPhotoWall"


def open_firewall_port(port):

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