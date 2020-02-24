# lectorium-pipeline

В этом репозитории два рабочих инструмента: модифицированный *concat_ng* и конвейер.

## Установка

```bash
$ # Clone
$ git clone https://github.com/bcskda/lectorium-pipeline
$ # Env
$ python3 -m venv .venv
$ source .venv/bin/activate
(.venv) $ pip install -r requirements.txt
```

## main.py

Это *concat_ng* c модификациями:
- Загрузка в облако по завершении предобработки
- Профили предобработки

Типичный вызов:

```bash
(.venv) $ python main.py -i /mnt/media/sdd -o /mnt/media/lectorium-ssd/Lectorium -p concat_compress -u --folder-id=XXYYZZ
```

- ```-p / --profile``` - профиль, общий для всех импортируемых записей
- ```-u / --upload``` - загружать результаты в облако (по умолчанию: нет)
- ```--folder-id``` - ID папки в google drive, куда будут загружены результаты

Можно посмотреть вывод ```python main.py --help``` и подкрутить ```config_default.json```

Профили хранятся в ```ff_presets/v2/PROFILE_NAME.json```

- Входные файлы:
- - Принимаются списком логических групп
- - К группам можно применять протоколы (на данный момент только ```concat```)

- Выходные файлы:
- - Может быть много
- - Входы задаются отдельно для каждого
- - Имена задаются как общий basename из CLI + суффикс

- Разное:
- - Поддержка filter_complex и объявленных фильтрами pad-ов в качестве входов

Сейчас профиля два: склейка со сжатием и без

#### Что плохого

- Нужно запускать для каждой карты, как *concat_ng*

- Не создаёт в облаке подпапки по датам (исправимо, TODO)

#### Что хорошего

- Сам загружает в облако

- Проще, чем конвейер

- До сих пор не сбоил

## pipeline

Конвейер, от поиска видео до загрузки до загрузки в облако. После старта достаточно подключать карты памяти.

Типичный запуск (в трёх шеллах, поскольку не форкаются):

```bash
(shell 1) python -m daemons.transcoder --importer 127.0.0.1:1338 --bind 127.0.0.1:1337
(shell 2) python -m daemons.importer --transcoder 127.0.0.1:1337 --devwatch 127.0.0.1:1339 --bind 127.0.0.1:1338
(shell 3) python -m daemons.devwatch --importer 127.0.0.1:1338 --bind 127.0.0.1:1339
```

Типичное завершение: Ctrl+C вызовет обработчик. Если в это время происходил импорт - undefined behavior.

Состоит из трёх компонентов.

1) devwatch
- Через udev обнаруживает подключаемые блочные устройства
- Монтирует их в /mnt/lectorium-devwatch-...
- Пытается обнаружить характерные папки (вроде ```PRIVATE/AVCHD/...```
- Посылает обнаруженные директории на импорт
- Отмонтирует устройство, получив сообщение о завершении обработки
- (!) К сожалению, работает от рута

2) importer
- Принимает от предыдущей стадии примонтированные корни карт памяти
- Код из *concat_ng* разбивает записи на группы
- Группы отправляются на предобработка
- По завершении предобработки загружает в облако, создавая папки по датам
- После обработки карты памяти сообщает предыдущей стадии

3) transcoder
- Принимает таски на предобработка
- Сообщает импорту по завершении
- При минимальной доработке масштабируется на соседние хосты в достаточно быстрой сети

#### Что плохого

- Запускаются в трёх разных шеллах, не уходят в фон (решается tmux'ом)

- Неудобные логи - немало лишней информации, но не хватает отметок времени

- Нет ручного контроля процесса: если импортировать, то всё сразу

- Могут быть проблемы с umount обработанных карт - недостаточно тестировалось. (TODO лучше пока исключить этот код)

#### Что хорошего

- Если подключить несколько карт одновременно, последовательно отработает все

- Перекодирование может масштабироваться
