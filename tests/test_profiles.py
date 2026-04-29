"""Tests for profiles helpers."""
from insighta.profiles import ProfileData, profile_row


SAMPLE = {
    "id": "abc123",
    "name": "Ada Obi",
    "gender": "female",
    "gender_probability": 0.97,
    "age": 28,
    "age_group": "adult",
    "country_id": "NG",
    "country_name": "Nigeria",
    "country_probability": 0.88,
    "created_at": "2025-01-15T10:30:00+00:00",
}


def test_profile_data_from_dict():
    p = ProfileData.from_dict(SAMPLE)
    assert p.id == "abc123"
    assert p.name == "Ada Obi"
    assert p.gender == "female"
    assert p.gender_probability == 0.97
    assert p.age == 28
    assert p.age_group == "adult"
    assert p.country_id == "NG"
    assert p.country_name == "Nigeria"
    assert p.country_probability == 0.88


def test_profile_row_length():
    p = ProfileData.from_dict(SAMPLE)
    row = profile_row(p)
    assert len(row) == 9  # one entry per table column


def test_profile_row_gender_color_female():
    p = ProfileData.from_dict(SAMPLE)
    row = profile_row(p)
    assert "magenta" in row[2]


def test_profile_row_gender_color_male():
    male = {**SAMPLE, "gender": "male"}
    p = ProfileData.from_dict(male)
    row = profile_row(p)
    assert "blue" in row[2]


def test_profile_row_probability_format():
    p = ProfileData.from_dict(SAMPLE)
    row = profile_row(p)
    assert row[3] == "97.0%"
    assert row[7] == "88.0%"


def test_profile_row_country_combined():
    p = ProfileData.from_dict(SAMPLE)
    row = profile_row(p)
    assert row[6] == "Nigeria (NG)"
