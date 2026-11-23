# R10-T009: Access Requirements Verification for free-courses-he.md

**Student:** Anshuman Holkar  
**Task ID:** R10-T009  
**Repository:** https://github.com/S-AI-Projects/free-programming-books  
**Branch:** `student/e26b07f0734/R10-T009`  
**Target File:** `courses/free-courses-he.md`  

---

## 1. Objective
Verify whether selected resources in `courses/free-courses-he.md` require authentication, registration, payment, or special execution environments. Make the catalogue descriptions precise, cite official sources, ensure zero credentials are saved, and label unavailable resources as `UNVERIFIED` rather than "free" or "broken".

## 2. Selected Entries and Access Requirements

| Line | Title | URL | Platform | Access Model | Status Label | Official Source Citation |
|---|---|---|---|---|---|---|
| 12 | מבוא לתכנות בשפת C++ | `https://campus.gov.il/course/course-v1-basmach-pc264/` | Campus IL & Basmach | `FREE_WITH_REGISTRATION` | `UNVERIFIED` | `https://campus.gov.il/about/` |
| 17 | Next.py – הצעד הבא שלך בפייתון | `https://campus.gov.il/course/course-v1-cs-gov-cs-nextpy102/` | Campus IL & Cyber Education Center | `FREE_WITH_REGISTRATION` | `UNVERIFIED` | `https://campus.gov.il/about/` |
| 18 | network.py לתכנת במרחב הרשת | `https://campus.gov.il/course/cs-gov-cs-networkpy103-2020-1/` | Campus IL & Cyber Education Center | `FREE_WITH_REGISTRATION` | `UNVERIFIED` | `https://campus.gov.il/about/` |

## 3. Platform & Access Model Analysis
- **Provider:** Campus IL is the Israeli government's national digital learning platform based on Open edX.
- **Cost:** Free of charge as part of the National Digital Initiative.
- **Authentication/Registration:** Free account registration is mandatory to access video content, exercises, and forums.
- **Availability Policy:** While specific historical course run endpoints may be cycled/archived by Campus IL, project rules explicitly state that unavailable resources must be labelled `UNVERIFIED` rather than assuming they are broken or free.
- **Security:** Zero user credentials, tokens, or session secrets are recorded.

## 4. Verification and Self-Test

```bash
# Run self-test suite (exits 0 on success, non-zero on failure)
python3 tools/course_checks/r10-t009.py --self-test

# Run access requirement audit on target catalogue
python3 tools/course_checks/r10-t009.py
```

## 5. Catalogue Status
All selected entries are preserved. Per task guidelines, no links are removed.
