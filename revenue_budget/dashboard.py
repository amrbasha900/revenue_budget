"""Read-only executive dashboard for planned revenue (not actual invoiced sales)."""
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt

from revenue_budget.revenue_budget.report.mix_common import MONTHS


def build_dashboard(rows, budget_count, currency):
    customers = defaultdict(lambda: {"label": "", "category": "", "net": 0.0, "gross": 0.0})
    items = defaultdict(lambda: {"name": "", "uom": "", "qty": 0.0, "gross": 0.0, "net": 0.0})
    categories, groups = defaultdict(float), defaultdict(float)
    monthly = {month: {"gross": 0.0, "net": 0.0} for month in MONTHS}
    gross = net = 0.0

    for row in rows:
        g, n = flt(row.gross), flt(row.net)
        gross += g
        net += n
        c = customers[row.customer]
        c["label"] = row.customer_name or row.customer
        c["category"] = row.customer_category or _("Unassigned")
        c["net"] += n
        c["gross"] += g
        i = items[row.item_code]
        i["name"] = row.item_name or row.item_code
        i["uom"] = row.uom or ""
        i["qty"] += flt(row.qty)
        i["gross"] += g
        i["net"] += n
        categories[row.customer_category or _("Unassigned")] += n
        groups[row.item_group or _("Unassigned")] += n
        if row.budget_month in monthly:
            monthly[row.budget_month]["gross"] += g
            monthly[row.budget_month]["net"] += n

    best_month = max(MONTHS, key=lambda m: monthly[m]["net"]) if net else None
    by_customer = sorted(customers.items(), key=lambda t: (-t[1]["net"], t[0]))
    by_qty = sorted(items.items(), key=lambda t: (-t[1]["qty"], t[0]))
    by_value = sorted(items.items(), key=lambda t: (-t[1]["net"], t[0]))

    return {
        "currency": currency, "gross": round(gross, 2), "net": round(net, 2),
        "discount": round(gross - net, 2),
        "discount_rate": round((gross - net) / gross * 100, 2) if gross else 0,
        "budget_count": budget_count, "customer_count": len(customers),
        "item_count": len(items),
        "top_customer": {
            "code": by_customer[0][0], **by_customer[0][1],
        } if by_customer else None,
        "top_item_qty": {"code": by_qty[0][0], **by_qty[0][1]} if by_qty else None,
        "top_item_value": {"code": by_value[0][0], **by_value[0][1]} if by_value else None,
        "top_5_share": round(sum(v["net"] for _, v in by_customer[:5]) / net * 100, 2) if net else 0,
        "best_month": {"month": _(best_month), "value": round(monthly[best_month]["net"], 2)} if best_month else None,
        "months": [_(m) for m in MONTHS],
        "monthly_gross": [round(monthly[m]["gross"], 2) for m in MONTHS],
        "monthly_net": [round(monthly[m]["net"], 2) for m in MONTHS],
        "top_customers": [
            {"code": k, **v, "net": round(v["net"], 2),
             "share": round(v["net"] / net * 100, 2) if net else 0}
            for k, v in by_customer[:10]
        ],
        "top_items_qty": [{"code": k, **v, "qty": round(v["qty"], 3)} for k, v in by_qty[:10]],
        "top_items_value": [{"code": k, **v, "net": round(v["net"], 2)} for k, v in by_value[:10]],
        "categories": [{"name": k, "value": round(v, 2)}
                       for k, v in sorted(categories.items(), key=lambda t: -t[1])],
        "item_groups": [{"name": k, "value": round(v, 2)}
                        for k, v in sorted(groups.items(), key=lambda t: -t[1])],
    }


@frappe.whitelist()
def get_dashboard(company=None, fiscal_year=None, customer_category=None, customer=None,
                  item_group=None, budget_month=None):
    if not company or not fiscal_year:
        frappe.throw(_("Company and Fiscal Year are required"))
    if not frappe.has_permission("Customer Revenue Budget", "report"):
        frappe.throw(_("Not permitted to view revenue budget reports"), frappe.PermissionError)
    if not frappe.has_permission("Company", "read", company):
        frappe.throw(_("Not permitted for selected company"), frappe.PermissionError)

    params = {"company": company, "fiscal_year": fiscal_year}
    conditions = [
        "b.docstatus=1", "b.budget_status='Active'",
        "b.company=%(company)s", "b.fiscal_year=%(fiscal_year)s",
    ]
    for field, column in (
        ("customer_category", "b.customer_category"), ("customer", "b.customer"),
        ("item_group", "i.item_group"), ("budget_month", "b.budget_month"),
    ):
        value = locals()[field]
        if value:
            conditions.append(column + "=%(" + field + ")s")
            params[field] = value

    # Explicitly count DISTINCT parent budgets to avoid inflating count by child rows.
    rows = frappe.db.sql("""
        SELECT b.name AS budget, b.customer, c.customer_name, b.customer_category,
               b.budget_month, i.item_code, i.item_name, i.item_group, i.uom,
               i.planned_qty AS qty,
               i.planned_gross_revenue * b.exchange_rate AS gross,
               i.planned_net_revenue_base AS net
        FROM `tabCustomer Revenue Budget` b
        INNER JOIN `tabRevenue Budget Item` i
            ON i.parent=b.name AND i.parenttype='Customer Revenue Budget'
            AND i.parentfield='items'
        LEFT JOIN `tabCustomer` c ON c.name=b.customer
        WHERE """ + " AND ".join(conditions),
        params, as_dict=True
    )
    currency = frappe.db.get_value("Company", company, "default_currency")
    return build_dashboard(rows, len({row.budget for row in rows}), currency)
