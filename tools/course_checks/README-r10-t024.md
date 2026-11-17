# R10-T024 category checker

`r10-t024.py` checks the selected entries and repeated category headings in
[`casts/free-podcasts-screencasts-fr.md`](../../casts/free-podcasts-screencasts-fr.md).
It uses an explicit, source-reviewed expected-category map rather than
reclassifying entries from title keywords. Findings include source line,
recommended category, subject rationale, and the resource page used as
evidence; suggested moves require manual review.

Selected entries after the evidence-backed correction:

| Line | Category | Display name | URL |
| ---: | --- | --- | --- |
| 9 | Cloud computing | Le podcast AWS en français | `https://aws.amazon.com/fr/blogs/france/podcasts` |
| 20 | Langage Agnostique | Les Cast Codeurs Podcast | `https://lescastcodeurs.com` |
| 14 | Langage Agnostique | Artisan Developpeur | `https://artisandeveloppeur.fr/podcast` |

Subject review performed on 2026-11-17:

- The [AWS podcast page](https://aws.amazon.com/fr/blogs/france/podcasts) is
  hosted by AWS and its episode archive includes AWS Lambda/Fargate, cloud
  migration, and public-cloud topics; **Cloud computing** remains appropriate.
- The [Cast Codeurs homepage](https://lescastcodeurs.com) covers Java/JDK as
  well as Rust, TypeScript, PHP, data, infrastructure, and other software
  topics. This supports moving it from **Java** to **Langage Agnostique**.
- The [Artisan Developpeur podcast page](https://artisandeveloppeur.fr/podcast)
  describes the software-development profession and community news; **Langage
  Agnostique** remains appropriate.

Run the offline checker and its success/failure fixtures:

```sh
python3 tools/course_checks/r10-t024.py --self-test
```

The test verifies valid placements, catches a deliberately misplaced entry and
a repeated heading, and checks for a non-zero CLI result on the failing fixture.
It saves inputs, expected/actual results, subject evidence, and tool versions in
`work/R10-T024/results.json`. The checker never removes a link.
