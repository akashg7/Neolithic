"""
Grading Engine — Deterministic self-assay grading.
Farmer answers 6 questions → rule engine maps to Grade A/B/C + improvement tip.
No ML, no external dependencies. Offline-capable.
"""

GRADE_RULES = {
    # Inputs are now integers 1, 2, 3 (higher = better)
    "size_uniform": lambda v: v,
    "colour_uniform": lambda v: v,
    "damage_pct": lambda v: 3 if v < 5 else (2 if v < 15 else 1),
    "sprouting": lambda v: v,
    "moisture_feel": lambda v: v,
    "foreign_matter": lambda v: v,
}

IMPROVEMENT_TIPS_EN = {
    "damage_pct": "Careful handling during harvest reduces damage. Consider sorting out damaged produce before listing.",
    "sprouting": "Store in cool, dark, dry conditions to prevent sprouting.",
    "moisture_feel": "Sun-dry produce for 2-3 days to reduce moisture and achieve a higher grade.",
    "foreign_matter": "Clean and sieve the produce to remove foreign matter before listing.",
    "size_uniform": "Sort produce by size before listing for a more uniform lot.",
    "colour_uniform": "Remove discoloured items before listing for a more uniform lot.",
}

IMPROVEMENT_TIPS_MR = {
    "damage_pct": "काढणी दरम्यान काळजी घेतल्यास नुकसान कमी होते. विकण्यापूर्वी खराब झालेले पीक वेगळे करा.",
    "sprouting": "कोंब येणे टाळण्यासाठी थंड, गडद आणि कोरड्या जागी साठवा.",
    "moisture_feel": "ओलावा कमी करण्यासाठी आणि चांगला ग्रेड मिळवण्यासाठी पीक 2-3 दिवस उन्हात वाळवा.",
    "foreign_matter": "विकण्यापूर्वी बाह्य पदार्थ काढण्यासाठी पीक स्वच्छ करा आणि चाळून घ्या.",
    "size_uniform": "एकरूप लॉटसाठी विकण्यापूर्वी पीक आकारानुसार वर्गीकरण करा.",
    "colour_uniform": "एकरूप लॉटसाठी विकण्यापूर्वी रंगहीन आयटम काढून टाका.",
}


def grade(answers: dict) -> dict:
    """
    Input: dict with keys matching GRADE_RULES
    Output: { "score": int, "grade": "A" | "B" | "C", "weakest_dimension": str, "tip_mr": str, "tip_en": str }
    """
    total_score = 0
    worst_param = "size_uniform"
    worst_score = 99

    for param, rule in GRADE_RULES.items():
        value = answers.get(param)
        if value is None:
            continue
        score = rule(value)
        total_score += score
        if score < worst_score:
            worst_score = score
            worst_param = param

    max_possible = len(GRADE_RULES) * 3  # 18
    # Scale score to 0..1000
    score_1000 = int((total_score / max_possible) * 1000)

    if total_score >= max_possible * 0.8:       # >= 14.4
        grade_label = "A"
    elif total_score >= max_possible * 0.55:    # >= 9.9
        grade_label = "B"
    else:
        grade_label = "C"

    tip_en = IMPROVEMENT_TIPS_EN.get(worst_param, "Maintain current quality practices.")
    tip_mr = IMPROVEMENT_TIPS_MR.get(worst_param, "सध्याच्या गुणवत्ता पद्धती राखून ठेवा.")

    return {
        "score": score_1000,
        "grade": grade_label,
        "weakest_dimension": worst_param,
        "tip_mr": tip_mr,
        "tip_en": tip_en
    }
