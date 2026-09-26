"""Prompt template for triple extraction, tuned for a local 8B instruction model."""

RELATION_TYPES = [
    "ACQUIRED",
    "MERGED_WITH",
    "INVESTED_IN",
    "APPOINTED_AS",
    "RESIGNED_FROM",
    "PARTNERED_WITH",
]

SYSTEM_PROMPT = """You are an information extraction system for finance text.
Extract factual relationships as JSON triples. Follow these rules exactly:

1. Only use these relation types: {relation_types}
2. Only extract relationships explicitly stated in the text - do not infer or guess.
3. subject_type and object_type must be exactly "Company" or "Person".
4. Use full, canonical entity names as they appear in the text (e.g. "Microsoft Corporation", not "the company").
5. Direction matters: for APPOINTED_AS and RESIGNED_FROM, the subject is always the Person and the object is always the Company (e.g. "Jane Smith APPOINTED_AS Acme Corp", never the reverse). For ACQUIRED, MERGED_WITH, INVESTED_IN, PARTNERED_WITH, subject and object are both companies.
6. Output ONLY valid JSON matching this exact shape, nothing else - no explanation, no markdown fences:
{{"triples": [{{"subject": "...", "subject_type": "Company", "relation": "ACQUIRED", "object": "...", "object_type": "Company"}}]}}
7. If no relevant relationships are found, output {{"triples": []}}
""".format(relation_types=", ".join(RELATION_TYPES))

FEW_SHOT_EXAMPLES = [
    {
        "text": "Acme Corp announced today that it has completed its acquisition of Beta Industries for $2.1 billion.",
        "output": {
            "triples": [
                {
                    "subject": "Acme Corp",
                    "subject_type": "Company",
                    "relation": "ACQUIRED",
                    "object": "Beta Industries",
                    "object_type": "Company",
                }
            ]
        },
    },
    {
        "text": "The board of Widget Inc. appointed Jane Smith as Chief Executive Officer, effective immediately. Former CEO John Doe resigned from Widget Inc.",
        "output": {
            "triples": [
                {
                    "subject": "Jane Smith",
                    "subject_type": "Person",
                    "relation": "APPOINTED_AS",
                    "object": "Widget Inc.",
                    "object_type": "Company",
                },
                {
                    "subject": "John Doe",
                    "subject_type": "Person",
                    "relation": "RESIGNED_FROM",
                    "object": "Widget Inc.",
                    "object_type": "Company",
                },
            ]
        },
    },
]


def build_user_prompt(text: str) -> str:
    import json

    examples_block = "\n\n".join(
        f"Text: {ex['text']}\nOutput: {json.dumps(ex['output'])}" for ex in FEW_SHOT_EXAMPLES
    )
    return f"""Examples:

{examples_block}

Now extract triples from this text:

Text: {text}
Output:"""
