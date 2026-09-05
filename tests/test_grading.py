"""Tests for the grading engine — pure logic, no DB needed."""
import pytest

from app.engines.grading_engine import grade


def test_grade_a():
    """Perfect answers should yield Grade A."""
    answers = {
        "size_uniformity": "high",
        "color_uniformity": "high",
        "damage_percent": 2,
        "sprouting_percent": 1,
        "moisture_level": "dry",
        "foreign_matter": "none",
    }
    result = grade(answers)
    assert result["grade"] == "A"


def test_grade_b():
    """Medium-quality answers should yield Grade B."""
    answers = {
        "size_uniformity": "medium",
        "color_uniformity": "medium",
        "damage_percent": 10,
        "sprouting_percent": 5,
        "moisture_level": "normal",
        "foreign_matter": "low",
    }
    result = grade(answers)
    assert result["grade"] == "B"


def test_grade_c():
    """Poor answers should yield Grade C."""
    answers = {
        "size_uniformity": "low",
        "color_uniformity": "low",
        "damage_percent": 30,
        "sprouting_percent": 15,
        "moisture_level": "moist",
        "foreign_matter": "high",
    }
    result = grade(answers)
    assert result["grade"] == "C"


def test_improvement_tip_present():
    """Every grade result should have an improvement tip."""
    answers = {
        "size_uniformity": "medium",
        "color_uniformity": "high",
        "damage_percent": 20,
        "sprouting_percent": 1,
        "moisture_level": "normal",
        "foreign_matter": "none",
    }
    result = grade(answers)
    assert "improvement_tip" in result
    assert len(result["improvement_tip"]) > 0


def test_empty_answers():
    """Empty answers should still return a result (Grade C)."""
    result = grade({})
    assert result["grade"] in ("A", "B", "C")
    assert "improvement_tip" in result
