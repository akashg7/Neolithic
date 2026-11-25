---
title: How the hold-or-sell advice works
language: en
---

# How the hold-or-sell advice works

## What the advice answers
For a lot, the engine compares selling today with holding for 1 to 14 days. It uses the forecast for the mandi and crop at three levels: p10, p50 and p90. p10 is a bad-case price, p50 is the middle estimate and p90 is a good-case price. All prices are per quintal, and gains are for the whole lot.

## How net value is counted
For each hold day the engine takes the p50 price and subtracts five costs: transport, commission, loading, storage and spoilage. The commission is 2.5 percent of value. Transport is 50 paise per km. Loading is 2 paise per kg. Storage is 5 paise per kg per day. Spoilage is 0.20 percent of value per day. It picks the hold day with the best gain over selling now. Worst case is the same calculation with the p10 price.

## Possible answers
- HOLD: wait the number of days shown, because the expected gain beats selling now and the worst case is not a loss.
- SPLIT: sell half now and hold half, because the worst case is worse than selling now.
- SELL_NOW with reason GAIN_BELOW_COST: the best gain is under Rs 50 for the whole lot, so waiting is not worth it.
- NO_ADVICE: the engine refuses, and says why.

## When the engine refuses (NO_ADVICE)
- BAND_TOO_WIDE: the forecast range (p90 minus p10, divided by p50) is more than 35 percent, so the forecast is too uncertain to advise.
- INSUFFICIENT_HISTORY: fewer than 180 days of price history for that crop and market.
- STALE_DATA: the current spot price is missing or not positive.
- MODEL_UNAVAILABLE: there is no forecast model for that crop.
Refusing is deliberate. The platform would rather say it does not know than guess.

## Confidence
High if the band is under 20 percent, medium if it is wider but still within 35 percent.

Sources: repo files app/domain/window.py, app/domain/costs.py and app/domain/constants.py.
