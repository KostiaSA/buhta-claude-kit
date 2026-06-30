# buhta-claude-kit

**Плагин Claude Code** (skills + tools + docs) для работы с проектом **«БУХта» (Бухта ERP)** —
legacy-системой учёта. Покрывает **пользовательские формы** (движок dream) и **печатные шаблоны
отчётов** (FastReport), плюс инструменты работы с БД MSSQL и HTTP-сервером автоматизации `.exe`.

> Расчёт зарплаты и налогов вынесен в **отдельный плагин** `buhta-zarplata`
> (репозиторий https://github.com/KostiaSA/buhta-claude-zp-kit, приватный).

## Репозитории

| Плагин | Репозиторий | Видимость | Содержимое |
|---|---|---|---|
| `buhta` (этот) | https://github.com/KostiaSA/buhta-claude-kit | public | формы dream + печатные шаблоны + tools |
| `buhta-zarplata` | https://github.com/KostiaSA/buhta-claude-zp-kit | private | расчёт зарплаты/налогов + procs |

Репозиторий — **единый источник правды** для skills и tools. Он самодостаточен: не требует
исходников Delphi-проекта BM и читается на любом компьютере (`git clone`). Подключается как плагин,
**не трогая родной `.claude` целевого проекта**:

```
# на любом проекте/ПК:
/plugin marketplace add KostiaSA/buhta-claude-kit
/plugin install buhta@buhta-claude
# на dev-машине (правки сразу, без push):
claude --plugin-dir <путь>/buhta-claude-kit
```

Параметры подключения к MSSQL задаются через userConfig плагина (Claude спросит при включении),
либо env `BUHTA_SERVER/BUHTA_DB/BUHTA_UID/BUHTA_PWD`, либо локальный `tools/db.local.json`
(скопировать из `tools/db.example.json`; не коммитится). Инструменты в скиллах вызываются как
`python "${CLAUDE_PLUGIN_ROOT}/tools/<script>.py"`.

## Структура каталога

- [skills/](skills/) — скилы плагина: `buhta-forms` (формы dream), `buhta-reports` (печатные шаблоны).
- [docs/](docs/) — документация: схема данных и запросы, формы dream, руководства по формам и отчётам.
- [tools/](tools/) — python-хелперы:
  - `q.py` / `dump.py` / `exec_sql.py` — работа с БД MSSQL (чтение, выгрузка исходников, выполнение SQL);
  - `buhta_client.py` — HTTP-клиент локального сервера автоматизации `.exe` (формы, отчёты, запросы);
  - `validate_xml_xsd.py` — валидация XML против XSD;
  - `dbconfig.py` — резолв параметров подключения; `db.example.json` — шаблон кредов.
- [.claude-plugin/](.claude-plugin/) — манифест плагина (`plugin.json`) и маркетплейс (`marketplace.json`).

## Требования

- Python 3 + `pyodbc` + ODBC Driver 18 for SQL Server (для `q.py`/`dump.py`/`exec_sql.py`);
- `lxml` — для `validate_xml_xsd.py`;
- запущенный `bmProject.exe` с сервером автоматизации `127.0.0.1:8765` — для `buhta_client.py`.

> Подробная документация по подсистеме зарплаты/налогов и тексты заявок ведутся отдельно
> (в приватной рабочей копии рядом с исходниками BM) и в этот публичный комплект не входят.
