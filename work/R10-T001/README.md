# R10-T001: Structured Parser for free-podcasts-screencasts-es.md

**Student:** Anshuman Holkar  
**Task ID:** R10-T001  
**Repository:** https://github.com/S-AI-Projects/free-programming-books  
**Branch:** `student/e26b07f0734/R10-T001`  
**Target File:** `casts/free-podcasts-screencasts-es.md`  

---

## 1. Objective
Extract display name, URL, category, author, and available format metadata from selected entries in `casts/free-podcasts-screencasts-es.md` while preserving original 1-based line numbers.

## 2. Selected Entries

| Line | Title | Category | URL | Author / Format |
|---|---|---|---|---|
| 15 | Conceptos fundamentales: Bases de datos relacionales | Bases de Datos | `https://www.youtube.com/playlist?list=PLzSFZWTjelbJ01UciHPAWTqUFWesoGr9A` | Programación y más (screencast) |
| 20 | BigDateame | Ciencia de Datos | `https://open.spotify.com/show/0aikWOJmQMglEmbmbHqv4q` | Iker Gómez García (podcast) |
| 21 | DataFuturologyEspanol | Ciencia de Datos | `https://podcasts.apple.com/es/podcast/data-futurology-espa%C3%B1ol/id1523527265` | Felipe Flores (podcast) |

## 3. Implementation Details
The parser is implemented in `tools/course_checks/r10-t001.py` using Python 3 standard library:
- **Heading tracking:** Identifies section categories and maps entries to their parent category.
- **Fenced code block handling:** Ignores any markdown links within ````...```` blocks.
- **Fragment preservation:** Fully retains URL anchor fragments (e.g., `#episode12`).
- **Line retention:** Reports exact 1-based line number for each parsed item.
- **Self-test mode (`--self-test`):** Validates all edge cases with assertions that exit non-zero on failure.

## 4. Verification and Self-Test

```bash
# Run the self-test suite (exits 0 on success, non-zero on failure)
python3 tools/course_checks/r10-t001.py --self-test

# Run standard parser output
python3 tools/course_checks/r10-t001.py
```

## 5. Catalogue Status
No catalogue edits were required: all three selected entries are correctly formatted according to repository guidelines and accessible at their original URLs.
