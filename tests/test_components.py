from core.components import (LCSC_PATTERN, REQUIRED_KEYS, find_by_lcsc, find_part,
                             load_components, validate_part)


def test_every_part_has_all_fields():
    for mpn, part in load_components().items():
        missing = REQUIRED_KEYS - part.keys()
        assert not missing, f"{mpn} is missing {missing}"


def test_lcsc_numbers_look_right():
    # Either a real C-number, or null for generic families (resistors etc.)
    for mpn, part in load_components().items():
        assert part["lcsc"] is None or LCSC_PATTERN.match(part["lcsc"]), f"{mpn}: bad lcsc {part['lcsc']}"


def test_find_ignores_case():
    assert find_part("l7805cv") is not None


def test_find_by_lcsc():
    assert find_by_lcsc("C111887")["mpn"] == "L7805CV"


def test_unknown_part_is_flagged():
    problems = validate_part("FAKE-PART-123")
    assert problems and "not in our component list" in problems[0]


def test_voltage_above_rating_is_flagged():
    assert validate_part("L7805CV", voltage_v=40) != []


def test_within_rating_is_ok():
    assert validate_part("L7805CV", voltage_v=12, current_a=1.0) == []


def test_catalog_todo():
    # Completeness is tracked with:  python -m core.catalog_todo
    from core.catalog_todo import todo
    flagged = {line.split()[1] for line in todo()}
    assert "L7805CV" not in flagged            # complete entry: not on the to-do list
    assert "FAKE-PART" not in flagged
