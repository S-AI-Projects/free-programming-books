# R10-T029 Romanian course access check

Run `python3 tools/course_checks/r10-t029.py --self-test` for the offline
fixtures. The checker reads only the selected entries in
`courses/free-courses-ro.md`, preserves their source line numbers, and records
access requirements only when manually verified against the exact official
resource URL. It never saves credentials.

| Course | Official resource | Section | Source line |
| --- | --- | --- | ---: |
| Structuri de Date și Algoritmi | <https://lectii.utm.md/courses/structuri-de-date-si-algoritmi/> | Algoritmi și Structuri de Date | 11 |
| Programarea calculatoarelor | <https://lectii.utm.md/courses/programarea-calculatoarelor/> | C++ | 16 |
| Programarea Orientată pe Obiecte | <https://lectii.utm.md/courses/programarea-orientata-pe-obiecte/> | C++ | 17 |

Manual browser checks could not reach the course content: the first two pages
failed to load, and the third showed a Cloudflare security-verification
challenge. All three are therefore reported as **unverified**. Authentication,
registration, payment, and environment requirements remain unknown; these
observations do not establish that the courses are broken or free. No catalogue
change was made.

Synthetic offline fixtures cover public access, authentication/registration,
payment, environment requirements, missing evidence, and automated 403/404
responses.
An automated failure alone remains unverified and never recommends removal.
Inputs, expected-versus-actual results, report, and tool versions are stored in
`work/R10-T029/`.
