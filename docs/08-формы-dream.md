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

## 4. Рецепт: обновление списка-справочника из HotKeyForm

`HotKeyForm` вызывается по горячей клавише **из списка** (справочник ТМЦ, Организации и т.п.). После
`ExecuteSQL(...)`, изменившего запись, нужно освежить строку в списке-владельце.

### Доступ к владельцу через `Owner`
В скрипте формы `Owner` — это **форма-владелец**, из которой вызвали HotKey (для справочников это
`TbmLookForm`/`TTMCLookForm`/`TOrgLookForm`, `bmLookFormUnit.pas:16`). Опубликованные поля владельца
доступны напрямую: `Owner.Grid`, `Owner.SaveButton` и т.п. (грид справочника — `Grid: TbmGrid`,
`bmLookFormUnit.pas:18`).

### Обновить только текущую (focused) строку
```pascal
Owner.Grid.RefreshRow;   // перечитать из БД и перерисовать ТОЛЬКО текущую строку
```
`TbmGrid.RefreshRow` (`bmGrid.pas:15608`) делает всё как надо: `FView.RecNo:=FocusedNode.Data` →
`View.RefreshRow` (перечитать запись) → `RefreshRow2` (**сбросить кэш ячеек узла** `Node.Strings`) → `Paint`.
Обновляется ровно та запись, что была в фокусе (её `Ключ` и попал во временную таблицу `[#…]`).

Полная перезагрузка списка (тяжелее, когда точечно нельзя): `Owner.Grid.LoadData;`
(оба метода зарегистрированы для скрипта — `import/bmGrid_imp.pas:1124` и `:443`).

### Почему не `OkResult` и не `_SendMessage`
- Встроенный авто-refresh по `OkResult:=True` (`TbmGrid.InternalAfterCallWizard`, `bmGrid.pas:17486`)
  для одиночной строки зовёт **только** `FView.RefreshRow` — **без** `RefreshRow2`/`Paint`. Данные в БД
  меняются, но текст ячейки кэшируется в `Node.Strings` (`GetDrawValue`, `bmGrid.pas:3791`) и остаётся
  старым. Поэтому визуально «не обновляется».
- Паттерн `_SendMessage(Owner.Handle, BM_DOGSPECGRIDREFRESH, 0, 0)` работает **только** для форм, которые
  сами ловят это сообщение (`TbmDogEditForm`, `message BM_DOGSPECGRIDREFRESH`, `bmDogEditForm.pas:221`).
  У `TbmLookForm` такого обработчика нет, а `BM_GridLoadData` даже не зарегистрирован как скрипт-константа —
  поэтому для справочника проще и надёжнее вызвать метод грида напрямую (`Owner.Grid.RefreshRow`).

### Частный случай: `_SendMessage` в форму-владельца с обработчиком (рабочий код)
Если владелец — **форма, которая сама ловит сообщение обновления**, то паттерн из «догспека» рабочий:
`Owner` = `TbmDogEditForm`, он обрабатывает `BM_DOGSPECGRIDREFRESH` (`bmDogEditForm.pas:221`) и перерисовывает
свой грид спецификации. `_SendMessage` и `BM_DOGSPECGRIDREFRESH` зарегистрированы для скрипта
(`import/bmVBInterface_imp.pas:2776`, `import/bmConst_imp.pas:1034`):
```pascal
procedure THotKeyForm.FormOkButtonClick(Sender: TObject);
begin
  try
    ExecuteSQL( 'UPDATE Догспец SET [Субконто 1]='+IntegerAsSQL(PodrEdit.Value) +Chr(13)+
      ' ,[Status] = CASE Status WHEN 1 THEN 1 WHEN 4 THEN 1 WHEN 2 THEN 2 WHEN 3 THEN 3 WHEN 0 THEN 2 END '+Chr(13)+
      'FROM [#Изменить подразделение] '+Chr(13)+
      'INNER JOIN #Догспец Догспец ON Догспец.Ключ=RecordID AND [Тип Субконто 1]=''Под'' '+
        'AND [Субконто 1]<>'+IntegerAsSQL(PodrEdit.Value) );
    _SendMessage(Owner.Handle, BM_DOGSPECGRIDREFRESH, 0, 0);   // перерисовать грид догспека
    Owner.SaveButton.Enabled:=True;                            // владелец «испачкан» -> дать сохранить
    bmInformation( 'Записи сохранены.' );
  except
    bmError( 'Ошибка при обработке.' );
  end;
  Close;
end;
```
Отличие от справочника: у `EditForm` данные держатся в памяти (спека договора не сохранена в БД до нажатия
«Сохранить»), поэтому и обновление идёт **сообщением в форму** (она знает, как перечитать свой грид), плюс
взводится `SaveButton.Enabled`. У `LookForm` данные уже в БД — там точечный `Owner.Grid.RefreshRow`.

### Готовый образец
```pascal
procedure THotKeyForm.FormOkButtonClick(Sender: TObject);
begin
  try
    ExecuteSQL( 'UPDATE ТМЦ SET [_КодЗаповедника]='+IntegerAsSQL(SertEdit.Value)+
      ' FROM [#Проставить Код Заповедника] '+
      ' INNER JOIN ТМЦ ON ТМЦ.Ключ=RecordID AND [_КодЗаповедника]<>'+IntegerAsSQL(SertEdit.Value) );
    Owner.Grid.RefreshRow;                        // обновить только текущую строку списка
    bmInformation( 'Код Заповедника сохранён.' );
  except
    bmError( 'Ошибка при обработке.' );
  end;
  Close;
end;
```
Вызывать `Owner.Grid.RefreshRow` **до** `Close` (пока владелец жив и focused-узел на месте).

---

## 5. Границы / безопасность
- Правки идут в **БД подключённого .exe** (клиентская копия); перенос в эталон «Стандартная» — отдельный шаг.
- Проверка синтаксиса — **лёгкая** (без запуска формы, без побочных эффектов).
- Запуск формы и нажатие кнопок (`/form/run`, `/form/click`) — **следующая итерация** (экспериментально:
  init-скрипт формы может открыть модальное окно / сгенерировать отчёт).
- Очень короткие (<5 байт) значения `PackFieldValue` превращает в пусто́ — для реальных форм неактуально.
