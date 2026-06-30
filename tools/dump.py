#!/usr/bin/env python
"""Dump stored-proc / function sources to individual UTF-8 files.
Usage: python dump.py "Proc Name 1" "Proc Name 2" ...
Writes each to tools\procs\<sanitized>.sql
"""
import sys, os, re, pyodbc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dbconfig
# Connection from dbconfig (plugin userConfig / BUHTA_* env / db.local.json).
CONN = dbconfig.get_conn_str()
OUTDIR = dbconfig.procs_dir()
cn = pyodbc.connect(CONN, timeout=30); cur = cn.cursor()
for name in sys.argv[1:]:
    cur.execute("SELECT m.definition FROM sys.sql_modules m "
                "JOIN sys.objects o ON o.object_id=m.object_id WHERE o.name=?", name)
    row = cur.fetchone()
    safe = re.sub(r'[\\/:*?"<>|]', '_', name)
    path = os.path.join(OUTDIR, safe + ".sql")
    with open(path, "w", encoding="utf-8") as f:
        f.write(row[0] if row else "<NOT FOUND: %s>" % name)
    print(("OK " if row else "MISS ") + path)
