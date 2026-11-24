# Revenue Budget: annual commercial plans and estimated collection

This enhancement is **planning-only**. No Sales Invoice, Payment Entry, Journal Entry, ledger or actual settlement is created or updated.

## Scope
- One submitted **Revenue Commercial Plan** per company/customer/calendar year, with previous submitted revisions preserved as Superseded
- Collection Lag (Months), 0–12: budgeted sale month plus lag determines planned collection month
- **Discount Rules** with a stable Rule Code and selection of Percentage / Fixed Amount / Tiered
- Monthly, quarterly, or annual tiers; either Whole Band or Progressive
- Optional rule scope: all items, one item group, one item
- Discount effect: with planned sales collection or in one specified month/year
- Monthly 12-month preview in the plan, plus **Revenue Estimated Collection** Script Report

## How the options work

| Option | Effect |
|---|---|
| Percentage | Eligible planned sales × percentage |
| Fixed Amount / Monthly | Apply amount once for each month in the selected range |
| Fixed Amount / Once | Apply amount once, in first eligible sales month |
| Tiered / Monthly | Threshold independently evaluated per month |
| Tiered / Quarterly | Threshold evaluated for each calendar quarter |
| Tiered / Annual | Threshold evaluated for all eligible months in year |
| Whole Band | Reached tier's percentage × entire threshold base, plus tier's fixed bonus |
| Progressive | Apply per-band percentage to band segment; only last reached tier's fixed bonus |
| Before Item Discount | Use planned item gross revenue |
| After Item Discount | Use planned item net after item-level discounts, excluding other commercial rules |
| With Sales Collection | Discount follows its sales month's lag to planned collection |
| Specific Month | Total rule award reduces collection once in selected month/year |

All rules are additive and use the original chosen calculation base. Overlapping rules are not sequential, and their percentages are not compounded.

## Usage
1. Ensure monthly **Customer Revenue Budget** documents are submitted and Active.
2. Create **Revenue Commercial Plan** for a calendar year (e.g. 2026), company, customer.
3. Set debt age in months, and enter discount rows. Give each row a unique Rule Code.
4. For Tiered rows, add rows in Tier Thresholds using the same Rule Code, starting at zero, continuous, and with the last upper bound left at zero (unlimited).
5. Each field has a description; expand a discount row to see info icons and option meanings.
6. Save Draft, use **Preview 12-Month Plan**, check amounts, then Submit to make it Active.
7. Open **Revenue Estimated Collection** under Revenue Budget Workspace.

**Cross-year carryover:** January–December of the chosen year includes collections due from the previous year's *Active* plan. For example, 2025 November/December sales at 2-month lag are collected in 2026 January/February. If the prior-year plan is absent, the preview warns; no carryover is invented.

**Revisions:** Use Create Revision on an Active plan. It clones all rules and tiers into a new Draft. On Submit, the previous version becomes Superseded and the new one becomes Active. There is no approval workflow yet; restrict Submit permission accordingly.

**Boundaries and limitations:** Supports calendar-year fiscal years named YYYY, monthly lag (not invoice dates or aging by days), one base currency per company, and planned commercial deductions. It does not model actual invoices, taxes, independent cash payments, financial posting, payment installments, refunds, or unusual tier exclusion logic. Named customer accounts must match ERPNext Customer codes. A fixed amount in excess of expected collection can produce a negative estimated net amount: review this as an assumption, not a recorded transaction.

## Server commands
```bash
bench --site YOUR_SITE migrate
bench --site YOUR_SITE clear-cache
```

## Test plan
- Validate a plan with percentage, one-time fixed, monthly fixed, a quarterly tier, and an annual tier
- At 2-month lag, prove prior-year November/December collection flows to current-year January/February
- Change budget quantities to move a customer into a new tier, then re-preview
- Check no duplicate active plan versions and no edits to submitted plans
- Validate plan rules reject forbidden fields, overlapping or incomplete tiers
- Validate actual invoices/payments and ledger balances remain untouched

Tests included in `revenue_budget/tests/test_commercial_forecast.py`.
