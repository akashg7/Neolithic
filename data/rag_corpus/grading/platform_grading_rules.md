---
title: Krishi-Mitr platform grading rules (A, B, C)
language: en
crops: [onion, soybean, tur, wheat, tomato]
---

# Krishi-Mitr platform grading rules (A, B, C)

## Prototype rules, not official standards
The platform grades each lot A, B or C from measured percentages. These thresholds are simplified values modelled on AGMARKNET-style grade specifications. They are a prototype rule set and not the official notified standards. For official grades see the WDRA onion and soyabean documents.

## What each grade means for price
Grade A is worth 100 percent of the base price. Grade B is worth 85 percent. Grade C is worth 70 percent. The platform applies these multipliers when it assesses lot value for a pledge loan.

## Onion
Onion is judged on surface moisture and size uniformity. Grade A needs moisture below 12 percent and size uniformity of at least 85 percent. Grade B needs moisture up to 15 percent and uniformity of at least 70 percent. Anything worse is Grade C. Tips the platform gives: cure in shade to bring moisture down, and sort into size bins of 45 to 55 mm.

## Soyabean, wheat, gram, maize and other grains and oilseeds
These are judged on moisture, foreign matter and damaged grain. Grade A needs moisture up to 10 percent, foreign matter up to 1 percent and damaged grain up to 2 percent. Grade B needs moisture up to 12 percent, foreign matter up to 2 percent and damaged grain up to 5 percent. Anything worse is Grade C. The same strategy is also used as an approximation for rice, groundnut, jowar, cotton and turmeric.

## Tomato, potato, green chilli and banana
Fresh vegetables are judged on decay, size uniformity and discolouration, because moisture is not a useful signal for them. Grade A needs damage up to 2 percent, uniformity of at least 85 percent and discolouration up to 5 percent. Grade B needs damage up to 8 percent, uniformity of at least 70 percent and discolouration up to 15 percent. Anything worse is Grade C.

## Tur
The platform has no grading rule registered for tur yet, so a tur lot cannot be graded by the measured-grade rules. WDRA has its own tur grade standard, but its numeric limits are not copied here.

## Six-question self-assay
Separately from measured grading, a farmer can answer six quick questions about the lot and get an indicative grade and an improvement tip. Measured grading uses the percentage rules above.

Sources: repo files app/engines/strategies/grading_strategy.py and app/domain/assessed_value.py.
