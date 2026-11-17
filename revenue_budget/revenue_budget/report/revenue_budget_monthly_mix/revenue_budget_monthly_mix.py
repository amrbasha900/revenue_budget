from collections import defaultdict
import frappe
from frappe import _
from frappe.utils import cstr
from revenue_budget.revenue_budget.report.mix_common import MONTHS, fetch_rows, to_month_map, group_keys, group_mode, graph

def execute(filters=None):
    filters=frappe._dict(filters or {})
    rows=fetch_rows(filters)
    totals=to_month_map(rows)
    columns=[
        {"fieldname":"customer_category","label":_("Customer Category"),"fieldtype":"Link","options":"Revenue Budget Customer Category","width":175},
        {"fieldname":"customer","label":_("Customer Code"),"fieldtype":"Link","options":"Customer","width":145},
        {"fieldname":"customer_name","label":_("Customer Name"),"fieldtype":"Data","width":180},
        {"fieldname":"item_group","label":_("Item Group"),"fieldtype":"Link","options":"Item Group","width":170},
        {"fieldname":"item_code","label":_("Item Code"),"fieldtype":"Link","options":"Item","width":150},
        {"fieldname":"item_name","label":_("Item Name"),"fieldtype":"Data","width":230},
    ] + [{"fieldname":"month_"+str(i+1),"label":_(m)+" %","fieldtype":"Percent","width":100} for i,m in enumerate(MONTHS)]
    # The denominator is the FULL filtered monthly net revenue, including every item.
    leaf=defaultdict(lambda: {m:0.0 for m in MONTHS})
    metadata={}
    for r in rows:
        key=(r.customer_category or "",r.customer,r.customer_name or "",r.item_group or "",r.item_code,r.item_name or "")
        metadata[key]=r
        if r.budget_month in MONTHS:
            leaf[key][r.budget_month]+=float(r.amount or 0)

    keys=group_keys(group_mode(filters))
    # No tree selected: maintain six fixed identity columns as in the sample.
    result=[]
    serial=[0]
    def append_item(key, parent, depth):
        serial[0]+=1
        row=dict(zip(["customer_category","customer","customer_name","item_group","item_code","item_name"],key))
        row.update({"row_id":"L-"+str(serial[0]),"parent_id":parent,"indent":depth})
        for i,m in enumerate(MONTHS):
            row["month_"+str(i+1)]=round(leaf[key][m]/totals[m]*100,4) if totals[m] else 0
        result.append(row)

    if not keys:
        for k in sorted(leaf):
            append_item(k,None,0)
    else:
        labels={"customer_category":"customer_category","item_group":"item_group"}
        indices={"customer_category":0,"item_group":3}
        def subtree(subkeys, level, parent_id, path):
            if level==len(keys):
                for k in sorted(subkeys):
                    append_item(k,parent_id,level)
                return
            field=keys[level]
            clusters=defaultdict(list)
            for k in subkeys:
                clusters[k[indices[field]] or _("Unassigned")].append(k)
            for group_name in sorted(clusters):
                current_path=path+(group_name,)
                gid="G-"+str(len(result)+1)+"-"+str(level)
                group_row={"row_id":gid,"parent_id":parent_id,"indent":level,"is_group":1}
                # Place group label in its native column and show its monthly contribution.
                group_row[field]=group_name
                for i,m in enumerate(MONTHS):
                    amount=sum(leaf[k][m] for k in clusters[group_name])
                    group_row["month_"+str(i+1)]=round(amount/totals[m]*100,4) if totals[m] else 0
                result.append(group_row)
                subtree(clusters[group_name],level+1,gid,current_path)
        subtree(list(leaf),0,None,())
    chart=graph(rows,_("Monthly Mix by Group (%)"),as_percent=True,mode=group_mode(filters))
    return columns,result,None,chart
