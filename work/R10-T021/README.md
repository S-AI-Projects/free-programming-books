# R10-T021 validation evidence

The checker reads only `casts/free-podcasts-screencasts-pt_BR.md` and selects
the three URLs assigned for this task. The source entries matched the supplied
names and URLs, so no catalogue edit was necessary.

## Offline inputs

- `success.md`: contains the selected resources, a fenced fake resource link,
  and a fragment-bearing resource URL.
- `failure.md`: omits the third selected resource to exercise validation failure.

The canonical fixture inputs and assertions are in
`tools/course_checks/fixtures/r10-t021/`.

## Results

- `expected.json`: expected extracted records from the current source, including
  original line numbers.
- `actual.json`: output from running the checker against the current source.
- `self-test-output.txt`: output from the offline `--self-test` run.
- `tool-versions.txt`: Python and platform versions used for the checks.
