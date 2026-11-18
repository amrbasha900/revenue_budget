frappe.ui.form.on("Revenue Budget Change Request",{
change_type(frm){frm.clear_table("details");frm.set_value("new_exchange_rate",0);configure(frm);},
refresh(frm){configure(frm);}
});
function configure(frm){
const t=frm.doc.change_type;
const m={"new_item_code":["Add Item","Replace Item"],"new_qty":["Add Item","Replace Item","Quantity Change","Price and Quantity Change"],"new_rate":["Add Item","Replace Item","Price Change","Price and Quantity Change"],"new_discount_percentage":["Add Item","Replace Item","Discount Change"]};
frm.set_df_property("details","hidden",["Cancel Budget","Exchange Rate Change"].includes(t)?1:0);
frm.set_df_property("new_exchange_rate","hidden",t==="Exchange Rate Change"?0:1);
Object.entries(m).forEach(([f,k])=>frm.fields_dict.details?.grid.update_docfield_property(f,"read_only",k.includes(t)?0:1));
frm.fields_dict.details?.grid.update_docfield_property("item_code","read_only",t==="Add Item"?1:0);
frm.refresh_field("details");
}