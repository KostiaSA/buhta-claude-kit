---
name: buhta-forms
description: Создание и редактирование пользовательских форм в legacy-системе БУХта (движок dream, DelphiScript). Используй, когда просят найти/посмотреть/изменить форму, её визуал (ДФМ) или скрипт: «добавь кнопку/поле/чекбокс на форму», «измени форму печати/диалог», «исправь скрипт формы», «проверь синтаксис формы», «вызови отчёт из формы», «экспорт в XML/Excel из формы», работа с формами печати НДФЛ/СЗВ/РСВ/6-НДФЛ/ЕФС. Триггеры: «форма», «ДФМ»/«DFM», «скрипт формы», «dream», «TbuhtaButton/TbuhtaDBEdit/TSimpleForm», «добавь кнопку», «обработчик OnClick», имена форм из таблицы [Форма].
---

# Создание и редактирование форм БУХты (dream)

## Что это
Пользовательские формы БУХты (диалоги, печать, экспорт — НДФЛ, СЗВ, РСВ, ЕФС и т.п.) хранятся в
таблице `[Форма]`: `[ДФМ]` — визуал (DFM-текст), `[Скрипт]` — логика на **DelphiScript** (движок
dream). Оба поля **сжаты** — читать/писать только через HTTP-эндпоинты `/form/*` (.exe должен быть
запущен и авторизован). **Полное руководство — [docs/09-руководство-по-формам.md](../../docs/09-руководство-по-формам.md)**,
устройство хранения/эндпоинты — [docs/08-формы-dream.md](../../docs/08-формы-dream.md).

## Рабочий процесс (инструменты tools/)
> Запускай инструменты как `python "${CLAUDE_PLUGIN_ROOT}/tools/<script>.py" …`
> (в примерах ниже `tools/` = `${CLAUDE_PLUGIN_ROOT}/tools/`; туда же пишутся `_form_*`/`_out.txt`).
```bash
python tools/buhta_client.py --form-list --filter <подстрока> [--class Form]   # найти форму
python tools/buhta_client.py --form-get "<имя>"          # dfm/script -> tools\_form_<имя>.dfm/.pas
# править локально tools\_form_<имя>.pas / .dfm
python tools/buhta_client.py --form-check "<имя>" --script tools\_form_<имя>.pas   # синтаксис ДО записи
python tools/buhta_client.py --form-set-script "<имя>" tools\_form_<имя>.pas       # записать [Скрипт]
python tools/buhta_client.py --form-set-dfm "<имя>" tools\_form_<имя>.dfm          # записать [ДФМ]
# открыть форму в .exe и проверить; откат — из tools\_form_<имя>_backup.*
```

