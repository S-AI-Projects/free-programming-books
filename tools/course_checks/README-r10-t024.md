# R10-T024 French podcast category checker

Run `python3 tools/course_checks/r10-t024.py` to print the three selected French
podcast records with their source line and category.

| Display name | URL | Category | Source line |
| --- | --- | --- | ---: |
| Le podcast AWS en français | [Podcast](https://aws.amazon.com/fr/blogs/france/podcasts) | Cloud computing | 9 |
| Les Cast Codeurs Podcast | [Podcast](https://lescastcodeurs.com) | Langage Agnostique | 20 |
| Artisan Developpeur | [Podcast](https://artisandeveloppeur.fr/podcast) | Langage Agnostique | 14 |

The `Les Cast Codeurs Podcast` entry was moved from Java to Langage Agnostique.
Subject evidence was checked on 2026-11-18 on its [homepage](https://lescastcodeurs.com):
the podcast covers Java/JDK and Rust, TypeScript, PHP, data/AI, infrastructure,
web, security, and tooling. This is broad general-development subject evidence,
not a Java-only classification.

The other two entries remain in their existing categories: AWS under Cloud
computing and Artisan Developpeur under Langage Agnostique.

Run `python3 tools/course_checks/r10-t024.py --self-test` for valid-category,
deliberately misplaced-category, repeated-heading, missing-entry, and
failing-assertion fixtures. Failed assertions exit non-zero.

No resource is removed solely because of an automated request. Generated evidence
is written to `work/R10-T024/`; the checker uses only the Python standard library.
