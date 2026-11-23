# R10-T008: List Formatting & Ordering Check for free-programming-interactive-tutorials-ru.md

**Student:** Anshuman Holkar  
**Task ID:** R10-T008  
**Repository:** https://github.com/S-AI-Projects/free-programming-books  
**Branch:** `student/e26b07f0734/R10-T008`  
**Target File:** `more/free-programming-interactive-tutorials-ru.md`  

---

## 1. Objective
Validate markdown bullet syntax, heading hierarchy, and alphabetical ordering rules in `more/free-programming-interactive-tutorials-ru.md` in accordance with repository contribution guidelines.

## 2. Selected Entries and Audit

| Line | Section | Title | URL | Status |
|---|---|---|---|---|
| 14 | Веб-разработка | Учитесь веб-разработке бесплатно! | `http://codenamecrud.ru` | VALID_MARKDOWN_SYNTAX |
| 15 | Веб-разработка | Open source воркшопы | `https://nodeschool.io/ru` | VALID_MARKDOWN_SYNTAX |
| 20 | Облачные вычисления | Microsoft Certified: Azure Fundamentals | `https://docs.microsoft.com/ru-ru/learn/certifications/azure-fundamentals/` | VALID_MARKDOWN_SYNTAX |

## 3. Formatting Rules Checked
- **Bullet syntax:** Valid list item starting with `* ` or `- `.
- **Link syntax:** Exact `[Title](URL)` format with no spaces between closing bracket `]` and opening paren `(`.
- **Author separator:** Valid ` - ` (dash surrounded by single spaces) before author name.
- **Section ordering:** Validates case-insensitive alphabetical ordering within common script blocks.
- **Index isolation:** Correctly ignores internal `#anchor` links within `### Index`.
- **International text:** Preserves Cyrillic and multilingual characters without corruption.

## 4. Verification and Self-Test

```bash
# Run self-test suite (exits 0 on success, non-zero on failure)
python3 tools/course_checks/r10-t008.py --self-test

# Run formatting audit on target catalogue
python3 tools/course_checks/r10-t008.py
```

## 5. Catalogue Status
All selected entries obey repository formatting and syntax guidelines. No catalogue modifications required.
