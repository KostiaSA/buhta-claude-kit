#!/usr/bin/env python
"""Execute a .sql file against the BUHta DB (for ALTER/CREATE PROCEDURE, etc.).
Splits on lines containing only GO. Runs in autocommit.
Usage:  python exec_sql.py path\to\script.sql
        python exec_sql.py --check path\to\script.sql   (parse only, do NOT run)
SAFETY: this is a CLIENT DB COPY. A backup exists, but review the script first.
"""
import sys, os, re, pyodbc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dbconfig
# Connection from dbconfig (plugin userConfig / BUHTA_* env / db.local.json).
CONN = dbconfig.get_conn_str()

def main():
    args = sys.argv[1:]
    check = False
    if args and args[0] == "--check":
        check = True; args = args[1:]
    if not args:
        print(__doc__); sys.exit(1)
    with open(args[0], encoding="utf-8-sig") as f:
        sql = f.read()
    # split on standalone GO
    batches = [b for b in re.split(r'(?im)^[ \t]*GO[ \t]*;?[ \t]*$', sql) if b.strip()]
    print(f"{len(batches)} batch(es) parsed.")
    if check:
        print("--check: not executing.")
        return
    cn = pyodbc.connect(CONN, timeout=60, autocommit=True)
    cur = cn.cursor()
    for i, b in enumerate(batches, 1):
        cur.execute(b)
        print(f"batch {i}: OK")
    print("DONE.")

if __name__ == "__main__":
    main()
