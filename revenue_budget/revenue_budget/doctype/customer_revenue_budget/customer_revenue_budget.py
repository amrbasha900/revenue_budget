import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

class CustomerRevenueBudget(Document):
    def validate(self):
        if not self.is_new():
            old = self.get_doc_before_save()
            if old and old.docstatus == 1:
                frappe.throw(_("Submitted budgets are immutable. Use a change request."))
        if self.budget_status != "Draft":
            frappe.throw(_("Budget status is managed by the system."))
        if flt(self.exchange_rate) <= 0:
            frappe.throw(_("Exchange rate must be positive."))
        if not self.items:
            frappe.throw(_("At least one budget item is required."))
        seen = set()
        totals = [0, 0, 0, 0]
        for row in self.items:
            if row.item_code in seen:
                frappe.throw(_("Duplicate item: {0}").format(row.item_code))
            seen.add(row.item_code)
            if flt(row.planned_qty) < 0 or flt(row.planned_rate) < 0:
                frappe.throw(_("Quantity and price cannot be negative."))
            if not 0 <= flt(row.planned_discount_percentage) <= 100:
                frappe.throw(_("Invalid discount percentage."))
            i = frappe.db.get_value("Item", row.item_code, ["item_name","item_group","brand","stock_uom"], as_dict=True)
            if not i:
                frappe.throw(_("Item not found: {0}").format(row.item_code))
            row.item_name, row.item_group, row.brand, row.uom = i.item_name, i.item_group, i.brand, i.stock_uom
            row.planned_gross_revenue = flt(row.planned_qty) * flt(row.planned_rate)
            row.planned_discount_amount = row.planned_gross_revenue * flt(row.planned_discount_percentage) / 100
            row.planned_net_revenue = row.planned_gross_revenue - row.planned_discount_amount
            row.planned_net_revenue_base = row.planned_net_revenue * flt(self.exchange_rate)
            for n, amount in enumerate([row.planned_gross_revenue,row.planned_discount_amount,row.planned_net_revenue,row.planned_net_revenue_base]):
                totals[n] += amount
        self.total_gross_revenue, self.total_discount_amount, self.total_net_revenue, self.total_net_revenue_base = totals
        self.series_key = "|".join([self.company, self.customer, self.fiscal_year, self.budget_month])
        existing = frappe.get_all("Customer Revenue Budget", filters={"series_key":self.series_key,"budget_status":"Active","name":["!=",self.name or ""]},pluck="name",limit=1)
        if existing and not self.flags.revision_application:
            frappe.throw(_("An active budget exists for the same company, customer, year and month."))

    def before_submit(self):
        if self.budget_status != "Draft":
            frappe.throw(_("Only draft budgets can be submitted."))
        if not self.flags.revision_application and frappe.db.exists("Customer Revenue Budget",{"series_key":self.series_key,"budget_status":"Active"}):
            frappe.throw(_("An active budget already exists for this period."))
        self.budget_status = "Active"

    def on_cancel(self):
        frappe.throw(_("Use a budget cancellation request, not direct cancellation."))

    def on_trash(self):
        if self.docstatus or self.budget_status != "Draft":
            frappe.throw(_("Historical budgets cannot be deleted."))
