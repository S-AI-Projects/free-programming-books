# R10-T050 repeatable maintenance pass verification

Run `python3 tools/course_checks/r10-t050.py` to execute a scoped, reproducible maintenance pass for the selected Norwegian free programming book entries from `books/free-programming-books-no.md`.

The check targets these three assigned entries:

| Title | URL | Category | Source line | Author | Format |
| --- | --- | --- | ---: | --- | --- |
| LaTeX for nybegynnere | [Link](https://www.mn.uio.no/ifi/tjenester/it/hjelp/latex/latex-for-nybegynnere.pdf) | Latex | 8 | Dag Langmyhr | PDF |
| LaTeX for viderekomne | [Link](https://www.mn.uio.no/ifi/tjenester/it/hjelp/latex/latex-videre.pdf) | Latex | 9 | Dag Langmyhr | PDF |
| Lokal guide til farger i LaTeX | [Link](https://www.mn.uio.no/ifi/tjenester/it/hjelp/latex/farger.pdf) | Latex | 10 | Dag Langmyhr | PDF |

## Running the check

```bash
# Output scoped maintenance report JSON separating facts from recommendations
python3 tools/course_checks/r10-t050.py

# Run offline fixture unit tests
python3 tools/course_checks/r10-t050.py --self-test
```

## Maintenance Policies & Invariants

1. **Separation of Facts and Recommendations**: Each entry report clearly separates observable facts (HTTP response, content length, verified format, author) from editorial recommendations (retain, update metadata, investigate, or propose removal).
2. **Line Number Preservation**: Exact source line numbers (8, 9, 10) are tracked and reported.
3. **Conservative Removal Policy**: A link is never proposed for removal based solely on a single automated crawl or network error; transient errors require manual review.
4. **Reproducible Offline Fixtures**: Scenarios in `work/R10-T050/fixtures/maintenance_scenarios.json` test valid entries, metadata drift, transient failures, and confirmed 404 deletions without network access.

Run evidence and generated artifacts are stored in `work/R10-T050/`.
