"""Dashboard data for revenue budget Script Reports.

Only submitted active versions are included. Values use company base currency.
"""
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt

from revenue_budget.revenue_budget.report.mix_common import MONTHS, fetch_rows, group_keys, group_mode


def build_dashboard(rows, grouping="None"):
    hierarchy = group_keys(grouping)
    group_field = hierarchy[0] if hierarchy else "customer_category"
    by_group = defaultdict(float)
    by_month = defaultdict(float)
    per_group_month = defaultdict(lambda: defaultdict(float))
    customers = set()
    items = set()
    for row in rows:
        amount = flt(row.amount)
        group = str(row.get(group_field) or _("Unassigned"))
        month = row.budget_month
        customers.add(row.customer)
        items.add(row.item_code)
        by_group[group] += amount
        if month in MONTHS:
            by_month[month] += amount
            per_group_month[group][month] += amount

    # Highest value groups are visible individually; others are aggregated, never dropped.
    ranked = sorted(by_group, key=lambda g: (-by_group[g], g))
    visible = ranked[:10]
    if len(ranked) > 10:
        other = _("Other")
        # Prevent an actual group from colliding with the Other bucket.
        while other in by_group:
            other += " *"
        by_group[other] = sum(by_group[g] for g in ranked[10:])
        per_group_month[other] = {
            month: sum(per_group_month[g][month] for g in ranked[10:])
            for month in MONTHS
        }
        visible.append(other)

    grand_total = sum(by_month.values())
    return {
        "group_label": {
            "customer_category": _("Customer Category"),
            "item_group": _("Item Group"),
        }.get(group_field, _("Customer Category")),
        "total": grand_total,
        "customer_count": len(customers),
        "item_count": len(items),
        "group_count": len(ranked),
        "months": [_(m) for m in MONTHS],
        "monthly_totals": [round(by_month[m], 2) for m in MONTHS],
        "groups": [{"name": g, "value": round(by_group[g], 2)} for g in visible],
        "group_monthly": [
            {"name": g, "values": [round(per_group_month[g][m], 2) for m in MONTHS]}
            for g in visible
        ],
        "is_empty": not rows,
    }


@frappe.whitelist()
def get_dashboard(filters=None):
    if not frappe.has_permission("Customer Revenue Budget", "report"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)
    filters = frappe._dict(filters or {})
    if not filters.get("company"):
        frappe.throw(_("Please select a Company to use one consistent base currency."))
    # Company access is checked separately from the report role.
    if not frappe.has_permission("Company", "read", filters.company):
        frappe.throw(_("Not permitted for selected company"), frappe.PermissionError)
    return build_dashboard(fetch_rows(filters), group_mode(filters))
