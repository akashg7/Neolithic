---
title: Escrow payment flow
language: en
---

# Escrow payment flow

## The steps
The buyer's money is held by the platform until the goods are checked. The states in order are: CREATED, DEPOSIT_HELD (buyer has paid in), IN_TRANSIT (farmer has dispatched), INSPECTED (buyer has checked the goods), and FUNDS_RELEASED (farmer is paid).

## Disputes
A dispute can be raised while the goods are in transit or after inspection, for example if the quality is rejected or the buyer does not show up. Funds stay held while the lot is DISPUTED. A dispute can be resolved by releasing the funds to the farmer. Steps cannot be skipped: for example, money cannot be released before inspection, and the platform returns a conflict error if someone tries.

## Payment gateway
Payments run through Razorpay in test mode in this prototype.

Sources: repo file app/domain/states/escrow_state.py.
