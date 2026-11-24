"""Purely planned discounts, monthly sales and collection timing. No actual ledger writes."""
from collections import defaultdict
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import flt

MONTHS = ("January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December")
M_INDEX = {m: i for i, m in enumerate(MONTHS)}
MAX_LAG = 12

def _money(value):
    return round(flt(value), 2)

def _year(fiscal_year):
    text = str(fiscal_year)
    if not text.isdigit() or len(text) != 4:
        frappe.throw(_("Planning requires a calendar-year Fiscal Year named YYYY."))
    return int(text)

def validate_plan(plan):
    year = _year(plan.fiscal_year)
    if not plan.company or not plan.customer:
        frappe.throw(_("Company and customer are required."))
    if not 0 <= int(plan.debt_age_months or 0) <= MAX_LAG:
        frappe.throw(_("Collection lag must be between 0 and 12 months."))
    base = frappe.db.get_value("Company", plan.company, "default_currency")
    if not base:
        frappe.throw(_("Company base currency is required."))
    if plan.currency and plan.currency != base:
        frappe.throw(_("Plan currency must equal the company base currency."))
    plan.currency = base
    codes = set()
    tiers = defaultdict(list)
    for tier in plan.tier_rules:
        tiers[tier.rule_code].append(tier)
        if flt(tier.min_sales) < 0 or flt(tier.max_sales) < 0:
            frappe.throw(_("Tier limits cannot be negative."))
        if flt(tier.max_sales) and flt(tier.max_sales) <= flt(tier.min_sales):
            frappe.throw(_("Tier upper bound must exceed lower bound."))
        if not 0 <= flt(tier.discount_percentage) <= 100 or flt(tier.fixed_bonus) < 0:
            frappe.throw(_("Invalid tier discount or fixed bonus."))
    for rule in plan.discount_rules:
        if rule.rule_code in codes or not rule.rule_code or not rule.rule_title:
            frappe.throw(_("Discount rule codes must be unique and named."))
        codes.add(rule.rule_code)
        kind = rule.calculation_type
        if kind not in ("Percentage", "Fixed Amount", "Tiered"):
            frappe.throw(_("Invalid calculation type."))
        if rule.from_month not in M_INDEX or rule.to_month not in M_INDEX or M_INDEX[rule.from_month] > M_INDEX[rule.to_month]:
            frappe.throw(_("Start month must not exceed end month."))
        if rule.scope_type not in ("All Items", "Item Group", "Item"):
            frappe.throw(_("Unsupported item scope."))
        if rule.scope_type == "Item" and not rule.item_code:
            frappe.throw(_("Choose an item for Item scope."))
        if rule.scope_type == "Item Group" and not rule.item_group:
            frappe.throw(_("Choose an item group for Item Group scope."))
        if rule.scope_type != "Item" and rule.item_code:
            frappe.throw(_("Item is only allowed for Item scope."))
        if rule.scope_type != "Item Group" and rule.item_group:
            frappe.throw(_("Item Group is only allowed for Item Group scope."))
        if rule.base_type not in ("Before Item Discount", "After Item Discount"):
            frappe.throw(_("Choose a valid calculation base."))
        if rule.settlement_type not in ("With Sales Collection", "Specific Month"):
            frappe.throw(_("Choose a settlement timing."))
        if rule.settlement_type == "Specific Month":
            if rule.settlement_month not in M_INDEX or int(rule.settlement_year or 0) < year:
                frappe.throw(_("Specific settlement requires a valid month and a year not before the plan year."))
            if int(rule.settlement_year) > year + 1:
                frappe.throw(_("Settlement may extend at most to the following year."))
        elif rule.settlement_month or int(rule.settlement_year or 0):
            frappe.throw(_("Specific month/year are only allowed for Specific Month settlement."))
        if kind == "Percentage":
            if not 0 <= flt(rule.percentage) <= 100 or flt(rule.fixed_amount) or rule.fixed_frequency or rule.target_period or rule.tier_method:
                frappe.throw(_("Percentage rule permits only the percentage calculation fields."))
        elif kind == "Fixed Amount":
            if flt(rule.fixed_amount) < 0 or rule.fixed_frequency not in ("Monthly", "Once"):
                frappe.throw(_("Fixed amount must be nonnegative with Monthly or Once frequency."))
            if flt(rule.percentage) or rule.target_period or rule.tier_method:
                frappe.throw(_("Fixed rule cannot contain percent or tier options."))
        else:
            if rule.target_period not in ("Monthly", "Quarterly", "Annual") or rule.tier_method not in ("Whole Band", "Progressive"):
                frappe.throw(_("Tiered rules require target period and calculation method."))
            if flt(rule.percentage) or flt(rule.fixed_amount) or rule.fixed_frequency:
                frappe.throw(_("Tiered rule cannot contain basic percentage or fixed amount."))
        if kind != "Tiered" and rule.rule_code in tiers:
            frappe.throw(_("Tier lines are only allowed for Tiered rules."))
        if kind == "Tiered":
            bands = sorted(tiers[rule.rule_code], key=lambda t: flt(t.min_sales))
            if not bands or flt(bands[0].min_sales) != 0:
                frappe.throw(_("Tiers must start at zero for {0}.").format(rule.rule_code))
            previous_upper = 0
            for index, band in enumerate(bands):
                if flt(band.min_sales) != previous_upper:
                    frappe.throw(_("Tier boundaries must be continuous without overlaps or gaps."))
                if not flt(band.max_sales) and index != len(bands) - 1:
                    frappe.throw(_("Unlimited upper tier must be last."))
                previous_upper = flt(band.max_sales)
            if previous_upper:
                frappe.throw(_("Last tier must have no upper limit."))
    for code in tiers:
        if code not in codes:
            frappe.throw(_("Tier references an unknown rule: {0}").format(code))


