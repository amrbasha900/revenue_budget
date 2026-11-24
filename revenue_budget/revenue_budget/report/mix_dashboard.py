"""Filter-sensitive KPI and chart data for the two Revenue Budget reports."""
from collections import defaultdict

import frappe
from frappe import _

from revenue_budget.revenue_budget.report.mix_common import (
    MONTHS, amount, fetch_rows, group_keys, group_mode, group_share, metric_mode,
)


def build_dashboard(rows, grouping="None", mode="Percentage"):
    metric = "After Discount" if mode == "Percentage" else mode
    percent = mode == "Percentage"
    hierarchy = group_keys(grouping)
    group_field = hierarchy[0] if hierarchy else "customer"
    grouped = defaultdict(list)
    by_month = defaultdict(float)
    customers, items = set(), set()
    for row in rows:
        group = str(row.get(group_field) or _("Unassigned"))
        grouped[group].append(row)
        if row.budget_month in MONTHS:
            by_month[row.budget_month] += amount(row, metric)
        customers.add(row.customer)
        items.add(row.item_code)

    ordered = sorted(grouped, key=lambda g: -sum(amount(r, metric) for r in grouped[g]))
    selected = ordered[:10]
    if len(ordered) > 10:
        other = _("Other")
        while other in grouped:
            other += " *"
        grouped[other] = [r for group in ordered[10:] for r in grouped[group]]
        selected.append(other)

    grand_total = sum(by_month.values())
    group_values = [
        group_share(grouped[group], rows, m, metric) if percent
        else round(sum(amount(r, metric) for r in grouped[group] if r.budget_month == m), 2)
        for group in selected for m in MONTHS
    ]
    monthly_share = [
        # Customer-normalized group share is a 100% contribution when the entire
        # customer scope is present; the month line shows 100% where data exists.
        100 if by_month[m] else 0 for m in MONTHS
    ]
    return {
        "group_label": {
            "customer_category": _("Customer Category"),
            "item_group": _("Item Group"),
            "customer": _("Customer"),
        }.get(group_field, _("Customer")),
        "value_mode": mode, "is_percent": percent,
        "total": grand_total, "customer_count": len(customers),
        "item_count": len(items), "group_count": len(ordered),
        "months": [_(m) for m in MONTHS],
        "monthly_totals": monthly_share if percent else [round(by_month[m], 2) for m in MONTHS],
        "groups": [
            {
                "name": g,
                "value": (
                    round(
                        sum(amount(r, metric) for r in grouped[g]) /
                        sum(amount(r, metric) for r in rows if r.customer in {x.customer for x in grouped[g]}) * 100, 2
                    )
                    if sum(amount(r, metric) for r in rows if r.customer in {x.customer for x in grouped[g]})
                    else 0
                ) if percent else round(sum(amount(r, metric) for r in grouped[g]), 2),
            }
            for g in selected
        ],
        "group_monthly": [
            {"name": g, "values": [
                group_share(grouped[g], rows, m, metric) if percent
                else round(sum(amount(r, metric) for r in grouped[g] if r.budget_month == m), 2)
                for m in MONTHS
            ]} for g in selected
        ],
        "is_empty": not rows,
    }


@frappe.whitelist()
def get_dashboard(filters=None):
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)
    filters = frappe._dict(filters or {})
    mode = metric_mode(filters)
    return build_dashboard(fetch_rows(filters), group_mode(filters), mode)
