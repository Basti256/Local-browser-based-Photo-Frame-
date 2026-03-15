"""
Cloudflare Tunnel Manager.

Startet cloudflared (bin/cloudflared.exe) und parst die öffentliche URL
aus der Ausgabe (trycloudflare.com). Wird bei network_mode="tunnel" verwendet.
"""
import subprocess
import threading
import re
import os


class TunnelManager:

    def __init__(self):

        self.process = None
        self.public_url = None
        self.running = False

    # ------------------------------------------------
    # Tunnel starten
    # ------------------------------------------------

    def start(self, port):

        if self.running:
            return

        url = f"http://localhost:{port}"

        self.process = subprocess.Popen(
            ["bin/cloudflared.exe", "tunnel", "--url", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        self.running = True

        thread = threading.Thread(target=self._read_output)
        thread.daemon = True
        thread.start()

    # ------------------------------------------------
    # Tunnel Output lesen
    # ------------------------------------------------

    def _read_output(self):

        for line in self.process.stdout:

            print("[Tunnel]", line.strip())

            if "trycloudflare.com" in line:

                # Nur die saubere Basis-URL extrahieren (ohne dest=, Pfade, etc.)
                match = re.search(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com", line)
                if match:
                    self.public_url = match.group(0)
                    print("Tunnel URL erkannt:", self.public_url)

    # ------------------------------------------------
    # Tunnel stoppen
    # ------------------------------------------------

    def stop(self):
        """Beendet den cloudflared-Prozess."""

        if self.process:

            try:
                self.process.terminate()
            except:
                pass

        self.running = False
        self.public_url = None

    # ------------------------------------------------
    # Status
    # ------------------------------------------------

    def status(self):
        """Liefert {"running": bool, "url": str oder None}."""

        url = self.public_url
        # Bereinige URL falls sie Pfade/Präfixe enthält
        if url:
            match = re.search(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com", url)
            if match:
                url = match.group(0)

        return {
            "running": self.running,
            "url": url
        }


tunnel_manager = TunnelManager()