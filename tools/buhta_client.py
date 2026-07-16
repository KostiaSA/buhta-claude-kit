#!/usr/bin/env python
"""Client for the BUHta .exe local automation server (bmAutomationServer).

The server listens ONLY on 127.0.0.1:8765 and must be started by launching the
.exe and logging in. Wire encoding is cp1251 both ways (matches the Delphi side).

Usage:
  python buhta_client.py --ping
  python buhta_client.py --query-list [--filter Подр] [--root Сотрудник]  -- find named queries (SchemaView)
  python buhta_client.py "Подразделение"                 -- run a named query
  python buhta_client.py "Подразделение" --top 50
  python buhta_client.py "Подразделение" --sql            -- print generated SQL (no exec)
  python buhta_client.py "<view>" -p "дата начала=2025-01-01" -p "ключ=10"
  python buhta_client.py --add "Подразделение" "Начальник подразделения.Фамилия" --color green --caption "Фамилия начальника"
  python buhta_client.py --style "Подразделение" "Название" --color red --width 200
  python buhta_client.py --remove "Подразделение" "Фамилия начальника"

  python buhta_client.py --form-list [--filter НДФЛ] [--class Form]  -- list dream forms
  python buhta_client.py --form-get "<имя формы>"        -- read form; saves dfm/script to files
  python buhta_client.py --form-check "<имя формы>"      -- syntax-check stored script
  python buhta_client.py --form-check "<имя>" --script file.pas      -- check a candidate script
  python buhta_client.py --form-set-script "<имя>" file.pas          -- write [Скрипт] (auto-backup)
  python buhta_client.py --form-set-dfm "<имя>" file.dfm             -- write [ДФМ]    (auto-backup)

  python buhta_client.py --report-list [--filter X] [--type 0] [--group G]  -- list templates
  python buhta_client.py --report-get "<ключ>"          -- read; body/data -> tools\\_report_*
  python buhta_client.py --report-set-template "<ключ>" file [--kind text|blob]  -- write body (auto-backup)
  python buhta_client.py --report-set-data "<ключ>" file.data        -- write [Данные] (auto-backup)
  python buhta_client.py --report-show "<ключ>" [-p "имя=значение"]   -- preview by name
  python buhta_client.py --report-print "<ключ>" [-p "имя=значение"]  -- print by name
  python buhta_client.py --report-print-doc "<таблица>" --ids "1,2,3" [--vid V]  -- doc-linked print

  python buhta_client.py --gen-doc-vids                  -- document kinds that have generation settings
  python buhta_client.py --gen-rules 1                   -- generation rules for a document kind
  python buhta_client.py --gen-rule-get 218              -- one rule, all columns -> tools\\_out.txt
  python buhta_client.py --gen-rule-set 218 -f "Сумма=Докспец.Сумма" -f "Приоритет=5"  -- edit fields (+auto refresh proc)
  python buhta_client.py --gen-proc-sql 1                -- generated CREATE PROCEDURE text -> tools\\_gen_proc_1.sql
  python buhta_client.py --gen-proc-db 1                 -- current proc text from DB -> tools\\_gen_proc_1_db.sql
  python buhta_client.py --gen-proc-refresh 1            -- (re)create the generation stored procedure (ALTER/CREATE)
  python buhta_client.py --gen-proc-recreate 1           -- DROP+CREATE the generation stored procedure (clean)
  python buhta_client.py --gen-run 12345                 -- run generation for one document by key
  python buhta_client.py --gen-provodki 12345            -- postings produced for a document

Full JSON result is written (pretty, UTF-8) to tools\\_out.txt; a short summary
is printed. Importable: run_query(name, params=None, top=None) -> dict, ping().
"""
import sys, os, json, re, base64, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dbconfig

HOST = os.environ.get("BUHTA_HOST", "127.0.0.1")
PORT = int(os.environ.get("BUHTA_PORT", "8765"))
BASE = f"http://{HOST}:{PORT}"
# Output goes next to the scripts (portable: no hardcoded drive/path).
OUT = dbconfig.out_path()


