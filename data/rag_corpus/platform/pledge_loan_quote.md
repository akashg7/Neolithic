---
title: Platform pledge loan quote
language: en
---

# Platform pledge loan quote

## What the quote shows
If a farmer holds the crop in a warehouse, the platform can show an indicative loan against it. The quote is not a lender's offer. Final terms depend on warehouse inspection, grade verification and lender approval.

## How the number is worked out
The crop value uses the cautious p10 forecast price, not the middle estimate, multiplied by the grade factor (A 100 percent, B 85 percent, C 70 percent). The loan is 70 percent of that value. Interest defaults to 12 percent a year, charged for the days stored.

## When no quote is shown
The card appears only if the expected gain from holding is larger than the interest on the loan. If the gain is equal to or smaller than the interest, the farmer is better off selling now and no pledge card is shown. No card also appears if the value is zero or the number of days is zero.

## Warehouse registration
The quote records whether the warehouse is registered with WDRA. WDRA registration helps keep stored produce insured and traceable. The 12 percent rate and the 70 percent loan ratio are platform defaults and not bank rates. Compare them with the KCC and e-NWR pledge loan terms.

Sources: repo files app/domain/pledge.py, app/domain/assessed_value.py and app/domain/constants.py.
