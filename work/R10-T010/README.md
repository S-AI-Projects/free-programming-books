# R10-T010: Repeatable Maintenance Pass for free-programming-books-el.md Entries

**Student:** Anshuman Holkar  
**Task ID:** R10-T010  
**Repository:** https://github.com/S-AI-Projects/free-programming-books  
**Branch:** `student/e26b07f0734/R10-T010`  
**Target File:** `books/free-programming-books-el.md`  

---

## 1. Objective
Establish a documented, repeatable maintenance pass for entries in `books/free-programming-books-el.md`. The workflow generates a scoped maintenance report, cleanly separates observed facts (HTTP status code, MIME type, accessibility, publisher, observation provenance) from editorial recommendations and decisions, preserves line-mapping accuracy back to the catalogue, and guarantees deterministic execution across repeated runs.

## 2. Maintenance Pass Methodology

The repeatable maintenance process follows a strict 4-phase pipeline:
1. **Scope Selection & Parsing:**
   - Parse markdown headings and list item links with exact 1-based line tracking.
   - Filter to audit target entries within the scope of Greek language programming resources (`books/free-programming-books-el.md`).
2. **Fact Collection & Separation:**
   - Record verifiable technical evidence independently: HTTP response codes, response headers, content types, publisher, and observation provenance.
   - For Kallipos repository links, manual browser observations (interactive session navigating past Kallipos Cloudflare anti-bot challenge barrier) are explicitly labeled with `observed_by: "manual_browser"` and observation date `2026-11-23`.
   - Never invent default facts: if facts are missing for a resource, `observed_facts` is recorded as `null` and designated `UNOBSERVED`.
3. **Editorial Review (Recommendations & Decision Provenance):**
   - Formulate maintenance decisions (`KEEP`, `UPDATE`, `DEPRECATE`) based on policy.
   - Explicitly record decision provenance: `decided_by: "Anshuman Holkar"`, `decision_date: "2026-11-23"`, and before/after metadata snapshots.
   - If recommendations are missing, no decision is invented (`null`).
   - Per project guidelines, an automated check failure alone is never sufficient to delete a link. Manual inspection and evidence are mandatory.
4. **Deterministic Report Generation:**
   - Emit sorted, reproducible JSON reports guaranteed to produce stable output matching committed fixtures and `expected_selected.json`.

## 3. Selected Entries and Audit Results

| Line | Section | Title | URL | Observed Facts | Decision Provenance | Rationale |
|---|---|---|---|---|---|---|
| 19 | C | Διαδικαστικός προγραμματισμός | `https://repository.kallipos.gr/bitstream/11419/1346/3/00_master%20document_KOY.pdf` | HTTP 200, PDF, Active (manual_browser 2026-11-23) | `KEEP` by Anshuman Holkar | Official Kallipos bitstream repository PDF verified accessible. |
| 20 | C | Μια σύγχρονη προσέγγιση στη γλώσσα C | `https://repository.kallipos.gr/handle/11419/11683` | HTTP 200, HTML landing page, Active (manual_browser 2026-11-23) | `KEEP` by Anshuman Holkar | Kallipos handle persistent landing page with book chapters and metadata. |
| 25 | C# | Επίλυση προβλημάτων με τη γλώσσα C# | `https://repository.kallipos.gr/handle/11419/9349` | HTTP 200, HTML landing page, Active (manual_browser 2026-11-23) | `KEEP` by Anshuman Holkar | Persistent Kallipos handle landing page containing full textbook. |

## 4. Verification and Self-Test Suite

The implementation provides an automated, self-contained verification tool (`tools/course_checks/r10-t010.py`):

```bash
# 1. Run self-test suite (offline fixture tests, exits 0 on pass)
python3 tools/course_checks/r10-t010.py --self-test

# 2. Run with Python -O optimization
python3 -O tools/course_checks/r10-t010.py --self-test

# 3. Run maintenance pass against books/free-programming-books-el.md
python3 tools/course_checks/r10-t010.py
```

### Self-Test Assertions:
1. **Assertion 1 (Separation of Concerns):** Verifies report structure maintains clear separation between `observed_facts` and `recommendations`, verifying manual browser observation provenance and decision provenance.
2. **Assertion 2 (Missing Facts Edge Probe):** Asserts that when facts and decisions are missing, the report produces `null` / `UNOBSERVED` without inventing default status 200 or KEEP decisions.
3. **Assertion 3 (Field-by-Field Verification):** Compares all selected entries field-by-field against `expected_selected.json`.
4. **Assertion 4 (Determinism & Stability):** Verifies output stability against committed `results.json`.
5. **Assertion 5 (Line Precision):** Asserts exact source line mapping to target file lines 19, 20, and 25.

## 5. Catalogue Status
All selected entries are verified, conformant, and retained in `books/free-programming-books-el.md`. No links are deleted.
