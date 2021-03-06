## Профили перекодирования 

Все профили:
- склеивают входные файлы - т.к. имеющиеся камеры пишут блоками по 2~4 ГБ
- перекодируют звук в общепринятые кодеки - mp3 и aac

Профили различаются:
- наличием сжатия - \*_compress_\*
- наличием разделения звуковых дорожек - \*_fbsound_\*
- наличием аппаратного ускорения h.264 - \*_nvenc_\*

Имеющиеся профили - неполный комбинаторный перебор сочетаний.

### Сжатие

Имеющиеся камеры пишут MPEG-TS, сырой размер одной полуторачасовой лекции - около 20 ГБ. Почти всегда имеет смысл сжать исходник до передачи монтирующему. Вариант без аппаратного ускорения использует CRF, с - постоянный битрейт 3Mbps. Характерный размер на выходе - 1.5~2.5 ГБ.

### Разделение дорожек

На случай проблем с радиопетлями, новые камеры пишут в два каналы единственной звуковой дорожки из разных источников. В правый - звук с радиопетель, предпочтителен при монтаже. В левый - звук с камеры, резерв. Для удобства монтирующих _fbsound_-профили вырезают из контейнера резервную дорожку и сохраняют отдельным файлом.

### Аппаратное ускорение

Поддерживается NVidia, необходимы CUDA и _(проверить необходимость)_ модуль ядра nvidia. Для сравнения, на i7-8750H: и GTX 1070:
- без - скорость 1.2x на libx264 (12 потоков) + libmp3lame (1 поток) - 2.20 GHz
- с - скорость 6x на h264_nvenc _(todo)_ + libmp3lame (1 поток) - 3.80 GHz, 11% _GPU utilization_

Ноутбукам с их охлаждением может стать нехорошо от 80°C.

### Как устроены профили

У профиля, глобально, есть входы, выходы и граф фильтров.

Ко входам можно применять протоколы ffmpeg. Например, можно указать протокол concat для одного из входов и подать список имён файлов - список отобразится в ``concat:1.MTS|2.MTS``.

Как и в ffmpeg filtergraph, у каждого выхода профиля есть _входные вершины_. Ими могут быть целые входы, отдельные дорожки входов либо выходы фильтров. Можно ссылаться стандартно для ffmpeg: на входы - ``stream`` или ``stream:track``, на фильтры - по меткам pad'ов.

Также у каждого выхода есть постоянный суффикс, добавляемый к имени выходного файла: например, ``.fallback_sound.mp3``.

Граф фильтров передаётся в ffmpeg как ``-filter_complex``. Позволяет автоматизировать манипуляции со звуком и, в принципе, простейший монтаж _(TODO)_.
