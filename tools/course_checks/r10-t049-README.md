# R10-T049 access requirements verification

Run `python3 tools/course_checks/r10-t049.py` to parse and verify the access requirements for the selected Kannada free course entries from `courses/free-courses-kn.md`.

The check inspects these three assigned entries:

| Title | URL | Category | Source line | Metadata |
| --- | --- | --- | ---: | --- |
| C programming in Kannada | [Link](https://youtube.com/playlist?list=PLUZkVL-W-8GLVwteCNH_HNoIAhbfBHnLb) | C | 12 | - script kiddie |
| Complete C Language Course in KANNADA | [Link](https://youtube.com/playlist?list=PLjvPj4x59YBUYkNJr4kCKOXsP3NyM4-ik) | C | 13 | - The Coding Class: Yuvaraj Madha |
| CSS in Kannada (ಕನ್ನಡದಲ್ಲಿ) - Beginner to Advanced. | [Link](https://youtube.com/playlist?list=PLBGSzVCM24iHnpfOMnhuyiyEo_NGSxdPD) | HTML and CSS | 18 | - DEBUG CODING |

## Running the check

```bash
# Display JSON classifications for the selected entries
python3 tools/course_checks/r10-t049.py

# Run offline fixture unit tests
python3 tools/course_checks/r10-t049.py --self-test
```

## Access Requirements Policy

1. **Source Citing**: Every access claim must cite the official playlist/resource URL.
2. **Credential Safety**: No passwords, personal tokens, or login credentials are saved or required.
3. **Conservative Verification**: An unavailable resource or an automated error without manual page confirmation is marked `unverified` rather than assumed free, paywalled, or broken.
4. **No Automated Removal**: Catalogue links are never removed solely because an automated check failed or timed out.
5. **Offline Fixtures**: Scenarios in `work/R10-T049/fixtures/access_scenarios.json` test public courses, login walls, registration walls, and automated HTTP failures.

Run evidence and logs are recorded in `work/R10-T049/`.
