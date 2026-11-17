frappe.query_reports["Revenue Budget Mix Analysis"] = {
  filters: [{
    fieldname:"fiscal_year", label:__("Fiscal Year"), fieldtype:"Link", options:"Fiscal Year", reqd:1
  },{
    fieldname:"company", label:__("Company"), fieldtype:"Link", options:"Company"
  },{
    fieldname:"customer_category", label:__("Customer Category"), fieldtype:"Link", options:"Revenue Budget Customer Category"
  },{
    fieldname:"customer", label:__("Customer"), fieldtype:"Link", options:"Customer"
  },{
    fieldname:"item_group", label:__("Item Group"), fieldtype:"Link", options:"Item Group"
  },{
    fieldname:"item_code", label:__("Item"), fieldtype:"Link", options:"Item"
  },{
    fieldname:"group_by", label:__("Tree Grouping"), fieldtype:"Select", options:"\nNone\nCustomer Category\nItem Group\nCustomer Category > Item Group\nItem Group > Customer Category", default:"Customer Category"
  }],
  tree: true,
  name_field: "row_id",
  parent_field: "parent_id",
  initial_depth: 2
};