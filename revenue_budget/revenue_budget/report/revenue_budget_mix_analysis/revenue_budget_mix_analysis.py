from collections import defaultdict
import frappe
from frappe import _
from revenue_budget.revenue_budget.report.mix_common import MONTHS, fetch_rows, group_keys, group_mode, graph

def execute(filters=None):
    filters=frappe._dict(filters or {})
    rows=fetch_rows(filters)
    keys=group_keys(group_mode(filters)) or ["customer_category"]
    columns=[
        {"fieldname":"group_label","label":_("Grouping"),"fieldtype":"Data","width":270},
        {"fieldname":"annual_total","label":_("Annual Net Revenue (Base)"),"fieldtype":"Currency","width":190},
        {"fieldname":"annual_share","label":_("Annual Share %"),"fieldtype":"Percent","width":130},
    ] + [{"fieldname":"month_"+str(i+1),"label":_(m),"fieldtype":"Currency","width":130} for i,m in enumerate(MONTHS)]
    annual=sum(float(r.amount or 0) for r in rows)
    result=[]
    def recurse(subrows,depth,parent,rootkey):
        field=keys[depth]
        buckets=defaultdict(list)
        for r in subrows:
            buckets[str(r.get(field) or _("Unassigned"))].append(r)
        for name in sorted(buckets):
            current=rootkey+(name,)
            id_="G-"+str(len(result)+1)
            item=buckets[name]
            values={m:0.0 for m in MONTHS}
            for r in item:
                if r.budget_month in values:
                    values[r.budget_month]+=float(r.amount or 0)
            summ=sum(values.values())
            out={"row_id":id_,"parent_id":parent,"indent":depth,"is_group":1,
                 "group_label":name,"annual_total":summ,
                 "annual_share":round(summ/annual*100,4) if annual else 0}
            for i,m in enumerate(MONTHS):
                out["month_"+str(i+1)]=values[m]
            result.append(out)
            if depth+1 < len(keys):
                recurse(item,depth+1,id_,current)
    recurse(rows,0,None,())
    chart=graph(rows,_("Monthly Net Revenue by Group (Base Currency)"),mode=group_mode(filters))
    return columns,result,None,chart
