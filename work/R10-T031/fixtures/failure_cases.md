### Section with Fenced Code Block

This link is inside a code fence and must be ignored:

```
* [FakeBook](https://example.com/fake-should-be-ignored)
```

This link is real and should be parsed:

* [RealBook](https://example.com/real)


### Malformed Entries (should all be ignored)

* [Missing closing bracket(https://example.com/bad1)
* [No URL at all]
* just a plain text line
* [Title with no URL](
