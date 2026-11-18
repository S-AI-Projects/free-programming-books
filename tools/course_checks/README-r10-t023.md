# R10-T023 conservative duplicate checker

Run `python3 tools/course_checks/r10-t023.py` to print the three assigned Czech
resource records and duplicate groups. Records retain their category and original
source line.

The checker is limited to the Czech resource list and is scoped by the following
fixed entries:

| Display name | URL | Category | Source line |
| --- | --- | --- | ---: |
| Bash očima Bohdana Milara | [PDF](http://i.iinfo.cz/files/root/k/bash_ocima_bohdana_milara.pdf) | Bash | 32 |
| Systémové programování v jazyce C# | [PDF](https://phoenix.inf.upol.cz/esf/ucebni/sysprog.pdf) | C# | 37 |
| Moderní programování objektových aplikací v C++ | [PDF](https://akela.mendelu.cz/~xvencal2/CPP/opora.pdf) | C++ | 42 |

Normalization is deliberately conservative: scheme and hostname case, HTTP/HTTPS
default ports, trailing path slashes, and query parameter order are normalized.
Paths, schemes, fragments, and query values remain distinct. Exact URL groups are
reported separately from normalized-only groups.

Run `python3 tools/course_checks/r10-t023.py --self-test` for exact duplicate,
normalization, fenced-code, distinct-fragment, query-value, parameter-order,
scheme-difference, and failing-assertion fixtures. A failed assertion exits
non-zero. The tool proposes no deletion; shared landing pages need manual review.

Generated run evidence is written to `work/R10-T023/`. The checker uses only
the Python standard library.