## Железные правила
1. **Синтаксис перед записью:** всегда `--form-check` до `--form-set-script` (ответ `valid` + `errLine/errChar/errMessage`).
2. **Только через /form/*** (поля сжаты VCLZip; ручная правка в БД испортит данные).
3. **Бэкап есть** — перед каждым `set` авто-сохранение `_backup.*`. Правки idут в БД запущенного .exe (клиентская копия), эталон «Стандартная» не трогаем.
4. **Класс обработчика = корневой класс формы из ДФМ** (`TSimpleForm`/`THotKeyForm`/…): менять нельзя.
5. Сначала `--form-get`, посмотреть структуру; не выдумывать имена компонентов/полей — брать из формы и схемы.
6. **Концы строк CRLF:** скрипты/ДФМ хранятся с `\r\n`. Клиент уже читает/пишет файлы с `newline=""` (без удвоения). Если правишь другим инструментом — сохраняй CRLF, не добавляй пустые строки (иначе в редакторе появятся лишние переводы строк). Схлопнуть задвоенные: `replace('\r\n\r\n','\r\n')`.

## Ключевые паттерны
- **Обработчик события:** в ДФМ `OnClick = ИмяProc` (или `OnShow = bmFormShow`), в скрипте —
  `procedure T<КлассКорневойФормы>.ИмяProc(Sender: TObject); begin ... end;`.
- **Доступ к компонентам по Name:** `NumEdit.Value`, `ResultLabel.Caption := '…'`, `OkButton.Enabled := False`.
- **Координаты ДФМ** — пиксели; «внизу слева» = малый `Left`, большой `Top`, `Anchors = [akLeft, akBottom]`.
- **Кириллица в ДФМ** — коды `#NNNN` (или обычная строка в апострофах).

## Топ-функции скрипта
- Данные: `GetValueFromSQL(SQL): Variant` (скаляр, самая частая), `ExecuteSQL(SQL)`, объект `bm` (`bm.UserName/Kontora`, `bm.GetValueFromSQL`).
- SQL-литералы: `StringAsSQL`, `DateAsSQL`, `IntegerAsSQL`, `PeriodAsSQL`.
- Сообщения: `bmInformation`, `bmError`, `bmConfirmation(msg):Boolean`.
- Отчёты: `ShowReport(name)`, `ShowReportWithParam(name, NewParam)`, `ShowArchiveReport(Self, ID)`, `PrintReport(name)`; параметры через `SetGlobalVar(name,val)`.
- Формы/диалоги: `ShowForm(name)`, `DialogPeriod`, `DialogKadryID`, `DialogSQLList(SQL)`.
- Утилиты: `VarToStr`, `IntToStr`, `FormatCurr`, `Now/Year/Month`.

## Компоненты ДФМ (частые)
`TbuhtaButton` (TBitBtn: Left/Top/Width/Height/Caption/OnClick), `TbuhtaLabel`, `TbuhtaDBEdit`
(FieldType/LookupTable/LookupForm/Value/OnChanged), `TbuhtaView`+`TbuhtaGrid`+`TbmColumn`
(встроенный запрос+грид), период-эдит (`OnChanged`→PeriodEditChanged), `TCheckBox`/`TRadioButton`,
`TbuhtaPageControl`/`TTabSheet`, `TbuhtaFormPlacement` (служебный).

## Сценарии (см. docs/09 §5 с примерами кода)
- (a) печатный отчёт/диалог параметров → `ShowReport`/`ShowArchiveReport`;
- (b) экспорт в XML (MSXML `CreateOleObject('MSXML.DOMDocument')` + хелперы `SetOneNodeAttr`/`AddOneNodeText`/`GetNextFile_XML`);
- (c) Excel через COM (`GetReportAsOLEObject`, `MyExcel.Workbooks[1]...Cells[..]`, `SaveFromOleObjectToArchive`);
- (d) HotKeyForm-действие (ввод→валидация `OkInputData`→`bmConfirmation`→`ExecuteSQL`);
- (e) Library (общие функции без UI); (f) EditForm/LookForm/LookupForm (привязка к таблице);
- (g) импорт из текстового файла (`AssignFile/Reset/ReadLn/Eof/CloseFile`);
- (h) экспорт в DBF (`TDbf` + `DateAsDBF`); (и) запрос к веб-сервису ФНС (`Msxml2.ServerXMLHTTP.6.0`, SOAP);
- (к) **WMS-форма терминала ТСД** (`PocketPCForm`/`TPocketPCForm`): событие сканера
  `bmFormBarCodeRead` (код в `bm.BarCode`), `PlaySoundOnPocketPC`, парсинг GS1/маркировки
  (`bmGS1BarcodeUnit`), доменные ТМЦ/паллет-хелперы из Library-формы WMS. Подробно — docs/09 §10.

## Дополнительные библиотеки функций
Скриптам доступны целые юниты Delphi (рег. в `c:\bm\import\*_imp.pas`): даты (`bmDate`:
`FirstDayOfMonth/LastDayOfMonth/FirstDayOfYear/Quarter/IsMonthPeriod/StrToDateDef`), строки
(`rxStrUtils`: `WordCount/ExtractWord/LeftStr/RightStr/DelChars/IsWild`), утилиты (`bmUtil`:
`VariantAsSQL/DateAsDBF/bmRound/DeleteLastChar`), `Variants` (`VarToStrDef`), стандартные
(`SysUtils/Classes/Dialogs/ComObj/Dbf` + файловый I/O). Нет функции в списках — ищи в `import\*_imp.pas`
или просто проверь `--form-check`. Методы: `PeriodEdit.SetPeriodValue(dt)`, `Grid.IsRowSelected(node)`.

## Рецепт: добавить кнопку, показывающую число строк/значение
1. `--form-get "<форма>"` → определить корневой класс (строка `object X: T<Класс>`), размеры, низ формы.
2. В ДФМ вставить **перед последним `end` корня**:
   ```
     object MyButton: TbuhtaButton
       Left = 8
       Top = <высота_клиента - 35>
       Width = 170
       Height = 25
       Anchors = [akLeft, akBottom]
       Caption = 'Кол-во сотрудников'
       OnClick = MyButtonClick
     end
   ```
3. В скрипт добавить:
   ```pascal
   procedure T<Класс>.MyButtonClick(Sender: TObject);
   begin
     bmInformation('Сотрудников в базе: '
       + VarToStr(GetValueFromSQL('SELECT COUNT(*) FROM [Сотрудник]')));
   end;
   ```
4. `--form-check` → `--form-set-dfm` + `--form-set-script` → проверить в .exe → при необходимости revert.

## Завершение
- После правки: `--form-check` зелёный, форма открывается в .exe без ошибок.
- Кратко отчитаться: что изменено в ДФМ/скрипте, как проверено, что в бэкапе для отката.
- Расчёт зарплаты/налогов и SQL-процедуры — отдельный skill [buhta-zarplata](../buhta-zarplata/SKILL.md).
- Сами **печатные шаблоны** (тело FastReport/Excel/Word, [Данные], печать N экземпляров) — skill
  [buhta-reports](../buhta-reports/SKILL.md) ([docs/10](../../docs/10-руководство-по-отчётам.md)).
  Форма лишь **вызывает** отчёт (`ShowReport`/`PrintReport`); правка самого шаблона — там.
