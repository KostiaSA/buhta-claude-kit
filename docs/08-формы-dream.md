# 08. Пользовательские формы (dream-движок)

Этот документ описывает, **где БУХта хранит пользовательские формы**, как устроен их движок
(`dream`), как форму **читать / править / проверять синтаксис** программно — через HTTP-канал
автоматизации `bmAutomationServer` (эндпоинты `POST /form/*`).

> Источник: исходники `c:\bm` (Delphi 6, cp1251) и каталог движка `c:\bm\dream`.

---

## 1. Где хранятся формы — таблица `[Форма]`

Все пользовательские формы (диалоги, печатные/экспортные формы, в т.ч. отчёты НДФЛ) — это
**строки таблицы `[Форма]`** (а не отдельные .pas/.dfm файлы на диске).

| Колонка | Назначение |
|---|---|
| `[Имя]` | ключ формы |
| `[Класс]` | тип формы (см. §2) |
| `[ДФМ]` | визуальное описание (DFM-подобный текст), **сжато VCLZip** |
| `[Скрипт]` | логика формы на DelphiScript, **сжато VCLZip** |
| `[Язык]` | язык скрипта (обычно `DelphiScript`) |
| `[Таблица]` | связанная таблица (для `EditForm`/`LookForm`/`LookupForm`) |
| `[Кто изменил]`,`[Когда изменил]`,`[Что изменил]` | аудит |
| `[Метки]` | закладки редактора |

Классы форм (значения `[Класс]`): `Form` (≈397), `HotKeyForm` (≈120), `EditForm` (≈54),
`LookForm` (≈25), `LookupForm` (≈10), `Library` (≈10).

### ⚠️ Сжатие полей `[ДФМ]`/`[Скрипт]`
Эти поля упакованы VCLZip с маркером-префиксом. Читать/писать их можно **только средствами .exe**:
- `UnPackFieldValue(s)` (bmDreamFormUtil.pas) — распаковать;
- `PackFieldValue(s)` (bmDreamFormUtil.pas) — упаковать обратно.

Поэтому Python напрямую к БД эти поля разобрать **не может** — работа идёт через HTTP-эндпоинты.

---

## 2. Движок dream (как форма исполняется)

Движок — самописный интерпретатор Delphi-подобного языка, каталог `c:\bm\dream`:
- `TDCScripter` (`dream\dcscript.pas`) — контейнер формы+скрипта, компиляция и запуск.
- Построение формы по имени: `CreateDreamForm` (`bmDreamFormUtil.pas:1090`) →
  `TFormRunner` + `TSQLFileSystem` (читает ДФМ/Скрипт из БД) + `TDCScripter.Run`.
- Сохранение формы штатным редактором (`bmDreamFormUtil.pas:1337`):
  `UPDATE [Форма] SET [ДФМ]=Pack(...),[Скрипт]=Pack(...),[Кто/Когда изменил]…` + `ClearGlobalDreamScripterCache`
  (сброс кэша скомпилированных скриптов — **без перезапуска .exe**).

### Проверка синтаксиса
`TDCScripter.CheckSyntaxEx2(var ErrLine,ErrChar:integer; var ErrMessage:string; StrictCheck:boolean):boolean`
(`dream\dcscript.pas:6465`) — компилирует `Script.Text`, возвращает `True`/`False` + позицию/текст ошибки.
**Лёгкая** проверка (без построения формы): `TDCScripter.Create(nil)` → `Language:=` → `UseModule:=False` →
`Script.Text:=` → `CheckSyntaxEx2(...,False)`. Ловит реальные синтаксические ошибки; идентификаторы
компонентов формы/глобалы при `StrictCheck=False` не флагуются ложно.

---

## 3. HTTP-эндпоинты (`bmAutomationServer`, тело JSON cp1251)

См. [c:\bm\bmAutomationServer.pas](../../c:/bm/bmAutomationServer.pas) (`TFormJob`/`HandleForm`) и
[tools/buhta_client.py](../tools/buhta_client.py).

- `POST /form/list` — `{"filter"?,"class"?}` → `{"ok":true,"count":N,"forms":[{"name","class","language"}]}`.
- `POST /form/get` — `{"name"}` → `{"ok":true,"name","class","language","table","who","when","dfm","script"}`
  (`dfm`/`script` распакованы). 404 если формы нет.
- `POST /form/script/set` — `{"name","script"}` → запись `[Скрипт]` (упаковка + аудит + сброс кэша). `{"ok":true}`.
- `POST /form/dfm/set` — `{"name","dfm"}` → запись `[ДФМ]` аналогично.
- `POST /form/check` — `{"name"?,"script"?,"language"?}` → если задан `script` — проверить его, иначе
  распаковать сохранённый `[Скрипт]`. Ответ: `{"ok":true,"valid":bool,"errLine":N,"errChar":N,"errMessage":"…"}`.

### Клиент (tools/buhta_client.py)
```bash
python tools/buhta_client.py --form-list --filter НДФЛ            # список форм
python tools/buhta_client.py --form-get "<имя формы>"            # читать; dfm/script -> файлы tools\_form_*
python tools/buhta_client.py --form-check "<имя формы>"          # проверить сохранённый скрипт
python tools/buhta_client.py --form-check "<имя>" --script f.pas # проверить кандидат-скрипт
python tools/buhta_client.py --form-set-script "<имя>" f.pas     # записать [Скрипт] (авто-бэкап)
python tools/buhta_client.py --form-set-dfm "<имя>" f.dfm        # записать [ДФМ] (авто-бэкап)
```
- `--form-get` сохраняет `dfm`/`script` в `tools\_form_<имя>.dfm/.pas` (round-trip для правки).
- Перед каждым `set` делается авто-бэкап текущего содержимого в `tools\_form_<имя>_backup.*`.
- Проверено: Pack/UnPack round-trip **без потерь** (побайтно), кириллица сохраняется.

---

## 4. Границы / безопасность
- Правки идут в **БД подключённого .exe** (клиентская копия); перенос в эталон «Стандартная» — отдельный шаг.
- Проверка синтаксиса — **лёгкая** (без запуска формы, без побочных эффектов).
- Запуск формы и нажатие кнопок (`/form/run`, `/form/click`) — **следующая итерация** (экспериментально:
  init-скрипт формы может открыть модальное окно / сгенерировать отчёт).
- Очень короткие (<5 байт) значения `PackFieldValue` превращает в пусто́ — для реальных форм неактуально.
