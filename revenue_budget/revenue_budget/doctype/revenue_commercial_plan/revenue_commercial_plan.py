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
        clean = lambda value: re.sub(r"[^\\w-]+", "-", str(value), flags=re.UNICODE).strip("-")
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
