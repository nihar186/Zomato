from src.ingestion.validator import validate_rows


def test_validate_accepts_complete_row(sample_normalized):
    valid, stats = validate_rows([sample_normalized])
    assert len(valid) == 1
    assert stats.valid_count == 1
    assert stats.dropped_count == 0


def test_validate_drops_missing_name(sample_normalized):
    row = dict(sample_normalized)
    row["name"] = ""
    valid, stats = validate_rows([row])
    assert valid == []
    assert stats.dropped_missing_name == 1


def test_validate_drops_missing_rating(sample_normalized):
    row = dict(sample_normalized)
    row["rating"] = None
    valid, stats = validate_rows([row])
    assert valid == []
    assert stats.dropped_missing_rating == 1
