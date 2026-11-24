frappe.query_reports["Revenue Estimated Collection"] = {
  filters: [
    {fieldname:"company",label:__("Company"),fieldtype:"Link",options:"Company",reqd:1},
    {fieldname:"fiscal_year",label:__("Fiscal Year"),fieldtype:"Link",options:"Fiscal Year",reqd:1},
    {fieldname:"customer_category",label:__("Customer Category"),fieldtype:"Link",options:"Revenue Budget Customer Category"},
    {fieldname:"customer",label:__("Customer"),fieldtype:"Link",options:"Customer"}
  ]
};