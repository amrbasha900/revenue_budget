"""Item/month matrix: percentages are scoped to each customer and month."""
from collections import defaultdict

import frappe
from frappe import _

from revenue_budget.revenue_budget.report.mix_common import (
    MONTHS, amount, customer_month_totals, fetch_rows, graph,
    group_keys, group_mode, group_share, metric_mode, share,
)

FIELDS = ["customer_category", "customer", "customer_name",
          "item_group", "item_code", "item_name"]


def execute(filters=None):
    filters = frappe._dict(filters or {})
    mode = metric_mode(filters)
    rows = fetch_rows(filters)
    totals = customer_month_totals(rows, mode)
    is_percent = mode == "Percentage"
    metric = "After Discount" if is_percent else mode
    columns = [
        {"fieldname": "customer_category", "label": _("Customer Category"),
         "fieldtype": "Link", "options": "Revenue Budget Customer Category", "width": 175},
        {"fieldname": "customer", "label": _("Customer Code"),
         "fieldtype": "Link", "options": "Customer", "width": 145},
        {"fieldname": "customer_name", "label": _("Customer Name"), "fieldtype": "Data", "width": 180},
        {"fieldname": "item_group", "label": _("Item Group"),
         "fieldtype": "Link", "options": "Item Group", "width": 170},
        {"fieldname": "item_code", "label": _("Item Code"),
         "fieldtype": "Link", "options": "Item", "width": 150},
        {"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 230},
    ] + [
        {"fieldname": f"month_{i}", "label": _(month) + (" %" if is_percent else " (Base)"),
         "fieldtype": "Percent" if is_percent else "Currency", "width": 120}
        for i, month in enumerate(MONTHS, 1)
    ]
    leaf = defaultdict(lambda: defaultdict(float))
    for row in rows:
        key = tuple(row.get(field) or "" for field in FIELDS)
        if row.budget_month in MONTHS:
            leaf[key][row.budget_month] += amount(row, metric)

    result = []
    serial = [0]

    def append_leaf(key, parent=None, depth=0):
        serial[0] += 1
        customer = key[1]
        item = dict(zip(FIELDS, key))
        item.update(row_id=f"L-{serial[0]}", parent_id=parent, indent=depth)
        for i, month in enumerate(MONTHS, 1):
            subtotal = leaf[key][month]
            item[f"month_{i}"] = (
                share(subtotal, totals[(customer, month)]) if is_percent
                else round(subtotal, 2)
            )
        result.append(item)

    hierarchy = group_keys(group_mode(filters))
    indices = {"customer_category": 0, "item_group": 3}
    if not hierarchy:
        for key in sorted(leaf):
            append_leaf(key)
    else:
        def recurse(subkeys, depth, parent):
            if depth == len(hierarchy):
                for key in sorted(subkeys):
                    append_leaf(key, parent, depth)
                return
            field = hierarchy[depth]
            groups = defaultdict(list)
            for key in subkeys:
                groups[key[indices[field]] or _("Unassigned")].append(key)
            for group_name in sorted(groups):
                group_id = f"G-{len(result) + 1}-{depth}"
                group_row = {"row_id": group_id, "parent_id": parent,
                             "indent": depth, "is_group": 1, field: group_name}
                selected = set(groups[group_name])
                group_rows = [
                    row for row in rows
                    if tuple(row.get(f) or "" for f in FIELDS) in selected
                ]
                for i, month in enumerate(MONTHS, 1):
                    if is_percent:
                        value = group_share(group_rows, rows, month, metric)
                    else:
                        value = sum(leaf[key][month] for key in selected)
                    group_row[f"month_{i}"] = round(value, 4 if is_percent else 2)
                result.append(group_row)
                recurse(groups[group_name], depth + 1, group_id)
        recurse(list(leaf), 0, None)

    chart = graph(
        rows, _("Monthly Customer Mix (%)") if is_percent else _("Monthly Revenue (Base)"),
        as_percent=is_percent, mode=group_mode(filters), value_mode=metric,
    )
    return columns, result, None, chart
