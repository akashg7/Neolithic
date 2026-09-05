"""
Grading Engine — Deterministic self-assay grading.
Farmer answers 6 questions → rule engine maps to Grade A/B/C + improvement tip.
No ML, no external dependencies. Offline-capable.
"""

GRADE_RULES = {
    # Each answer maps to a numeric score (higher = better)
    "size_uniformity":  {"high": 3, "medium": 2, "low": 1},
    "color_uniformity": {"high": 3, "medium": 2, "low": 1},
    "damage_percent":   lambda v: 3 if v < 5 else (2 if v < 15 else 1),
    "sprouting_percent": lambda v: 3 if v < 3 else (2 if v < 10 else 1),
    "moisture_level":   {"dry": 3, "normal": 2, "moist": 1},
    "foreign_matter":   {"none": 3, "low": 2, "moderate": 1, "high": 0},
}

IMPROVEMENT_TIPS = {
    "damage_percent": "Careful handling during harvest reduces damage. Consider sorting out damaged produce before listing.",
    "sprouting_percent": "Store in cool, dark, dry conditions to prevent sprouting.",
    "moisture_level": "Sun-dry produce for 2-3 days to reduce moisture and achieve a higher grade.",
    "foreign_matter": "Clean and sieve the produce to remove foreign matter before listing.",
    "size_uniformity": "Sort produce by size before listing for a more uniform lot.",
    "color_uniformity": "Remove discoloured items before listing for a more uniform lot.",
}


def grade(answers: dict) -> dict:
    """
    Input: dict with keys matching GRADE_RULES
    Output: { "grade": "A" | "B" | "C", "improvement_tip": str }
    """
    total_score = 0
    worst_param = None
    worst_score = 99

    for param, rule in GRADE_RULES.items():
        value = answers.get(param)
        if value is None:
            continue
        if callable(rule):
            score = rule(value)
        else:
            score = rule.get(value, 1)
        total_score += score
        if score < worst_score:
            worst_score = score
            worst_param = param

    max_possible = len(GRADE_RULES) * 3  # 18

    if total_score >= max_possible * 0.8:       # >= 14.4 → 15+
        grade_label = "A"
    elif total_score >= max_possible * 0.55:    # >= 9.9 → 10+
        grade_label = "B"
    else:
        grade_label = "C"

    tip = IMPROVEMENT_TIPS.get(worst_param, "Maintain current quality practices.")

    return {"grade": grade_label, "improvement_tip": tip}
