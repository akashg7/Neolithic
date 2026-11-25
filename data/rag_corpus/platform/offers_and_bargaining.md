---
title: Offers, counter-offers and lot status
language: en
---

# Offers, counter-offers and lot status

## Making an offer
A buyer makes an offer on one or more lots with a price per quintal. The farmer can accept, reject or counter.

## Three rounds only
Price bargaining is limited to 3 rounds. After the third round no further counter-offer is allowed and the platform answers with a MAX_ROUNDS error. The farmer or buyer must then accept or reject.

## Lot status
A lot starts as active. When an offer is accepted the lot is locked, then sold when the deal completes. If the offer is rejected or expires the lot goes back to active. A lot can also be pooled into an FPO batch or cancelled. Sold, pooled and cancelled are final.

## Matching buyers and lots
The matching engine scores a lot against a buyer's demand. The default balanced strategy weights grade 40 percent, price fit 30 percent and distance 30 percent, and ignores lots more than 500 km away. A fast-clearance option weights distance 60 percent, grade 30 percent and price 10 percent, within 150 km. If one lot is too small, the engine combines several lots to cover the quantity.

Sources: repo files app/services/offer_service.py, app/domain/lot_lifecycle.py, app/engines/matching_engine.py and app/engines/strategies/matching_strategy.py.
