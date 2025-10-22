#!/usr/bin/env python3

import sys
import ftplib
import socket
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# Configuration
TIMEOUT = 8            # secondes pour socket/connexion
WORKERS = 30           # nombre de threads concurrents
SUCCESS_FILE = "success.txt"
FAIL_FILE = "fail.txt"
LOG_FILE = "results.log"

def now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def extract_ftp_entry(line: str):
    """
    Tente d'extraire (host, port, user, password) depuis la ligne.
    Stratégie:
      - Nettoie la ligne (strip)
      - Recherche un split depuis la droite pour obtenir 4 champs via rsplit(':', 3)
      - Retourne None si extraction impossible
    """
    s = line.strip()
    if not s:
        return None

    # Supprimer les préfixes comme "[timestamp] [SUCCESS]" s'il y en a
    # Si la ligne contient ']' on prend la partie après le dernier ']' (souvent utile pour logs)
    if ']' in s:
        candidate = s.split(']')[-1].strip()
        if candidate:
            s = candidate

    # Certaines lignes peuvent contenir 'ftp://' ou autres ; enlever protocole si présent
    if s.lower().startswith("ftp://"):
        s = s[6:]

    # On cherche un pattern host:port:user:password
    parts = s.rsplit(':', 3)
    if len(parts) != 4:
        # impossible d'extraire
        return None

    host, port_str, user, password = parts
    host = host.strip()
    port_str = port_str.strip()
    user = user.strip()
    password = password.strip()

    # validation basique
    try:
        port = int(port_str)
    except Exception:
        return None

    if not host or not user:
        return None

    return host, port, user, password

def test_ftp_connect(entry_line: str):
    """
    Teste la connexion FTP pour une ligne brute d'entrée.
    Retourne un tuple (ok: bool, message: str, normalized_line: str)
    """
    parsed = extract_ftp_entry(entry_line)
    if not parsed:
        return False, "parse_error", entry_line.strip()

    host, port, user, password = parsed
    normalized = f"{host}:{port}:{user}:{password}"

    try:
        ftp = ftplib.FTP()
        ftp.connect(host, port, timeout=TIMEOUT)
        # Some servers require passive mode toggle; we leave default (passive True).
        ftp.login(user, password)
        # Optionnel : lister la racine pour valider (non obligatoire)
        try:
            ftp.nlst()  # simple commande pour confirmer permissions
        except Exception:
            # nlst peut échouer pour permissions, mais login peut être quand même OK.
            pass
        ftp.quit()
        return True, "connected", normalized

    except ftplib.error_perm as e:
        return False, f"perm_error: {e}", normalized
    except ftplib.error_temp as e:
        return False, f"temp_error: {e}", normalized
    except ftplib.error_proto as e:
        return False, f"proto_error: {e}", normalized
    except (socket.timeout, TimeoutError) as e:
        return False, "timeout", normalized
    except (ConnectionRefusedError, ConnectionResetError, OSError) as e:
        return False, f"network_error: {e}", normalized
    except Exception as e:
        return False, f"other_error: {repr(e)}", normalized

def write_line(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")

def main(input_file: str):
    p = Path(input_file)
    if not p.exists():
        print(f"Fichier introuvable: {input_file}")
        return 1

    lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    total = len(lines)
    print(f"[{now()}] Test de {total} lignes depuis {input_file} avec {WORKERS} threads...")

    # Clear output files
    Path(SUCCESS_FILE).write_text("", encoding="utf-8")
    Path(FAIL_FILE).write_text("", encoding="utf-8")
    Path(LOG_FILE).write_text("", encoding="utf-8")

    futures = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for i, line in enumerate(lines, 1):
            # soumet la tâche
            futures.append(ex.submit(test_ftp_connect, line))

        completed = 0
        for fut in as_completed(futures):
            completed += 1
            try:
                ok, msg, normalized = fut.result()
            except Exception as e:
                ok = False
                msg = f"internal_exception: {e}"
                normalized = "<unknown>"
            timestamp = now()
            log_line = f"[{timestamp}] [{'OK' if ok else 'FAIL'}] {normalized} => {msg}"
            print(f"[{completed}/{total}] {log_line}")
            write_line(Path(LOG_FILE), log_line)
            if ok:
                write_line(Path(SUCCESS_FILE), normalized)
            else:
                write_line(Path(FAIL_FILE), f"{normalized}  # {msg}")

    print(f"[{now()}] Terminé. Succès enregistrés dans {SUCCESS_FILE}, échecs dans {FAIL_FILE}, log dans {LOG_FILE}")
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 ftp_tester.py targets.txt")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
