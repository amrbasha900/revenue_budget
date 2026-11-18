"""Grouped monthly analysis with customer-based mix or gross/net values."""
from collections import defaultdict

import frappe
from frappe import _

from revenue_budget.revenue_budget.report.mix_common import (
    MONTHS, amount, fetch_rows, graph, group_keys, group_mode,
    group_share, metric_mode,
)


def execute(filters=None):
    filters = frappe._dict(filters or {})
    mode = metric_mode(filters)
    metric = "After Discount" if mode == "Percentage" else mode
    is_percent = mode == "Percentage"
    rows = fetch_rows(filters)
    keys = group_keys(group_mode(filters)) or ["customer"]
    columns = [
        {"fieldname": "group_label", "label": _("Grouping"), "fieldtype": "Data", "width": 270},
        {"fieldname": "annual_total",
         "label": _("Annual Customer Mix %") if is_percent else _("Annual Revenue (Base)"),
         "fieldtype": "Percent" if is_percent else "Currency", "width": 195},
    ] + [
        {"fieldname": f"month_{i}", "label": _(month) + (" %" if is_percent else " (Base)"),
         "fieldtype": "Percent" if is_percent else "Currency", "width": 130}
        for i, month in enumerate(MONTHS, 1)
    ]
    result = []

    def recurse(subrows, depth, parent):
        field = keys[depth]
        buckets = defaultdict(list)
        for r in subrows:
            buckets[str(r.get(field) or _("Unassigned"))].append(r)
        for label in sorted(buckets):
            group_rows = buckets[label]
            identifier = f"G-{len(result) + 1}"
            current = {
                "row_id": identifier, "parent_id": parent, "indent": depth,
                "is_group": 1, "group_label": label,
            }
            gross_total = sum(amount(r, metric) for r in group_rows)
            customers = {r.customer for r in group_rows}
            overall = sum(amount(r, metric) for r in rows if r.customer in customers)
            current["annual_total"] = (
                round(gross_total / overall * 100, 4) if overall else 0
            ) if is_percent else round(gross_total, 2)
            for i, month in enumerate(MONTHS, 1):
                current[f"month_{i}"] = (
                    group_share(group_rows, rows, month, metric) if is_percent
                    else round(sum(amount(r, metric) for r in group_rows if r.budget_month == month), 2)
                )
            result.append(current)
            if depth + 1 < len(keys):
                recurse(group_rows, depth + 1, identifier)
    recurse(rows, 0, None)
    chart = graph(
        rows, _("Monthly Customer Mix (%)") if is_percent else _("Monthly Revenue (Base)"),
        as_percent=is_percent, mode=group_mode(filters), value_mode=metric,
    )
    return columns, result, None, chart
