frappe.ui.form.on("Customer Revenue Budget",{
refresh(frm){if(frm.doc.docstatus===1&&frm.doc.budget_status==="Active"){frm.add_custom_button(__("Request Change"),()=>frappe.new_doc("Revenue Budget Change Request",{budget:frm.doc.name}));}},
company(frm){if(frm.doc.company&&!frm.doc.currency)frappe.db.get_value("Company",frm.doc.company,"default_currency").then(x=>frm.set_value("currency",x.message.default_currency));}
});
frappe.ui.form.on("Revenue Budget Item",{item_code(frm,cdt,cdn){const r=locals[cdt][cdn];if(!r.item_code)return;frappe.db.get_value("Item",r.item_code,["item_name","item_group","brand","stock_uom"]).then(x=>{const i=x.message||{};["item_name","item_group","brand"].forEach(k=>frappe.model.set_value(cdt,cdn,k,i[k]));frappe.model.set_value(cdt,cdn,"uom",i.stock_uom);});}});