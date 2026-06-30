#!/usr/bin/env python
"""Единый резолв подключения к MSSQL и путей для tools БУХты.

Креды берутся по приоритету (первый найденный источник выигрывает):
  1. userConfig плагина  -> env CLAUDE_PLUGIN_OPTION_server/database/uid/pwd
     (заполняется Claude Code при включении плагина)
  2. отдельные env       -> BUHTA_SERVER / BUHTA_DB / BUHTA_UID / BUHTA_PWD
  3. локальный файл      -> tools/db.local.json  (gitignored)

`database` дополнительно можно переопределить через BUHTA_DB (напр. клиентская копия
<база_клиента>) поверх любого источника.

Файл db.local.json (не коммитится) — копия db.example.json с реальным паролем.
"""
import os
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_CFG = os.path.join(SCRIPT_DIR, "db.local.json")

DEFAULT_DRIVER = "ODBC Driver 18 for SQL Server"


def out_path(name="_out.txt"):
    """Путь к файлу вывода рядом со скриптами (портативно, без хардкода диска)."""
    return os.path.join(SCRIPT_DIR, name)


def procs_dir():
    """Каталог для выгрузки исходников процедур."""
    d = os.path.join(SCRIPT_DIR, "procs")
    os.makedirs(d, exist_ok=True)
    return d


def _from_local_file():
    if os.path.exists(LOCAL_CFG):
        with open(LOCAL_CFG, encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_db_config():
    """Вернуть dict {server, database, uid, pwd, driver}, собранный из источников."""
    local = _from_local_file()

    def pick(plugin_key, env_key, local_key, default=None):
        return (
            os.environ.get("CLAUDE_PLUGIN_OPTION_" + plugin_key)
            or os.environ.get(env_key)
            or local.get(local_key)
            or default
        )

    cfg = {
        "server":   pick("server",   "BUHTA_SERVER", "server"),
        "database": pick("database", "BUHTA_DB",     "database"),
        "uid":      pick("uid",      "BUHTA_UID",    "uid"),
        "pwd":      pick("pwd",      "BUHTA_PWD",    "pwd"),
        "driver":   pick("driver",   "BUHTA_DRIVER", "driver", DEFAULT_DRIVER),
    }
    # BUHTA_DB имеет приоритет на переключение БД (клиентская копия и т.п.)
    if os.environ.get("BUHTA_DB"):
        cfg["database"] = os.environ["BUHTA_DB"]

    missing = [k for k in ("server", "database", "uid", "pwd") if not cfg[k]]
    if missing:
        raise SystemExit(
            "Не заданы параметры подключения к MSSQL: " + ", ".join(missing) + ".\n"
            "Задайте их одним из способов:\n"
            "  - userConfig плагина (Claude Code спросит при включении плагина buhta);\n"
            "  - переменные окружения BUHTA_SERVER/BUHTA_DB/BUHTA_UID/BUHTA_PWD;\n"
            "  - файл tools/db.local.json (скопируйте из tools/db.example.json).\n"
        )
    return cfg


def get_conn_str():
    """Строка подключения ODBC для pyodbc.connect()."""
    c = get_db_config()
    return (
        "DRIVER={%s};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s;TrustServerCertificate=yes"
        % (c["driver"], c["server"], c["database"], c["uid"], c["pwd"])
    )
