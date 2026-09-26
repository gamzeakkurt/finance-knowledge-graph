import pytest
from pydantic import ValidationError

from src.extraction.schema import ExtractionResult, Triple


def test_valid_triple_parses():
    triple = Triple(
        subject="Acme Corp",
        subject_type="Company",
        relation="ACQUIRED",
        object="Beta Industries",
        object_type="Company",
    )
    assert triple.subject == "Acme Corp"
    assert triple.relation == "ACQUIRED"


def test_invalid_relation_rejected():
    with pytest.raises(ValidationError):
        Triple(
            subject="Acme Corp",
            subject_type="Company",
            relation="BOUGHT",  # not in fixed vocabulary
            object="Beta Industries",
            object_type="Company",
        )


def test_invalid_entity_type_rejected():
    with pytest.raises(ValidationError):
        Triple(
            subject="Acme Corp",
            subject_type="Organization",  # only Company/Person allowed
            relation="ACQUIRED",
            object="Beta Industries",
            object_type="Company",
        )


def test_empty_subject_rejected():
    with pytest.raises(ValidationError):
        Triple(
            subject="",
            subject_type="Company",
            relation="ACQUIRED",
            object="Beta Industries",
            object_type="Company",
        )


def test_whitespace_stripped():
    triple = Triple(
        subject="  Acme Corp  ",
        subject_type="Company",
        relation="ACQUIRED",
        object="Beta Industries",
        object_type="Company",
    )
    assert triple.subject == "Acme Corp"


def test_extraction_result_parses_malformed_llm_json_shape():
    raw = {
        "triples": [
            {
                "subject": "Jane Smith",
                "subject_type": "Person",
                "relation": "APPOINTED_AS",
                "object": "Widget Inc.",
                "object_type": "Company",
            }
        ]
    }
    result = ExtractionResult.model_validate(raw)
    assert len(result.triples) == 1


def test_extraction_result_defaults_to_empty():
    result = ExtractionResult.model_validate({"triples": []})
    assert result.triples == []


def test_reversed_appointment_direction_is_corrected():
    # local 8B models sometimes emit Company APPOINTED_AS Person instead of Person APPOINTED_AS Company
    triple = Triple(
        subject="3M Company",
        subject_type="Company",
        relation="APPOINTED_AS",
        object="Jennifer W. Rumsey",
        object_type="Person",
    )
    assert triple.subject == "Jennifer W. Rumsey"
    assert triple.subject_type == "Person"
    assert triple.object == "3M Company"
    assert triple.object_type == "Company"


def test_correct_appointment_direction_is_unchanged():
    triple = Triple(
        subject="Jane Smith",
        subject_type="Person",
        relation="APPOINTED_AS",
        object="Widget Inc.",
        object_type="Company",
    )
    assert triple.subject == "Jane Smith"
    assert triple.object == "Widget Inc."
