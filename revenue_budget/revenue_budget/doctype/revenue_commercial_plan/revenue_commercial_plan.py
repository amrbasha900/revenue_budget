"""Annual customer commercial plan; submitted plans are immutable snapshots."""
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")


class RevenueCommercialPlan(Document):
    def autoname(self):
        clean = lambda value: re.sub(r"[^\w-]+", "-", str(value), flags=re.UNICODE).strip("-")
        self.name = "RCP-{}-{}-{}-V{}".format(
            clean(self.company), clean(self.customer), clean(self.fiscal_year), int(self.revision_no or 1)
        )

    def validate(self):
        from revenue_budget.commercial_forecast import validate_plan
        validate_plan(self)
        previous = self.get_doc_before_save()
        if previous and previous.docstatus == 1:
            frappe.throw(_("A submitted commercial plan is immutable. Make a new revision."))
        if self.plan_status != "Draft":
            frappe.throw(_("Plan status is maintained automatically."))

    def before_submit(self):
        # Explicit submitted revision is linked; previous active is superseded only
        # after new version validates. All changes share one request transaction.
        active = frappe.get_all(
            "Revenue Commercial Plan",
            filters={
                "company": self.company, "customer": self.customer,
                "fiscal_year": self.fiscal_year, "plan_status": "Active",
                "docstatus": 1,
            },
            pluck="name",
        )
        if active:
            if len(active) != 1 or active[0] != self.supersedes:
                frappe.throw(_("An active plan exists. Link it as Previous Plan for a revision."))
            previous = frappe.get_doc("Revenue Commercial Plan", active[0])
            if int(self.revision_no) != int(previous.revision_no) + 1:
                frappe.throw(_("Revision must increment the active plan revision by one."))
            frappe.db.set_value("Revenue Commercial Plan", previous.name,
                                "plan_status", "Superseded", update_modified=False)
        else:
            if self.supersedes or int(self.revision_no or 1) != 1:
                frappe.throw(_("First plan must have no previous plan and revision 1."))
        self.plan_status = "Active"

    def on_cancel(self):
        frappe.throw(_("Submitted commercial plans cannot be cancelled directly."))

    def on_trash(self):
        if self.docstatus or self.plan_status != "Draft":
            frappe.throw(_("Historical plans must be retained."))

@frappe.whitelist()
def create_revision(name):
    if not frappe.has_permission("Revenue Commercial Plan", "create"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    old = frappe.get_doc("Revenue Commercial Plan", name)
    old.check_permission("read")
    if old.plan_status != "Active" or old.docstatus != 1:
        frappe.throw(_("Only an active submitted plan can be revised."))
    if not frappe.has_permission("Company", "read", old.company):
        frappe.throw(_("Not permitted for company"), frappe.PermissionError)
    duplicate = frappe.get_all(
        "Revenue Commercial Plan",
        filters={"supersedes": old.name, "docstatus": 0},
        limit=1, pluck="name",
    )
    if duplicate:
        frappe.throw(_("A draft revision already exists: {0}").format(duplicate[0]))
    new = frappe.new_doc("Revenue Commercial Plan")
    for key in ("company", "customer", "fiscal_year", "customer_category", "debt_age_months"):
        new.set(key, old.get(key))
    new.supersedes = old.name
    new.revision_no = int(old.revision_no or 1) + 1
    for row in old.discount_rules:
        new.append("discount_rules", {
            key: row.get(key) for key in (
                "rule_code", "rule_title", "calculation_type", "percentage", "fixed_amount",
                "fixed_frequency", "target_period", "tier_method", "base_type", "scope_type",
                "item_group", "item_code", "from_month", "to_month", "settlement_type",
                "settlement_month", "settlement_year",
            )
        })
    for row in old.tier_rules:
        new.append("tier_rules", {
            key: row.get(key) for key in (
                "rule_code", "min_sales", "max_sales", "discount_percentage", "fixed_bonus",
            )
        })
    new.insert()
    return new.name
