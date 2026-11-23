# R10-T009: Access Requirements Verification for free-courses-he.md

**Student:** Anshuman Holkar  
**Task ID:** R10-T009  
**Repository:** https://github.com/S-AI-Projects/free-programming-books  
**Branch:** `student/e26b07f0734/R10-T009`  
**Target File:** `courses/free-courses-he.md`  

---

## 1. Objective
Verify whether selected resources in `courses/free-courses-he.md` require authentication, registration, payment, or special execution environments. Make catalogue descriptions precise, cite official sources, ensure zero credentials are saved, and label unavailable resources as `UNVERIFIED` without asserting an unverified access model.

## 2. Selected Entries and Access Requirements

| Line | Title | URL | Platform | Observed Status | Access Model | Official Source Citation | Proposed Catalogue Wording |
|---|---|---|---|---|---|---|---|
| 12 | מבוא לתכנות בשפת C++ | `https://campus.gov.il/course/course-v1-basmach-pc264/` | Campus IL & Basmach | `UNVERIFIED` | *(unverified)* | `https://campus.gov.il/course/course-v1-basmach-pc264/` | `* [מבוא לתכנות בשפת C++&lrm;](https://campus.gov.il/course/course-v1-basmach-pc264/) (קמפוסIL&lrm; ובסמ״ח) *(סטטוס לא מאומת)*` |
| 17 | Next.py – הצעד הבא שלך בפייתון | `https://campus.gov.il/course/course-v1-cs-gov-cs-nextpy102/` | Campus IL & Cyber Education Center | `UNVERIFIED` | *(unverified)* | `https://campus.gov.il/course/course-v1-cs-gov-cs-nextpy102/` | `* [Next.py –&lrm; הצעד הבא שלך בפייתון](https://campus.gov.il/course/course-v1-cs-gov-cs-nextpy102/) (קמפוסIL&lrm; והמרכז לחינוך סייבר) *(סטטוס לא מאומת)*` |
| 18 | network.py לתכנת במרחב הרשת | `https://campus.gov.il/course/cs-gov-cs-networkpy103-2020-1/` | Campus IL & Cyber Education Center | `UNVERIFIED` | *(unverified)* | `https://campus.gov.il/course/cs-gov-cs-networkpy103-2020-1/` | `* [network.py&lrm; לתכנת במרחב הרשת](https://campus.gov.il/course/cs-gov-cs-networkpy103-2020-1/) (קמפוסIL&lrm; והמרכז לחינוך סייבר) *(סטטוס לא מאומת)*` |

## 3. Platform & Access Model Analysis
- **Provider:** Campus IL is the Israeli government's national digital learning platform based on Open edX.
- **Availability Policy:** In automated requests, the historical course run endpoints returned 404 (past cohort run IDs). Following task policy, unavailable resources are labelled `UNVERIFIED` rather than assuming they are free or permanently broken.
- **Access Model Precision:** An unverified resource cannot have a verified access model asserted; hence `access_requirement` is set to `null` and designated `UNVERIFIED`.
- **Proposed Catalogue Annotation:** We propose annotating these entries with `*(סטטוס לא מאומת)*` (Status Unverified) to alert learners while keeping the entries in the catalogue for manual review.
- **Security:** Zero user credentials, tokens, or session secrets are recorded.

## 4. Verification and Self-Test

```bash
# Run self-test suite (exits 0 on success, non-zero on failure)
python3 tools/course_checks/r10-t009.py --self-test

# Run with Python -O optimization (must still exit 0 on success)
python3 -O tools/course_checks/r10-t009.py --self-test

# Run access requirement audit on target catalogue
python3 tools/course_checks/r10-t009.py
```

## 5. Catalogue Status
All selected entries are preserved. Per task guidelines, no links are removed without confirmed manual review.
