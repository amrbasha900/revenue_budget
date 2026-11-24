import frappe
from frappe import _

def execute(filters=None):
    f=frappe._dict(filters or {})
    conditions=["b.docstatus=1","b.budget_status='Active'"]
    params={}
    for k in ("company","customer","fiscal_year","budget_month"):
        if f.get(k):
            conditions.append("b."+k+"=%("+k+")s")
            params[k]=f[k]
    if f.get("item_code"):
        conditions.append("i.item_code=%(item_code)s")
        params["item_code"]=f.item_code
    specs=[
        ("budget","Budget","Link","Customer Revenue Budget"),("company","Company","Link","Company"),
        ("customer","Customer","Link","Customer"),("fiscal_year","Fiscal Year","Link","Fiscal Year"),
        ("budget_month","Month","Data",None),("revision_no","Revision","Int",None),
        ("item_code","Item","Link","Item"),("item_name","Item Name","Data",None),
        ("brand","Brand","Link","Brand"),("planned_qty","Quantity","Float",None),
        ("planned_rate","Unit Price","Currency","currency"),("planned_discount_percentage","Discount %","Percent",None),
        ("planned_net_revenue","Net Revenue","Currency","currency"),
        ("planned_net_revenue_base","Base Revenue","Currency",None),("currency","Currency","Link","Currency")]
    columns=[dict(fieldname=n,label=_(l),fieldtype=t,options=o,width=140) for n,l,t,o in specs]
    data=frappe.db.sql("""
        SELECT b.name AS budget,b.company,b.customer,b.fiscal_year,b.budget_month,b.revision_no,b.currency,
        i.item_code,i.item_name,i.brand,i.planned_qty,i.planned_rate,i.planned_discount_percentage,
        i.planned_net_revenue,i.planned_net_revenue_base
        FROM `tabCustomer Revenue Budget` b
        INNER JOIN `tabRevenue Budget Item` i
        ON i.parent=b.name AND i.parenttype='Customer Revenue Budget'
        WHERE """+" AND ".join(conditions)+"""
        ORDER BY b.fiscal_year,b.budget_month,b.customer,i.idx
    """,params,as_dict=True)
    return columns,data
