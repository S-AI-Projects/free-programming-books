# R10-T021 entry checker

`r10-t021.py` extracts Markdown list entries from the `Algoritmos` and
`Databases` sections of
[`casts/free-podcasts-screencasts-pt_BR.md`](../../casts/free-podcasts-screencasts-pt_BR.md).
Each extracted record includes its display name, exact URL, category, available
author/format metadata, and original source line number. Fenced-code examples
and entries in other categories are excluded; URL fragments are retained.

The selected source entries are:

| Line | Category | Display name | Available metadata |
| ---: | --- | --- | --- |
| 21 | Algoritmos | Curso em Vídeo - Curso de Lógica de Programação | Gustavo Guanabara; screencast |
| 22 | Algoritmos | Portugol Studio | screencast |
| 27 | Databases | Bóson Treinamentos - Curso de Modelagem de Dados | screencast |

Run the check and its offline fixtures from the repository root:

```sh
python3 tools/course_checks/r10-t021.py --self-test
```

The self-test records inputs, expected and actual fixture results, selected
source records, and tool versions in `work/R10-T021/results.json`. It also
checks that the normal checker command exits non-zero for the deliberately
invalid fixture. No network requests are made. To check a specific Markdown
input, pass `--file PATH`; extraction remains limited to the two target
categories.
