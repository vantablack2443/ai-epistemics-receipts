from typing import Literal
from pydantic import BaseModel, Field, model_validator

Category = Literal['tentative', 'scope', 'assumption', 'conditional', 'conflict']
Label = Literal['preserved', 'omitted', 'strengthened', 'weakened', 'contradicted']

class Item(BaseModel):
    id: str
    type: Literal['finding', 'qualification']
    quotation: str
    meaning: str
    paraphrases: list[str] = []

class Document(BaseModel):
    id: str
    split: Literal['development', 'test']
    category: Category
    text: str
    provenance: str
    items: list[Item] = Field(min_length=4, max_length=4)
    reviewed: bool = False

    @model_validator(mode='after')
    def validate_items(self):
        if sum(i.type == 'finding' for i in self.items) != 1:
            raise ValueError('exactly one finding required')
        if len({i.id for i in self.items}) != 4:
            raise ValueError('item IDs must be unique within document')
        if any(i.quotation not in self.text for i in self.items):
            raise ValueError('item quotations must appear in source')
        return self

class Annotation(BaseModel):
    generation_id: str
    item_id: str
    reviewer_id: str
    label: Label
    quotation: str = ''
    rationale: str = ''

    @model_validator(mode='after')
    def require_rationale(self):
        if self.label != 'preserved' and not self.rationale.strip():
            raise ValueError('non-preserved items require a rationale')
        return self


class ItemV2(BaseModel):
    id: str
    type: Literal['finding', 'qualification']
    quotation: str
    meaning: str

class DocumentV2(BaseModel):
    id: str
    split: Literal['development', 'test']
    kind: Literal['fictional', 'paper']
    text: str
    provenance: str
    licence: str
    items: list[ItemV2]
    reviewed: bool = False

    @model_validator(mode='after')
    def validate_v2(self):
        if not 6 <= len(self.items) <= 10:
            raise ValueError('6 to 10 items required')
        if sum(i.type == 'finding' for i in self.items) not in (1, 2):
            raise ValueError('1 or 2 findings required')
        if len({i.id for i in self.items}) != len(self.items):
            raise ValueError('item IDs must be unique within document')
        if any(not i.id.startswith(f'{self.id}-') for i in self.items):
            raise ValueError(f'item IDs must start with "{self.id}-"')
        for i in self.items:
            if self.text.count(i.quotation) != 1 or not i.quotation:
                raise ValueError(f'quotation of {i.id} must occur exactly once in the text')
        if not 900 <= len(self.text.split()) <= 1500:
            raise ValueError('text must be 900 to 1500 words')
        return self