def _post(path, payload, timeout=120):
    body = json.dumps(payload, ensure_ascii=False).encode("cp1251")
    req = urllib.request.Request(
        BASE + path, data=body, method="POST",
        headers={"Content-Type": "application/json; charset=windows-1251"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        raw = e.read()  # server still returns a JSON error body
    return json.loads(raw.decode("cp1251"))


def _get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=30) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        raw = e.read()
    return json.loads(raw.decode("cp1251"))


def ping():
    """Return the server /ping info (db, kontora, user)."""
    return _get("/ping")


def _payload(name, params, top):
    p = {"name": name}
    if params:
        p["params"] = params
    if top:
        p["top"] = int(top)
    return p


def run_query(name, params=None, top=None):
    """Run a named SchemaView query, return the parsed JSON result dict."""
    return _post("/query", _payload(name, params, top))


def run_query_sql(name, params=None, top=None):
    """Return the SQL generated for a named query WITHOUT executing it."""
    return _post("/query/sql", _payload(name, params, top))


def query_list(filter=None, root=None, top=200):
    """Find named queries (SchemaView) by ViewName/RootTable substring.

    Reads schema metadata straight from the DB (like q.py) — no running .exe
    needed, since SchemaView is distributed from the etalon and is the same
    across copies. Returns {"ok":True,"count":N,"views":[{name,root,oborot}]}.
    """
    import pyodbc  # lazy: HTTP-only commands must not require pyodbc/ODBC
    where, vals = [], []
    if filter:
        where.append("ViewName LIKE ?"); vals.append("%" + filter + "%")
    if root:
        where.append("RootTable LIKE ?"); vals.append("%" + root + "%")
    sql = ("SELECT TOP (%d) ViewName, RootTable, Oborot FROM SchemaView"
           % int(top))
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY ViewName"
    try:
        cn = pyodbc.connect(dbconfig.get_conn_str())
        rows = cn.cursor().execute(sql, *vals).fetchall()
        cn.close()
    except Exception as e:  # noqa: BLE001 — surface as a JSON error like the server
        return {"ok": False, "error": str(e)}
    views = [{"name": r[0], "root": r[1], "oborot": bool(r[2])} for r in rows]
    return {"ok": True, "count": len(views), "views": views}


def add_field(view, path, color=None, width=None, caption=None):
    """Add a field (dot-path, e.g. 'Начальник подразделения.Фамилия') to a view."""
    body = {"view": view, "path": path}
    if color is not None:
        body["color"] = color
    if width is not None:
        body["width"] = int(width)
    if caption:
        body["caption"] = caption
    return _post("/view/field/add", body)


def remove_field(view, field):
    """Remove a field (by caption) from a view."""
    return _post("/view/field/remove", {"view": view, "field": field})


def style_field(view, field, color=None, width=None, alignment=None, hidden=None):
    """Change color/width/alignment(0=left,1=right,2=center)/hidden of a field."""
    body = {"view": view, "field": field}
    if color is not None:
        body["color"] = color
    if width is not None:
        body["width"] = int(width)
    if alignment is not None:
        body["alignment"] = int(alignment)
    if hidden is not None:
        body["hidden"] = bool(hidden)
    return _post("/view/field/style", body)


def form_list(filter=None, class_=None):
    """List dream forms (name, class, language). Optional substring/class filter."""
    body = {}
    if filter:
        body["filter"] = filter
    if class_:
        body["class"] = class_
    return _post("/form/list", body)


def form_get(name):
    """Read one form: returns unpacked dfm/script + metadata."""
    return _post("/form/get", {"name": name})


def form_set_script(name, script):
    """Write the [Скрипт] field of a form (packed + audited server-side)."""
    return _post("/form/script/set", {"name": name, "script": script})


def form_set_dfm(name, dfm):
    """Write the [ДФМ] field of a form (packed + audited server-side)."""
    return _post("/form/dfm/set", {"name": name, "dfm": dfm})


def form_check(name=None, script=None, language=None):
    """Light syntax check of a form script (no form build). errLine/errChar/errMessage on failure."""
    body = {}
    if name:
        body["name"] = name
    if script is not None:
        body["script"] = script
    if language:
        body["language"] = language
    return _post("/form/check", body)


def _form_files(name):
    """Local file paths used to round-trip a form's dfm/script for editing."""
    safe = re.sub(r'[^0-9A-Za-zА-Яа-яЁё _-]', '_', name)
    base = os.path.join(os.path.dirname(OUT), "_form_" + safe)
    return base + ".dfm", base + ".pas"


# ---- print templates ([Отчет]) ----

def report_list(filter=None, type=None, group=None):
    """List print templates (key, type, group, changed). Optional filters."""
    body = {}
    if filter:
        body["filter"] = filter
    if type:
        body["type"] = type
    if group:
        body["group"] = group
    return _post("/report/list", body)


def report_get(name):
    """Read one template: meta + base64 body + base64 [Данные]."""
    return _post("/report/get", {"name": name})


def report_set_template(name, body_bytes, body_kind=None):
    """Write the template body column matching the type (base64, packed server-side)."""
    payload = {"name": name, "body": base64.b64encode(body_bytes).decode("ascii")}
    if body_kind:
        payload["bodyKind"] = body_kind
    return _post("/report/template/set", payload)


def report_set_data(name, data_bytes):
    """Write the [Данные] master-detail config (base64, packed server-side)."""
    return _post("/report/data/set",
                 {"name": name, "data": base64.b64encode(data_bytes).decode("ascii")})


def report_show(name, params=None):
    """Open the prepared report preview in the .exe by name (blocks until closed)."""
    body = {"name": name}
    if params:
        body["params"] = params
    return _post("/report/show", body, timeout=600)


def report_print(name, params=None):
    """Print the report by name (blocks until the preview/print dialog closes)."""
    body = {"name": name}
    if params:
        body["params"] = params
    return _post("/report/print", body, timeout=600)


def report_print_doc(table, ids=None, vid=None):
    """Document-linked print dialog (N instances by record list)."""
    body = {"table": table}
    if ids:
        body["ids"] = ids
    if vid:
        body["vid"] = vid
    return _post("/report/print-doc", body, timeout=600)


# ---- posting generation ([Генерация] -> _авто_Документ_<N>_генерация -> [Проводка]) ----

def gen_doc_vids():
    """Document kinds that have generation settings (vid, name, rules, has_proc)."""
    return _post("/gen/doc-vids", {})


def gen_rules(docvid):
    """All generation rules for a document kind."""
    return _post("/gen/rules", {"docvid": int(docvid)})


def gen_rule_get(key):
    """One generation rule ([Генерация]), all columns."""
    return _post("/gen/rule/get", {"key": int(key)})


def gen_rule_set(key, fields):
    """Update rule fields (dict column->value) and auto-refresh the stored proc.
    Value None writes SQL NULL; other values are typed server-side by column type,
    so numbers may be passed as strings ('10.9' -> varchar, '5' -> int/money)."""
    return _post("/gen/rule/set", {"key": int(key), "fields": fields}, timeout=600)


def gen_proc_sql(docvid):
    """Generated CREATE PROCEDURE text for a kind (NOT executed)."""
    return _post("/gen/proc/sql", {"docvid": int(docvid)}, timeout=600)


def gen_proc_db(docvid):
    """Current stored-proc text from the DB (OBJECT_DEFINITION)."""
    return _post("/gen/proc/db", {"docvid": int(docvid)})


def gen_proc_refresh(docvid):
    """(Re)create the per-kind generation stored procedure (ALTER if it exists)."""
    return _post("/gen/proc/refresh", {"docvid": int(docvid)}, timeout=600)


def gen_proc_recreate(docvid):
    """DROP + CREATE the per-kind generation stored procedure (clean rebuild)."""
    return _post("/gen/proc/recreate", {"docvid": int(docvid)}, timeout=600)


def gen_run(docid):
    """Run generation for one document by key (writes [Проводка] + [История])."""
    return _post("/gen/run", {"docid": int(docid)}, timeout=600)


def gen_provodki(docid):
    """Postings produced for a document (read back [Проводка])."""
    return _post("/gen/provodki", {"docid": int(docid)})


def _gen_proc_file(docvid, suffix=""):
    """Local .sql path to save a generation procedure's text for inspection."""
    return os.path.join(os.path.dirname(OUT), "_gen_proc_%s%s.sql" % (docvid, suffix))


def _report_files(name, ext):
    """Local file paths to round-trip a template body / its [Данные] config."""
    safe = re.sub(r'[^0-9A-Za-zА-Яа-яЁё _-]', '_', name)
    base = os.path.join(os.path.dirname(OUT), "_report_" + safe)
    return base + ext, base + ".data"


def _save(obj):
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    if args[0] == "--ping":
        res = ping()
        _save(res)
        print(json.dumps(res, ensure_ascii=False))
        return

    def flags(rest):
        o = {}
        j = 0
        while j < len(rest):
            if rest[j].startswith("--"):
                o[rest[j][2:]] = rest[j + 1]; j += 2
            else:
                j += 1
        return o

    # ---- named query (SchemaView) commands ----
    if args[0] == "--query-list":
        o = flags(args[1:])
        res = query_list(filter=o.get("filter"), root=o.get("root"),
                         top=o.get("top", 200))
        _save(res)
        if res.get("ok"):
            print(f"OK count={res.get('count')} -> tools\\_out.txt")
            for v in res.get("views", [])[:100]:
                mark = "  [оборотка]" if v.get("oborot") else ""
                print(f"  {v['name']}  <- {v['root']}{mark}")
        else:
            print(f"ERROR: {res.get('error')}")
        return

    # ---- dream form commands ----
    if args[0] == "--form-list":
        o = flags(args[1:])
        res = form_list(filter=o.get("filter"), class_=o.get("class"))
        _save(res)
        if res.get("ok"):
            print(f"OK count={res.get('count')} -> tools\\_out.txt")
            for f in res.get("forms", [])[:50]:
                print(f"  {f['name']}  [{f['class']}/{f['language']}]")
        else:
            print(f"ERROR: {res.get('error')}")
        return

    if args[0] == "--form-get":
        name = args[1]
        res = form_get(name)
        _save(res)
        if res.get("ok"):
            fdfm, fscr = _form_files(name)
            # newline="" preserves the form's exact CRLF/LF bytes (no Windows translation)
            with open(fdfm, "w", encoding="utf-8", newline="") as f:
                f.write(res.get("dfm", ""))
            with open(fscr, "w", encoding="utf-8", newline="") as f:
                f.write(res.get("script", ""))
            print(f"OK class={res.get('class')} language={res.get('language')}")
            print(f"  dfm    -> {fdfm}")
            print(f"  script -> {fscr}")
        else:
            print(f"ERROR: {res.get('error')}")
        return

    if args[0] == "--form-check":
        name = args[1] if len(args) > 1 and not args[1].startswith("--") else None
        o = flags(args[1:])
        script = None
        if o.get("script"):
            with open(o["script"], "r", encoding="utf-8", newline="") as f:
                script = f.read()
        res = form_check(name=name, script=script, language=o.get("language"))
        _save(res)
        if res.get("ok"):
            if res.get("valid"):
                print("VALID")
            else:
                print(f"INVALID line {res.get('errLine')} char {res.get('errChar')}: {res.get('errMessage')}")
        else:
            print(f"ERROR: {res.get('error')}")
        return

    if args[0] in ("--form-set-script", "--form-set-dfm"):
        name = args[1]
        path = args[2]
        with open(path, "r", encoding="utf-8", newline="") as f:
            text = f.read()
        # auto-backup current content first
        cur = form_get(name)
        if cur.get("ok"):
            fdfm, fscr = _form_files(name + "_backup")
            with open(fdfm, "w", encoding="utf-8", newline="") as f:
                f.write(cur.get("dfm", ""))
            with open(fscr, "w", encoding="utf-8", newline="") as f:
                f.write(cur.get("script", ""))
            print(f"backup -> {fdfm} ; {fscr}")
        if args[0] == "--form-set-script":
            res = form_set_script(name, text)
        else:
            res = form_set_dfm(name, text)
        _save(res)
        print("OK -> tools\\_out.txt" if res.get("ok") else f"ERROR: {res.get('error')}")
        return

    # ---- print template ([Отчет]) commands ----
    if args[0] == "--report-list":
        o = flags(args[1:])
        res = report_list(filter=o.get("filter"), type=o.get("type"), group=o.get("group"))
        _save(res)
        if res.get("ok"):
            print(f"OK count={res.get('count')} -> tools\\_out.txt")
            for r in res.get("reports", [])[:50]:
                print(f"  [{r['type']}] {r['key']}  ({r.get('group','')})  {r.get('changed','')}")
        else:
            print(f"ERROR: {res.get('error')}")
        return

    if args[0] == "--report-get":
        name = args[1]
        res = report_get(name)
        _save(res)
        if res.get("ok"):
            fbody, fdata = _report_files(name, res.get("ext", ".bin"))
            with open(fbody, "wb") as f:
                f.write(base64.b64decode(res.get("body", "")))
            with open(fdata, "wb") as f:
                f.write(base64.b64decode(res.get("data", "")))
            print(f"OK type={res.get('type')} bodyField={res.get('bodyField')} "
                  f"bodyKind={res.get('bodyKind')} copies={res.get('copies')}")
            print(f"  body -> {fbody}")
            print(f"  data -> {fdata}")
        else:
            print(f"ERROR: {res.get('error')}")
        return

    if args[0] in ("--report-set-template", "--report-set-data"):
        name = args[1]
        path = args[2]
        o = flags(args[3:])
        # auto-backup current template first (body + data)
        cur = report_get(name)
        if cur.get("ok"):
            bbody, bdata = _report_files(name + "_backup", cur.get("ext", ".bin"))
            with open(bbody, "wb") as f:
                f.write(base64.b64decode(cur.get("body", "")))
            with open(bdata, "wb") as f:
                f.write(base64.b64decode(cur.get("data", "")))
            print(f"backup -> {bbody} ; {bdata}")
        with open(path, "rb") as f:
            data = f.read()
        if args[0] == "--report-set-template":
            res = report_set_template(name, data, body_kind=o.get("kind"))
        else:
            res = report_set_data(name, data)
        _save(res)
        print("OK -> tools\\_out.txt" if res.get("ok") else f"ERROR: {res.get('error')}")
        return

    if args[0] in ("--report-show", "--report-print"):
        name = args[1]
        params = {}
        i = 2
        while i < len(args):
            if args[i] in ("-p", "--param"):
                k, _, v = args[i + 1].partition("=")
                params[k] = v
                i += 2
            else:
                i += 1
        fn = report_show if args[0] == "--report-show" else report_print
        res = fn(name, params or None)
        _save(res)
        print("OK -> tools\\_out.txt" if res.get("ok") else f"ERROR: {res.get('error')}")
        return

    if args[0] == "--report-print-doc":
        table = args[1]
        o = flags(args[2:])
        res = report_print_doc(table, ids=o.get("ids"), vid=o.get("vid"))
        _save(res)
        print("OK -> tools\\_out.txt" if res.get("ok") else f"ERROR: {res.get('error')}")
        return

    # ---- posting generation commands ----
    if args[0] == "--gen-doc-vids":
        res = gen_doc_vids()
        _save(res)
        if res.get("ok"):
            print(f"OK count={res.get('count')} -> tools\\_out.txt")
            for d in res.get("docvids", [])[:300]:
                flag = "proc" if d.get("has_proc") else "----"
                print(f"  [{flag}] вид={str(d.get('vid')):>5}  rules={str(d.get('rules')):>3}  {d.get('name','')}")
        else:
            print(f"ERROR: {res.get('error')}")
        return

    if args[0] == "--gen-rules":
        res = gen_rules(args[1])
        _save(res)
        if res.get("ok"):
            print(f"OK docvid={res.get('docvid')} count={res.get('count')} -> tools\\_out.txt")
            for r in res.get("rules", [])[:300]:
                print(f"  Ключ={r.get('Ключ')}  приор={r.get('Приоритет')}  "
                      f"{r.get('Дебет')} / {r.get('Кредит')}  Сумма={r.get('Сумма')!r}")
        else:
            print(f"ERROR: {res.get('error')}")
        return

    if args[0] == "--gen-rule-get":
        res = gen_rule_get(args[1])
        _save(res)
        print("OK -> tools\\_out.txt" if res.get("ok") else f"ERROR: {res.get('error')}")
        return

    if args[0] == "--gen-rule-set":
        key = args[1]
        fields = {}
        i = 2
        while i < len(args):
            if args[i] in ("-f", "--field"):
                k, _, v = args[i + 1].partition("=")
                fields[k] = None if v == "@null" else v
                i += 2
            else:
                i += 1
        if not fields:
            print("ERROR: no fields given (use -f \"Колонка=значение\")")
            return
        res = gen_rule_set(key, fields)
        _save(res)
        if res.get("ok"):
            print(f"OK key={res.get('key')} docvid={res.get('docvid')} "
                  f"updated={res.get('updated')} (proc refreshed) -> tools\\_out.txt")
        else:
            print(f"ERROR: {res.get('error')}")
        return

    if args[0] in ("--gen-proc-sql", "--gen-proc-db"):
        docvid = args[1]
        res = gen_proc_sql(docvid) if args[0] == "--gen-proc-sql" else gen_proc_db(docvid)
        _save(res)
        if res.get("ok"):
            suffix = "" if args[0] == "--gen-proc-sql" else "_db"
            fn = _gen_proc_file(docvid, suffix)
            with open(fn, "w", encoding="utf-8", newline="") as f:
                f.write(res.get("sql", ""))
            extra = "" if res.get("exists", True) else "  (proc does NOT exist in DB)"
            print(f"OK name={res.get('name')}{extra}")
            print(f"  sql -> {fn}")
        else:
            print(f"ERROR: {res.get('error')}")
        return

    if args[0] in ("--gen-proc-refresh", "--gen-proc-recreate"):
        fn = gen_proc_refresh if args[0] == "--gen-proc-refresh" else gen_proc_recreate
        res = fn(args[1])
        _save(res)
        if res.get("ok"):
            print(f"OK {res.get('name')} action={res.get('action')}")
        else:
            print(f"ERROR: {res.get('error')}")
        return

    if args[0] == "--gen-run":
        res = gen_run(args[1])
        _save(res)
        if res.get("ok"):
            print(f"OK docid={res.get('docid')} docvid={res.get('docvid')} "
                  f"provodki={res.get('provodki')}")
        else:
            print(f"ERROR: {res.get('error')}")
        return

    if args[0] == "--gen-provodki":
        res = gen_provodki(args[1])
        _save(res)
        if res.get("ok"):
            print(f"OK docid={res.get('docid')} count={res.get('count')} -> tools\\_out.txt")
            for pr in res.get("provodki", [])[:300]:
                print(f"  {pr.get('Дебет')} -> {pr.get('Кредит')}  "
                      f"Сумма={pr.get('Сумма')}  {pr.get('Примечание','')}")
        else:
            print(f"ERROR: {res.get('error')}")
        return

    if args[0] in ("--add", "--remove", "--style"):
        op = args[0][2:]
        view = args[1]
        o = flags(args[3:])
        if op == "add":
            res = add_field(view, args[2], color=o.get("color"),
                            width=o.get("width"), caption=o.get("caption"))
        elif op == "remove":
            res = remove_field(view, args[2])
        else:
            res = style_field(view, args[2], color=o.get("color"),
                              width=o.get("width"), alignment=o.get("align"),
                              hidden=(o.get("hidden") in ("1", "true", "yes")) if "hidden" in o else None)
        _save(res)
        if res.get("ok"):
            print("OK -> tools\\_out.txt")
            if res.get("sql"):
                print(res["sql"])
        else:
            print(f"ERROR: {res.get('error')}")
        return

    name = args[0]
    top = None
    params = {}
    sql_mode = False
    i = 1
    while i < len(args):
        a = args[i]
        if a == "--sql":
            sql_mode = True; i += 1; continue
        if a == "--top":
            top = args[i + 1]; i += 2; continue
        if a in ("-p", "--param"):
            k, _, v = args[i + 1].partition("=")
            params[k] = v; i += 2; continue
        i += 1

    if sql_mode:
        res = run_query_sql(name, params or None, top)
        _save(res)
        if res.get("ok"):
            print(res["sql"])
        else:
            print(f"ERROR: {res.get('error')}")
        return

    res = run_query(name, params or None, top)
    _save(res)
    if res.get("ok"):
        cols = ", ".join(c["name"] for c in res.get("columns", []))
        print(f"OK count={res.get('count')} -> tools\\_out.txt")
        print(f"columns: {cols}")
    else:
        print(f"ERROR: {res.get('error')}")


if __name__ == "__main__":
    main()
