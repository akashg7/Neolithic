---
title: FPO lot pooling
language: en
---

# FPO lot pooling

## What pooling does
An FPO (farmer producer organisation) admin can merge several small farmer lots into one larger batch lot. A bigger lot is easier to sell to a buyer who needs a large quantity.

## Rules
- Only an FPO admin linked to an FPO can pool, and only lots of that FPO's own member farmers.
- At least 2 distinct lots are needed, and all must be the same commodity.
- Only active lots can be pooled. After pooling, the source lots are marked pooled and cannot be used again.
- The batch grade is the lowest grade of any member lot. If any member lot is ungraded, the batch is treated as ungraded.
- The batch price is the average of member prices weighted by quantity, and it is set only if every member lot has a price.
- The batch records how much each member contributed.

Sources: repo file app/services/lot_pool_service.py.
