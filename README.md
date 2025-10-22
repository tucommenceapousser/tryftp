# tryftp
by trhacknon
just for perso use
---


## Usage:

```bash
python3 ftp_tester.py list.txt
```

Le fichier targets.txt doit contenir une entrée par ligne. Exemples de lignes acceptées :

```bash
    ftp.example.com:21:anonymous:gu**t
    192.168.1.10:21:admin:pas***3
    [2024-11-09 20:59:30] [SUCCESS] ftp.rdpublicidade.com.br:21:rdpublicidade:matsumoto@llan****hideto
    108.60.209.162:21:emenunew:Emenu***n123@@
```

Résultats écrits dans:
    success.txt  -> lignes réussies
    fail.txt     -> lignes échouées (raison incluse)
    results.log  -> log détaillé horodaté
"""
