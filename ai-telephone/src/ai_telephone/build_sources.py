"""Apply an AI review to v2 draft documents and write the reviewed source set.

A document is included only if its review line says doc_verdict "accept" and
every one of its items is decided exactly once. Anything else is excluded with
a reason, or raises ValueError when the review input is incomplete or ambiguous.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError, model_validator

from ai_telephone.models import DocumentV2


class ReviewItem(BaseModel):
    item_id: str
    decision: Literal['approve', 'revise_meaning', 'reject']
    new_meaning: str | None = None
    note: str = ''

    @model_validator(mode='after')
    def require_new_meaning(self):
        if self.decision == 'revise_meaning' and not (self.new_meaning or '').strip():
            raise ValueError(f'{self.item_id}: revise_meaning requires a non-empty new_meaning')
        return self


class ReviewLine(BaseModel):
    document_id: str
    reviewer: str
    strength_ok: bool
    realistic: bool
    doc_verdict: Literal['accept', 'redraft']
    doc_note: str = ''
    items: list[ReviewItem]


def _lines(path: Path):
    for lineno, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if line.strip():
            yield lineno, line


def _load_drafts(paths: list[Path]) -> tuple[dict[str, DocumentV2], list[str]]:
    docs: dict[str, DocumentV2] = {}
    missing: list[str] = []
    for path in paths:
        path = Path(path)
        if not path.exists():
            missing.append(str(path))
            continue
        for lineno, line in _lines(path):
            try:
                doc = DocumentV2.model_validate_json(line)
            except ValidationError as exc:
                raise ValueError(f'{path}:{lineno}: not a valid DocumentV2: {exc}') from exc
            if doc.id in docs:
                raise ValueError(f'duplicate document id {doc.id!r} (second occurrence at {path}:{lineno})')
            docs[doc.id] = doc
    return docs, missing


def _load_reviews(path: Path) -> dict[str, ReviewLine]:
    reviews: dict[str, ReviewLine] = {}
    for lineno, line in _lines(Path(path)):
        try:
            review = ReviewLine.model_validate_json(line)
        except ValidationError as exc:
            raise ValueError(f'{path}:{lineno}: invalid review line: {exc}') from exc
        if review.document_id in reviews:
            raise ValueError(f'multiple review lines for document {review.document_id!r} ({path}:{lineno})')
        reviews[review.document_id] = review
    return reviews


def _check_coverage(doc: DocumentV2, review: ReviewLine) -> None:
    doc_ids = [item.id for item in doc.items]
    counts = Counter(ri.item_id for ri in review.items)
    missing = [i for i in doc_ids if counts[i] == 0]
    duplicated = [i for i in doc_ids if counts[i] > 1]
    unknown = sorted(i for i in counts if i not in set(doc_ids))
    if missing or duplicated or unknown:
        raise ValueError(
            f'document {doc.id!r}: review items do not match the document '
            f'(missing={missing}, duplicated={duplicated}, unknown={unknown})'
        )


def _validation_reason(exc: ValidationError) -> str:
    msgs = [str(err['msg']).removeprefix('Value error, ') for err in exc.errors()]
    return 'fails validation after review: ' + '; '.join(msgs)


def _apply(doc: DocumentV2, review: ReviewLine, reviewer_label: str) -> DocumentV2:
    decisions = {ri.item_id: ri for ri in review.items}
    kept = []
    for item in doc.items:
        ri = decisions[item.id]
        if ri.decision == 'reject':
            continue
        meaning = ri.new_meaning if ri.decision == 'revise_meaning' else item.meaning
        kept.append({'id': item.id, 'type': item.type, 'quotation': item.quotation, 'meaning': meaning})
    data = doc.model_dump()
    data['items'] = kept
    data['reviewed'] = True
    data['provenance'] = f'{doc.provenance}; reviewed by {reviewer_label}; not reviewed by a human'
    return DocumentV2.model_validate(data)


def build(drafts: list[Path], reviews: Path, out: Path, reviewer_label: str,
          overwrite: bool = False) -> dict:
    out = Path(out)
    if out.exists() and not overwrite:
        raise FileExistsError(f'{out} already exists; pass overwrite=True to replace it')

    docs, missing = _load_drafts([Path(p) for p in drafts])
    review_map = _load_reviews(Path(reviews))

    included: list[DocumentV2] = []
    excluded: list[dict[str, str]] = []
    counts = {'approved': 0, 'revised': 0, 'rejected': 0}

    ordered = sorted(docs.values(), key=lambda d: (d.split != 'development', d.id))
    for doc in ordered:
        review = review_map.get(doc.id)
        if review is None:
            raise ValueError(f'no review line for document {doc.id!r}')
        _check_coverage(doc, review)

        if review.doc_verdict != 'accept':
            reason = f'doc_verdict is {review.doc_verdict}'
            if review.doc_note:
                reason += f': {review.doc_note}'
            excluded.append({'id': doc.id, 'reason': reason})
            continue

        try:
            reviewed = _apply(doc, review, reviewer_label)
        except ValidationError as exc:
            excluded.append({'id': doc.id, 'reason': _validation_reason(exc)})
            continue

        included.append(reviewed)
        for ri in review.items:
            if ri.decision == 'approve':
                counts['approved'] += 1
            elif ri.decision == 'revise_meaning':
                counts['revised'] += 1
            else:
                counts['rejected'] += 1

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', encoding='utf-8') as fh:
        for doc in included:
            fh.write(json.dumps(doc.model_dump(mode='json'), ensure_ascii=False) + '\n')

    return {
        'included': [d.id for d in included],
        'excluded': excluded,
        'items': counts,
        'items_scope': 'included documents only',
        'missing_drafts': missing,
        'unmatched_reviews': sorted(set(review_map) - set(docs)),
        'out': str(out),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Build reviewed v2 sources from drafts and an AI review.')
    parser.add_argument('--drafts', type=Path, nargs='+', required=True)
    parser.add_argument('--reviews', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reviewer-label', required=True)
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args(argv)
    try:
        report = build(args.drafts, args.reviews, args.out, args.reviewer_label, overwrite=args.overwrite)
    except (ValueError, FileExistsError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
