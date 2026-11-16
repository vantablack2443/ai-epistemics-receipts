# AI Telephone submission package

The report follows the official template section structure, adapted to a compact single-column PDF. It contains four body pages plus references and appendices. Review author details and scientific claims before submission. The project has not been submitted.

Files: report.pdf, editable report.md, abstract.txt, six-page slides.pdf, video-script.md, submission-fields.md, and research-artifacts.zip. Video recording remains deferred.

## Reproduce

From ai-telephone, install the locked Python 3.11 environment with uv sync. Run uv run pytest, then the analyze_cli and figures commands in Appendix B and uv run python report/audit_submission.py. Run report/build_submission.py with the bundled document Python runtime, which supplies reportlab and Pillow. No report-building command makes model calls. For tests on this Windows sandbox, point TEMP and TMP to a writable workspace directory.

The audit JSON records coverage and frozen-file checks. Windows checkout CRLF differs from manifest LF bytes; seven files match after normalization. annotate.py has the documented post-freeze quotation-validator amendment. Human annotation audit is absent. Test fixtures and runtime SQLite databases are excluded from the artifact archive.

## Sources verified on 16 November 2026

Organizer requirements: https://apartresearch.com/sprints/ai-x-epistemics-research-sprint-2026-11-13-to-2026-11-15

Official template text: https://docs.google.com/document/d/17b3JWki-ZkaqdmqGI5d0gof-HwlGuWU9Mc1_klNZXKs/edit

References: https://aclanthology.org/2020.acl-main.173/ and https://aclanthology.org/2023.emnlp-main.741/
