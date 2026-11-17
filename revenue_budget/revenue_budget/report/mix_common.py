"""Shared active-budget aggregation for monthly mix reports."""
import frappe
from frappe import _

MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"]

def fetch_rows(filters):
    filters = frappe._dict(filters or {})
    if not filters.get("fiscal_year"):
        frappe.throw(_("Please select a Fiscal Year"))
    clauses = ["b.docstatus = 1", "b.budget_status = 'Active'", "b.fiscal_year = %(fiscal_year)s"]
    params = {"fiscal_year": filters.fiscal_year}
    for field, dbfield in [
        ("company", "b.company"), ("customer_category", "b.customer_category"),
        ("customer", "b.customer"), ("item_group", "i.item_group"),
        ("item_code", "i.item_code"),
    ]:
        if filters.get(field):
            clauses.append(dbfield + " = %(" + field + ")s")
            params[field] = filters[field]
    # Company base currency reporting prevents mixing incompatible source currencies.
    return frappe.db.sql("""
        SELECT b.customer_category, b.customer, c.customer_name,
               i.item_group, i.item_code, i.item_name, b.budget_month,
               SUM(i.planned_net_revenue_base) AS amount
        FROM `tabCustomer Revenue Budget` b
        INNER JOIN `tabRevenue Budget Item` i ON i.parent=b.name
          AND i.parenttype='Customer Revenue Budget' AND i.parentfield='items'
        LEFT JOIN `tabCustomer` c ON c.name=b.customer
        WHERE """ + " AND ".join(clauses) + """
        GROUP BY b.customer_category, b.customer, c.customer_name,
                 i.item_group, i.item_code, i.item_name, b.budget_month
    """, params, as_dict=True)

def to_month_map(rows):
    totals = {m: 0.0 for m in MONTHS}
    for r in rows:
        if r.budget_month in totals:
            totals[r.budget_month] += float(r.amount or 0)
    return totals

def group_mode(filters):
    return (filters or {}).get("group_by") or "None"

def group_keys(mode):
    return {
        "None": [],
        "Customer Category": ["customer_category"],
        "Item Group": ["item_group"],
        "Customer Category > Item Group": ["customer_category", "item_group"],
        "Item Group > Customer Category": ["item_group", "customer_category"],
    }.get(mode, [])

def graph(rows, title, as_percent=False, mode="Customer Category"):
    # Show top 6 series, and preserve remainder in 'Other', without a misleading partial total.
    primary = group_keys(mode)
    field = primary[0] if primary else "customer_category"
    buckets = {}
    for r in rows:
        k = str(r.get(field) or _("Unassigned"))
        if r.budget_month not in MONTHS:
            continue
        if k not in buckets:
            buckets[k] = {m: 0.0 for m in MONTHS}
        buckets[k][r.budget_month] += float(r.amount or 0)
    selected = sorted(buckets, key=lambda k: -sum(buckets[k].values()))[:6]
    if len(selected) < len(buckets):
        buckets[_("Other")] = {m: sum(v[m] for k,v in buckets.items() if k not in selected) for m in MONTHS}
        selected.append(_("Other"))
    denominator = to_month_map(rows)
    datasets = []
    for k in selected:
        values = [
            round((buckets[k][m] / denominator[m] * 100 if denominator[m] else 0) if as_percent else buckets[k][m], 2)
            for m in MONTHS
        ]
        datasets.append({"name": k, "values": values})
    return {
        "data": {"labels": [_(m) for m in MONTHS], "datasets": datasets},
        "type": "bar", "barOptions": {"stacked": True},
        "height": 300, "title": title,
    }
