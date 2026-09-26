from src.graph.loader import normalize_name


def test_normalize_strips_inc_suffix():
    assert normalize_name("Acme Inc.") == "Acme"


def test_normalize_strips_corp_suffix():
    assert normalize_name("Beta Corp") == "Beta"


def test_normalize_strips_llc_suffix():
    assert normalize_name("Gamma Industries LLC") == "Gamma Industries"


def test_normalize_collapses_whitespace():
    assert normalize_name("  Acme   Corp  ") == "Acme"


def test_normalize_leaves_plain_names_alone():
    assert normalize_name("Microsoft") == "Microsoft"


def test_normalize_leaves_person_names_alone():
    assert normalize_name("Jane Smith") == "Jane Smith"


def test_normalize_falls_back_when_stripping_empties_name():
    # a pathological all-suffix input should not collapse to an empty string
    assert normalize_name("Inc.") == "Inc."
