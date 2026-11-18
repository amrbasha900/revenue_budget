# Revenue Budget — Phase 1

ERPNext 15 / Frappe application. One budget per company + customer + fiscal year + month, with document-level currency and exchange rate, and item-level planned quantity, unit price, discount percentage, gross/discount/net revenue.

## Versions
Submit a draft to make it Active. Each change request submitted against an Active version creates a new submitted revision and marks the previous version Superseded. A cancellation change marks the active budget Cancelled. The Revenue Budget Summary report explicitly filters only submitted Active records so it excludes historical revisions. All previous versions are preserved and linked.

## Allowed change types
Price Change, Quantity Change, Price and Quantity Change, Discount Change, Exchange Rate Change, Add Item, Remove Item, Replace Item, Cancel Budget. The form disables irrelevant fields; Python server validation rejects unauthorized fields and edits to submitted budgets. The request may contain multiple item rows of one change type.

**No approval Workflow is included. Submitting a request directly applies the revision. Restrict Submit permission to authorized staff until workflow is introduced.**

Install/upgrade with `bench --site SITE migrate`, then `bench --site SITE clear-cache`. Test on staging before production. Planned budget only; no actuals, credit, payment terms or collections.
