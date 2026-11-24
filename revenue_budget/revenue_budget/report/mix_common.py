"""Shared, active-only revenue-budget reporting helpers."""
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
METRICS = {
    "Percentage": None,
    "Before Discount": "i.planned_gross_revenue",
    "After Discount": "i.planned_net_revenue",
}
MODES = {
    "None": [],
    "Customer Category": ["customer_category"],
    "Item Group": ["item_group"],
    "Customer Category > Item Group": ["customer_category", "item_group"],
    "Item Group > Customer Category": ["item_group", "customer_category"],
}


def metric_mode(filters):
    mode = (filters or {}).get("value_mode") or "Percentage"
    if mode not in METRICS:
        frappe.throw(_("Unsupported value mode"))
    return mode


def group_mode(filters):
    mode = (filters or {}).get("group_by") or "None"
    if mode not in MODES:
        frappe.throw(_("Unsupported grouping"))
    return mode


def group_keys(mode):
    return MODES.get(mode, [])


def fetch_rows(filters):
    filters = frappe._dict(filters or {})
    if not filters.get("fiscal_year") or not filters.get("company"):
        frappe.throw(_("Fiscal Year and Company are required"))
    # Never aggregate base currencies across companies.
    if not frappe.has_permission("Customer Revenue Budget", "report"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    if not frappe.has_permission("Company", "read", filters.company):
        frappe.throw(_("Not permitted for company"), frappe.PermissionError)
    clauses = ["b.docstatus = 1", "b.budget_status = 'Active'",
               "b.fiscal_year = %(fiscal_year)s", "b.company = %(company)s"]
    params = {"fiscal_year": filters.fiscal_year, "company": filters.company}
    for field, column in (
        ("customer_category", "b.customer_category"),
        ("customer", "b.customer"),
        ("item_group", "i.item_group"),
        ("item_code", "i.item_code"),
    ):
        if filters.get(field):
            clauses.append(column + " = %(" + field + ")s")
            params[field] = filters[field]

    return frappe.db.sql("""
        SELECT b.customer_category, b.customer, c.customer_name,
               i.item_group, i.item_code, i.item_name, b.budget_month,
               SUM(i.planned_gross_revenue * b.exchange_rate) AS gross,
               SUM(i.planned_net_revenue_base) AS net
        FROM `tabCustomer Revenue Budget` b
        INNER JOIN `tabRevenue Budget Item` i
            ON i.parent=b.name AND i.parenttype='Customer Revenue Budget'
            AND i.parentfield='items'
        LEFT JOIN `tabCustomer` c ON c.name=b.customer
        WHERE """ + " AND ".join(clauses) + """
        GROUP BY b.customer_category, b.customer, c.customer_name,
                 i.item_group, i.item_code, i.item_name, b.budget_month
    """, params, as_dict=True)


def amount(row, mode):
    return flt(row.gross if mode == "Before Discount" else row.net)


def customer_month_totals(rows, mode):
    totals = defaultdict(float)
    for row in rows:
        if row.budget_month in MONTHS:
            totals[(row.customer, row.budget_month)] += amount(row, mode)
    return totals


def share(numerator, denominator):
    return round(numerator / denominator * 100, 4) if denominator else 0.0


def group_share(subrows, all_rows, month, mode):
    """Weighted share of a cohort, never sum of individual customer percentages.

    Denominator is the total selected-metric revenue of each customer/month
    participating in this group, under the same item/category filters.
    """
    customers = {r.customer for r in subrows if r.budget_month == month}
    totals = customer_month_totals(all_rows, mode)
    denominator = sum(totals[(customer, month)] for customer in customers)
    numerator = sum(amount(r, mode) for r in subrows if r.budget_month == month)
    return share(numerator, denominator)


def graph(rows, title, as_percent=False, mode="Customer Category", value_mode="After Discount"):
    group = group_keys(mode)
    field = group[0] if group else "customer_category"
    buckets = defaultdict(list)
    for r in rows:
        buckets[str(r.get(field) or _("Unassigned"))].append(r)
    ordered = sorted(buckets, key=lambda k: -sum(amount(r, value_mode) for r in buckets[k]))
    top = ordered[:6]
    if len(ordered) > 6:
        label = _("Other")
        while label in buckets:
            label += " *"
        buckets[label] = [r for k in ordered[6:] for r in buckets[k]]
        top.append(label)
    datasets = []
    for key in top:
        values = [
            group_share(buckets[key], rows, m, value_mode) if as_percent
            else round(sum(amount(r, value_mode) for r in buckets[key] if r.budget_month == m), 2)
            for m in MONTHS
        ]
        datasets.append({"name": key, "values": values})
    return {
        "data": {"labels": [_(m) for m in MONTHS], "datasets": datasets},
        "type": "bar", "barOptions": {"stacked": not as_percent},
        "height": 300, "title": title,
    }
