# R10-T023 duplicate checker

`r10-t023.py` parses list entries throughout
[`books/free-programming-books-cs.md`](../../books/free-programming-books-cs.md),
preserving each title, URL, category, trailing metadata, and original line.
It groups exact URL duplicates and separately reports conservative
normalization matches.

Normalization lowercases the scheme and hostname, removes an HTTP/HTTPS default
port, and treats an empty root path as `/`. It does **not** change schemes,
path case, path escapes, query strings (including parameter order), or
fragments. Thus query-dependent resources and distinct fragment anchors remain
separate.

Selected entries:

| Line | Category | Display name | URL |
| ---: | --- | --- | --- |
| 32 | Bash | Bash očima Bohdana Milara | `http://i.iinfo.cz/files/root/k/bash_ocima_bohdana_milara.pdf` |
| 37 | C# | Systémové programování v jazyce C# | `https://phoenix.inf.upol.cz/esf/ucebni/sysprog.pdf` |
| 42 | C++ | Moderní programování objektových aplikací v C++ | `https://akela.mendelu.cz/~xvencal2/CPP/opora.pdf` |

The source analysis finds `https://knihy.nic.cz` repeated on lines 72, 73, and
85 for differently titled books. This is reported as a shared-URL candidate,
not proof that the resources are duplicates; no deletion is proposed. No
distinct-URL normalization group was found in the current file.

Run the offline fixture and source checks:

```sh
python3 tools/course_checks/r10-t023.py --self-test
```

Fixtures cover exact duplicates, conservative host/default-port and empty-root
normalization, fenced fake links, meaningful fragments, query values, query
parameter order, and scheme differences. The checker only reports candidate
pairs for manual review; it never proposes or performs a deletion. Inputs,
expected/actual results, and tool versions are saved in `work/R10-T023/`.
