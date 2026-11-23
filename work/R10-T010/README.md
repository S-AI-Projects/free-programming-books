# R10-T010: Repeatable Maintenance Pass for free-programming-books-el.md Entries

**Student:** Anshuman Holkar  
**Task ID:** R10-T010  
**Repository:** https://github.com/S-AI-Projects/free-programming-books  
**Branch:** `student/e26b07f0734/R10-T010`  
**Target File:** `books/free-programming-books-el.md`  

---

## 1. Objective
Establish a documented, repeatable maintenance pass for entries in `books/free-programming-books-el.md`. The workflow generates a scoped maintenance report, cleanly separates observed facts (HTTP status code, MIME type, accessibility, publisher) from subjective/editorial recommendations, preserves line-mapping accuracy back to the catalogue, and guarantees deterministic execution across repeated runs.

## 2. Maintenance Pass Methodology

The repeatable maintenance process follows a strict 4-phase pipeline:
1. **Scope Selection & Parsing:**
   - Parse markdown headings and list item links with exact 1-based line tracking.
   - Filter to audit target entries within the scope of Greek language programming resources (`books/free-programming-books-el.md`).
2. **Fact Collection (Separation of Facts):**
   - Record verifiable technical evidence independently: HTTP response codes, response headers, content types, and hosting repository status.
3. **Editorial Review (Recommendations & Decisions):**
   - Formulate maintenance decisions (`KEEP`, `UPDATE`, `DEPRECATE`) based on policy.
   - Per project guidelines, an automated check failure alone is never sufficient to delete a link. Manual inspection and evidence are mandatory.
4. **Deterministic Report Generation:**
   - Emit sorted, reproducible JSON/text reports guaranteed to produce identical hashes across multiple passes.

## 3. Selected Entries and Audit Results

| Line | Section | Title | URL | Observed Facts | Decision | Rationale |
|---|---|---|---|---|---|---|
| 19 | C | Διαδικαστικός προγραμματισμός | `https://repository.kallipos.gr/bitstream/11419/1346/3/00_master%20document_KOY.pdf` | HTTP 200, PDF, Active | `KEEP` | Official Kallipos bitstream repository PDF verified accessible. |
| 20 | C | Μια σύγχρονη προσέγγιση στη γλώσσα C | `https://repository.kallipos.gr/handle/11419/11683` | HTTP 200, HTML landing page, Active | `KEEP` | Kallipos handle persistent landing page with book chapters and metadata. |
| 25 | C# | Επίλυση προβλημάτων με τη γλώσσα C# | `https://repository.kallipos.gr/handle/11419/9349` | HTTP 200, HTML landing page, Active | `KEEP` | Persistent Kallipos handle landing page containing full textbook. |

## 4. Verification and Self-Test Suite

The implementation provides an automated, self-contained verification tool (`tools/course_checks/r10-t010.py`):

```bash
# 1. Run self-test suite (offline fixture tests, exits 0 on pass)
python3 tools/course_checks/r10-t010.py --self-test

# 2. Run maintenance pass against books/free-programming-books-el.md
python3 tools/course_checks/r10-t010.py
```

### Self-Test Assertions:
1. **Assertion 1 (Separation of Concerns):** Verifies report structure maintains clear separation between `observed_facts` and `recommendations`.
2. **Assertion 2 (Determinism & Stability):** Verifies SHA-256 output hash stability across multiple execution passes.
3. **Assertion 3 (Line Precision):** Asserts exact source line mapping to target file lines 19, 20, and 25.

## 5. Catalogue Status
All selected entries are verified, conformant, and retained in `books/free-programming-books-el.md`. No links are deleted.
