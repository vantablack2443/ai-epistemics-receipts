# Development verification gates

Following ECC eval-harness guidance, define checks before implementation. No gate below has yet passed.

- Chain isolation: rounds two and three receive only their immediate parent; no ground truth enters prompts.
- Invocation: every call explicitly selects Terra and low reasoning; event logs identify tool use and halt affected chains.
- Storage: attempts and completed outputs are immutable, failed attempts remain distinct, resume skips completed cells, and overlength text remains unchanged.
- Design: budgets match across conditions and include headings; development data cannot enter final aggregation.
- Analysis: hand-calculated examples agree; paired resamples retain document identity; missing outputs are not zeroes.
- Manual app review: missing rounds, long or overlength text, disagreement, and incomplete runs are represented without misleading totals.

Human review is required for semantic annotations, source quality, final report, authorship, and submission. Automated tests cannot substitute for these checks.
