# R10-T021 course-list check

Run `python3 tools/course_checks/r10-t021.py` to print the selected records from
`casts/free-podcasts-screencasts-pt_BR.md` as JSON. Each record includes its
original source line, display name, URL, heading category, raw trailing
metadata, and parsed creator/resource type when present.

The checker is limited to these three playlist URLs:

| Display name | URL | Category | Source line | Metadata |
| --- | --- | --- | ---: | --- |
| Curso em Vídeo - Curso de Lógica de Programação | [Playlist](https://www.youtube.com/playlist?list=PLHz_AreHm4dmSj0MHol_aoNYCSGFqvfXV) | Algoritmos | 21 | Gustavo Guanabara; screencast |
| Portugol Studio | [Playlist](https://www.youtube.com/playlist?list=PLJ4lbwalqv3Eaiay2pCeU_QU6vb-Hz989) | Algoritmos | 22 | screencast |
| Bóson Treinamentos - Curso de Modelagem de Dados | [Playlist](https://www.youtube.com/playlist?list=PLucm8g_ezqNoNHU8tjVeHmRGBFnjDIlxD) | Databases | 27 | screencast |

Run `python3 tools/course_checks/r10-t021.py --self-test` for offline success
and failure fixtures. The tests verify fenced-code exclusion, fragment
preservation, source line mapping, metadata extraction, and nonzero failure
behavior when a selected entry is missing. No HTTP requests are made, and this
checker does not remove or reject a resource based on link availability.