def _eligible(item, rule):
    if rule.scope_type == "Item":
        return item.item_code == rule.item_code
    if rule.scope_type == "Item Group":
        return item.item_group == rule.item_group
    return True


def _tier_award(amount, bands, method):
    ordered = sorted(bands, key=lambda r: flt(r.min_sales))
    chosen = None
    result = 0.0
    for row in ordered:
        lower, upper = flt(row.min_sales), flt(row.max_sales)
        if amount >= lower and (not upper or amount < upper):
            chosen = row
        if method == "Progressive":
            portion = max(0.0, min(amount, upper) - lower) if upper else max(0.0, amount - lower)
            result += portion * flt(row.discount_percentage) / 100.0
    if not chosen:
        return 0.0
    if method == "Whole Band":
        result = amount * flt(chosen.discount_percentage) / 100.0
    return result + flt(chosen.fixed_bonus)


def _periods(rule):
    eligible = list(range(M_INDEX[rule.from_month], M_INDEX[rule.to_month] + 1))
    if rule.calculation_type != "Tiered" or rule.target_period == "Monthly":
        return [[m] for m in eligible]
    if rule.target_period == "Quarterly":
        return [[m for m in eligible if m // 3 == q] for q in range(4) if any(m // 3 == q for m in eligible)]
    return [eligible]


def _spread(amount, months, weights):
    """Cents-safe weighted distribution, preserving exact planned award."""
    total = sum(weights.get(m, 0.0) for m in months)
    if total <= 0:
        return [(months[-1], _money(amount))] if months else []
    remaining = _money(amount)
    result = []
    for m in months[:-1]:
        part = _money(amount * weights.get(m, 0.0) / total)
        result.append((m, part))
        remaining = _money(remaining - part)
    result.append((months[-1], remaining))
    return result


def sales_for_year(company, customer, year):
    records = frappe.get_all("Customer Revenue Budget", filters={
        "company": company, "customer": customer, "fiscal_year": str(year),
        "docstatus": 1, "budget_status": "Active",
    }, fields=["name", "budget_month", "exchange_rate"])
    monthly = defaultdict(lambda: {"gross": 0.0, "after_item_discount": 0.0, "items": []})
    for record in records:
        budget = frappe.get_doc("Customer Revenue Budget", record.name)
        month = M_INDEX.get(record.budget_month)
        if month is None:
            continue
        for row in budget.items:
            gross = flt(row.planned_gross_revenue) * flt(record.exchange_rate)
            net = flt(row.planned_net_revenue_base)
            entry = frappe._dict({"item_code": row.item_code, "item_group": row.item_group,
                                  "gross": gross, "net": net})
            monthly[month]["items"].append(entry)
            monthly[month]["gross"] += gross
            monthly[month]["after_item_discount"] += net
    return monthly, len(records)


def calculate_year(plan):
    year = _year(plan.fiscal_year)
    sales, count = sales_for_year(plan.company, plan.customer, year)
    lag = int(plan.debt_age_months)
    allocations = defaultdict(float)
    ledgers = []
    settled = defaultdict(float)
    discounts_by_sale_month = defaultdict(float)
    tiers = defaultdict(list)
    for t in plan.tier_rules:
        tiers[t.rule_code].append(t)

    for rule in plan.discount_rules:
        amount_by_month = defaultdict(float)
        start, end = M_INDEX[rule.from_month], M_INDEX[rule.to_month]
        weights = {}
        for m in range(start, end + 1):
            field = "gross" if rule.base_type == "Before Item Discount" else "net"
            weights[m] = sum(flt(item[field]) for item in sales[m]["items"] if _eligible(item, rule))
        if rule.calculation_type == "Fixed Amount":
            months = [start] if rule.fixed_frequency == "Once" else list(range(start, end + 1))
            for m in months:
                amount_by_month[m] += flt(rule.fixed_amount)
        elif rule.calculation_type == "Percentage":
            for m in range(start, end + 1):
                amount_by_month[m] += weights[m] * flt(rule.percentage) / 100
        else:
            for months in _periods(rule):
                basis = sum(weights[m] for m in months)
                award = _tier_award(basis, tiers[rule.rule_code], rule.tier_method)
                for m, portion in _spread(award, months, weights):
                    amount_by_month[m] += portion

        if rule.settlement_type == "With Sales Collection":
            for m, val in amount_by_month.items():
                settlement_year, month = divmod(m + lag, 12)
                target_year = year + settlement_year
                key = (target_year, month)
                val = _money(val)
                allocations[key] += val
                discounts_by_sale_month[m] += val
                ledgers.append({"rule": rule.rule_code, "sales_month": MONTHS[m],
                                "settlement_year": target_year, "settlement_month": MONTHS[month],
                                "discount": val, "mode": "With Sales Collection"})
        else:
            target_year = int(rule.settlement_year)
            target_month = M_INDEX[rule.settlement_month]
            # Aggregate periodic award, settle once only in selected month.
            total = _money(sum(amount_by_month.values()))
            allocations[(target_year, target_month)] += total
            for m, val in amount_by_month.items():
                discounts_by_sale_month[m] += _money(val)
            ledgers.append({"rule": rule.rule_code, "sales_month": _("Applicable Period"),
                            "settlement_year": target_year, "settlement_month": rule.settlement_month,
                            "discount": total, "mode": "Specific Month"})

    sales_schedule = defaultdict(float)
    for m in range(12):
        target_year, target_month = year + (m + lag) // 12, (m + lag) % 12
        sales_schedule[(target_year, target_month)] += sales[m]["after_item_discount"]
    return {
        "year": year, "lag": lag, "count": count, "sales": sales,
        "expected_collections": sales_schedule, "collection_discounts": allocations,
        "discounts_by_sale_month": discounts_by_sale_month, "discount_details": ledgers,
    }


def active_plan(company, customer, year):
    names = frappe.get_all("Revenue Commercial Plan", filters={
        "company": company, "customer": customer, "fiscal_year": str(year),
        "docstatus": 1, "plan_status": "Active",
    }, pluck="name")
    if len(names) > 1:
        frappe.throw(_("More than one active commercial plan exists for this period."))
    return frappe.get_doc("Revenue Commercial Plan", names[0]) if names else None


def forecast(company, customer, year, draft_plan=None):
    year = int(year)
    selected = draft_plan or active_plan(company, customer, year)
    if not selected:
        frappe.throw(_("No commercial plan exists for the chosen customer and year."))
    current = calculate_year(selected)
    previous_plan = active_plan(company, customer, year - 1)
    previous = calculate_year(previous_plan) if previous_plan else None
    warnings = []
    if not current["count"]:
        warnings.append(_("No active submitted monthly revenue budgets were found for this year."))
    if current["lag"] and not previous_plan:
        warnings.append(_("Previous-year commercial plan is missing; opening collections are not estimated."))
    output = []
    for m in range(12):
        k = (year, m)
        now = current["sales"][m]
        new_collections = flt(current["expected_collections"].get(k))
        old_collections = flt(previous["expected_collections"].get(k)) if previous else 0.0
        current_disc = flt(current["collection_discounts"].get(k))
        prev_disc = flt(previous["collection_discounts"].get(k)) if previous else 0.0
        planned_discount = flt(current["discounts_by_sale_month"].get(m))
        output.append({
            "month": MONTHS[m], "gross_sales": _money(now["gross"]),
            "sales_after_item_discount": _money(now["after_item_discount"]),
            "commercial_discount_on_sales": _money(planned_discount),
            "planned_net_revenue": _money(now["after_item_discount"] - planned_discount),
            "collections_prior_year": _money(old_collections),
            "collections_current_year": _money(new_collections),
            "expected_collection_before_discount": _money(new_collections + old_collections),
            "discount_on_collection": _money(current_disc + prev_disc),
            "expected_net_collection": _money(new_collections + old_collections - current_disc - prev_disc),
        })
    return {
        "company": company, "customer": customer, "year": year,
        "lag_months": current["lag"], "currency": selected.currency,
        "rows": output, "warnings": warnings,
        "rule_details": [
            row for row in (previous["discount_details"] if previous else []) + current["discount_details"]
            if row["settlement_year"] == year
        ],
    }


@frappe.whitelist()
def preview(plan_name):
    if not frappe.has_permission("Revenue Commercial Plan", "read", plan_name):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    doc = frappe.get_doc("Revenue Commercial Plan", plan_name)
    if not frappe.has_permission("Customer Revenue Budget", "report"):
        frappe.throw(_("Not permitted to report budgets"), frappe.PermissionError)
    validate_plan(doc)
    return forecast(doc.company, doc.customer, _year(doc.fiscal_year), draft_plan=doc)


@frappe.whitelist()
def preview_draft(doc):
    doc = frappe.parse_json(doc) if isinstance(doc, str) else doc
    plan = frappe.get_doc(doc)
    if not frappe.has_permission("Revenue Commercial Plan", "create"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    if not frappe.has_permission("Company", "read", plan.company):
        frappe.throw(_("Not permitted for company"), frappe.PermissionError)
    if not frappe.has_permission("Customer Revenue Budget", "report"):
        frappe.throw(_("Not permitted to report budgets"), frappe.PermissionError)
    validate_plan(plan)
    return forecast(plan.company, plan.customer, _year(plan.fiscal_year), draft_plan=plan)
