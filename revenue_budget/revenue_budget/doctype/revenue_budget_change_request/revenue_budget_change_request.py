import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

FIELDS = {
    "Price Change": {"new_rate"},
    "Quantity Change": {"new_qty"},
    "Price and Quantity Change": {"new_qty", "new_rate"},
    "Discount Change": {"new_discount_percentage"},
    "Add Item": {"new_item_code", "new_qty", "new_rate", "new_discount_percentage"},
    "Remove Item": set(),
    "Replace Item": {"new_item_code", "new_qty", "new_rate", "new_discount_percentage"},
}

class RevenueBudgetChangeRequest(Document):
    def validate(self):
        if not self.is_new():
            old = self.get_doc_before_save()
            if old and old.docstatus == 1:
                frappe.throw(_("Applied requests cannot be changed."))
        if self.request_status != "Draft":
            frappe.throw(_("Request status is system-managed."))
        self.check_request()

    def check_request(self):
        budget = frappe.get_doc("Customer Revenue Budget", self.budget)
        if budget.docstatus != 1 or budget.budget_status != "Active":
            frappe.throw(_("Change request must reference an active, submitted budget."))
        kind = self.change_type
        if kind not in FIELDS and kind not in ("Exchange Rate Change", "Cancel Budget"):
            frappe.throw(_("Unsupported change type."))
        if kind in ("Exchange Rate Change", "Cancel Budget"):
            if self.details:
                frappe.throw(_("Item rows are forbidden for this change type."))
            if kind == "Exchange Rate Change" and flt(self.new_exchange_rate) <= 0:
                frappe.throw(_("New exchange rate must be positive."))
            if kind == "Cancel Budget" and flt(self.new_exchange_rate):
                frappe.throw(_("Cancellation must not alter exchange rate."))
            return
        if flt(self.new_exchange_rate):
            frappe.throw(_("Exchange rate changes require their own change type."))
        if not self.details:
            frappe.throw(_("At least one item change is required."))
        current = {r.item_code:r for r in budget.items}
        touched, added = set(),set()
        for row in self.details:
            if kind == "Add Item":
                if row.item_code:
                    frappe.throw(_("Add Item cannot reference an existing line."))
                identity = row.new_item_code
            else:
                if not row.item_code or row.item_code not in current:
                    frappe.throw(_("Existing item is required."))
                identity = row.item_code
            if identity in touched:
                frappe.throw(_("Duplicate change row."))
            touched.add(identity)
            permitted = FIELDS[kind]
            for key in ("new_item_code","new_qty","new_rate","new_discount_percentage"):
                if key not in permitted and row.get(key) not in (None, "", 0):
                    frappe.throw(_("Field {0} is forbidden for {1}.").format(key,kind))
            for key in permitted:
                if row.get(key) is None or row.get(key) == "":
                    frappe.throw(_("Field {0} is required.").format(key))
                if key != "new_item_code" and flt(row.get(key)) < 0:
                    frappe.throw(_("Negative values are forbidden."))
            if "new_discount_percentage" in permitted and flt(row.new_discount_percentage)>100:
                frappe.throw(_("Discount cannot exceed 100%."))
            if kind in ("Add Item","Replace Item"):
                if not row.new_item_code or row.new_item_code in added or row.new_item_code in current:
                    frappe.throw(_("New item must be unique and not already in the budget."))
                added.add(row.new_item_code)
            if row.item_code in current:
                old = current[row.item_code]
                row.old_qty, row.old_rate, row.old_discount_percentage = old.planned_qty,old.planned_rate,old.planned_discount_percentage

    def before_submit(self):
        # No workflow in phase one: submitting directly applies the change.
        frappe.db.sql("select name from `tabCustomer Revenue Budget` where name=%s for update", self.budget)
        budget = frappe.get_doc("Customer Revenue Budget",self.budget)
        if budget.budget_status != "Active":
            frappe.throw(_("Budget has already been superseded."))
        self.check_request()
        if self.change_type == "Cancel Budget":
            frappe.db.set_value("Customer Revenue Budget", budget.name, "budget_status", "Cancelled", update_modified=False)
            self.impact_net_revenue = -flt(budget.total_net_revenue_base)
            self.request_status = "Applied"
            return
        new = frappe.new_doc("Customer Revenue Budget")
        for field in ("company","customer","fiscal_year","budget_month","currency","exchange_rate"):
            new.set(field,budget.get(field))
        new.revision_no = budget.revision_no + 1
        new.supersedes = budget.name
        for item in budget.items:
            new.append("items", {k:item.get(k) for k in ("item_code","planned_qty","planned_rate","planned_discount_percentage")})
        if self.change_type == "Exchange Rate Change":
            new.exchange_rate = self.new_exchange_rate
        else:
            by_code={r.item_code:r for r in new.items}
            for r in self.details:
                kind=self.change_type
                if kind == "Add Item":
                    new.append("items",dict(item_code=r.new_item_code,planned_qty=r.new_qty,planned_rate=r.new_rate,planned_discount_percentage=r.new_discount_percentage))
                elif kind == "Remove Item":
                    new.items=[v for v in new.items if v.item_code != r.item_code]
                elif kind == "Replace Item":
                    v=by_code[r.item_code]
                    v.item_code,v.planned_qty,v.planned_rate,v.planned_discount_percentage=r.new_item_code,r.new_qty,r.new_rate,r.new_discount_percentage
                else:
                    v=by_code[r.item_code]
                    if kind in ("Price Change","Price and Quantity Change"):v.planned_rate=r.new_rate
                    if kind in ("Quantity Change","Price and Quantity Change"):v.planned_qty=r.new_qty
                    if kind == "Discount Change":v.planned_discount_percentage=r.new_discount_percentage
        # Old version is preserved in full; only new version appears in active reports.
        frappe.db.set_value("Customer Revenue Budget",budget.name,"budget_status","Superseded",update_modified=False)
        new.flags.revision_application=True
        new.insert()
        new.submit()
        frappe.db.set_value("Customer Revenue Budget",budget.name,"superseded_by",new.name,update_modified=False)
        self.result_budget=new.name
        self.impact_net_revenue=flt(new.total_net_revenue_base)-flt(budget.total_net_revenue_base)
        self.request_status="Applied"

    def on_cancel(self):
        frappe.throw(_("Applied requests cannot be cancelled."))
