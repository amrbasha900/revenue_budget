"""Estimated collection report: all amounts are planning estimates in base currency."""
from collections import defaultdict

import frappe
from frappe import _
from revenue_budget.commercial_forecast import MONTHS, forecast, _year


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.get("company") or not filters.get("fiscal_year"):
        frappe.throw(_("Company and Fiscal Year are required"))
    if not frappe.has_permission("Revenue Commercial Plan", "report") or not frappe.has_permission("Customer Revenue Budget", "report"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    if not frappe.has_permission("Company", "read", filters.company):
        frappe.throw(_("Not permitted for company"), frappe.PermissionError)

    conditions = {"company":filters.company, "fiscal_year":filters.fiscal_year,
                  "docstatus":1, "plan_status":"Active"}
    if filters.get("customer"): conditions["customer"] = filters.customer
    if filters.get("customer_category"): conditions["customer_category"] = filters.customer_category
    plans = frappe.get_all("Revenue Commercial Plan",filters=conditions,
                          fields=["name","customer"],order_by="customer")
    metrics = [
        ("gross_sales", _("Planned Sales Before Item Discount")),
        ("sales_after_item_discount", _("Planned Sales After Item Discount")),
        ("commercial_discount_on_sales", _("Commercial Discounts on Sales")),
        ("planned_net_revenue", _("Planned Net Revenue")),
        ("collections_prior_year", _("Collections From Previous Year")),
        ("collections_current_year", _("Collections From Current Year")),
        ("expected_collection_before_discount", _("Expected Collection Before Commercial Deductions")),
        ("discount_on_collection", _("Commercial Deductions on Collection")),
        ("expected_net_collection", _("Expected Net Collection"))
    ]
    columns = [
        {"fieldname":"customer","fieldtype":"Link","options":"Customer","label":_("Customer"),"width":170},
        {"fieldname":"metric","fieldtype":"Data","label":_("Metric"),"width":290}
    ] + [{"fieldname":f"month_{i}","fieldtype":"Currency","label":_(m),"width":130}
         for i,m in enumerate(MONTHS,1)] + [
        {"fieldname":"annual_total","fieldtype":"Currency","label":_("Annual Total"),"width":165}
    ]
    results = []
    aggregate = defaultdict(lambda:defaultdict(float))
    for plan in plans:
        data = forecast(filters.company,plan.customer,_year(filters.fiscal_year))
        for key,label in metrics:
            row={"customer":plan.customer,"metric":label}
            for i,month in enumerate(data["rows"],1):
                value=month[key]
                row[f"month_{i}"]=value
                aggregate[key][i]+=value
            row["annual_total"]=round(sum(month[key] for month in data["rows"]),2)
            results.append(row)
    for key,label in metrics:
        row={"customer":"","metric":_("TOTAL") + " - " + label}
        for i in range(1,13):
            row[f"month_{i}"]=round(aggregate[key][i],2)
        row["annual_total"]=round(sum(aggregate[key].values()),2)
        results.append(row)
    return columns,results
