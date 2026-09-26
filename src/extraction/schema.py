"""Pydantic models used to validate LLM extraction output."""

from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class EntityType(str, Enum):
    COMPANY = "Company"
    PERSON = "Person"


class RelationType(str, Enum):
    ACQUIRED = "ACQUIRED"
    MERGED_WITH = "MERGED_WITH"
    INVESTED_IN = "INVESTED_IN"
    APPOINTED_AS = "APPOINTED_AS"
    RESIGNED_FROM = "RESIGNED_FROM"
    PARTNERED_WITH = "PARTNERED_WITH"


# For these relations the subject must be a Person and the object a Company.
# Local 8B models sometimes emit the reverse despite prompt instructions -
# detect and correct that here rather than dropping otherwise-valid triples.
PERSON_SUBJECT_RELATIONS = {RelationType.APPOINTED_AS, RelationType.RESIGNED_FROM}


class Triple(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    subject_type: EntityType
    relation: RelationType
    object: str = Field(min_length=1, max_length=200)
    object_type: EntityType

    @field_validator("subject", "object")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def fix_person_relation_direction(self) -> "Triple":
        if (
            self.relation in PERSON_SUBJECT_RELATIONS
            and self.subject_type == EntityType.COMPANY
            and self.object_type == EntityType.PERSON
        ):
            self.subject, self.object = self.object, self.subject
            self.subject_type, self.object_type = self.object_type, self.subject_type
        return self


class ExtractionResult(BaseModel):
    triples: list[Triple] = Field(default_factory=list)
