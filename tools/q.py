#!/usr/bin/env python
"""Query helper for the BUHta payroll DB.
Usage:
  python q.py "SELECT TOP 10 * FROM ..."          -- run inline SQL
  python q.py -f path\to\query.sql                 -- run SQL from file
  python q.py --proc "<proc name>"                 -- print stored proc source
Options:
  --raw    print without column truncation
"""
import sys, os, io, pyodbc, textwrap
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dbconfig

# Always emit UTF-8 so Cyrillic survives the Windows console code page.
# Output goes next to the scripts (portable: no hardcoded drive/path).
OUT = open(dbconfig.out_path(), "w", encoding="utf-8")

# Connection comes from dbconfig (plugin userConfig / BUHTA_* env / db.local.json).
# Source of truth = etalon DB "Стандартная"; override the DB with env BUHTA_DB
# (e.g. set BUHTA_DB=<база_клиента> to inspect a client copy).
CONN = dbconfig.get_conn_str()

def get_sql():
    args = sys.argv[1:]
    if not args:
        print(__doc__); sys.exit(1)
    if args[0] == "--proc":
        name = args[1]
        return ("SELECT m.definition FROM sys.sql_modules m "
                "JOIN sys.objects o ON o.object_id=m.object_id "
                f"WHERE o.name = N'{name}'"), True
    if args[0] == "-f":
        with open(args[1], encoding="utf-8") as f:
            return f.read(), False
    return args[0], False

def main():
    sql, is_proc = get_sql()
    cn = pyodbc.connect(CONN, timeout=30)
    cur = cn.cursor()
    cur.execute(sql)
    if is_proc:
        row = cur.fetchone()
        OUT.write(row[0] if row else "<not found>")
        OUT.close()
        print("OK -> tools\\_out.txt")
        return
    while True:
        if cur.description:
            cols = [c[0] for c in cur.description]
            OUT.write("\t".join(cols) + "\n")
            OUT.write("\t".join("-"*len(c) for c in cols) + "\n")
            for r in cur.fetchall():
                OUT.write("\t".join("" if v is None else str(v) for v in r) + "\n")
        if not cur.nextset():
            break
    OUT.close()
    print("OK -> tools\\_out.txt")

if __name__ == "__main__":
    main()
