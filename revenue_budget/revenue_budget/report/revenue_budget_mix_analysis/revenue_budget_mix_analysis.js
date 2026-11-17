frappe.query_reports["Revenue Budget Mix Analysis"] = {
  onload(report) {
    return frappe.require("/assets/revenue_budget/js/mix_dashboard.js").then(() => {
      revenue_budget.mix_dashboard.setup(report);
    });
  },
  after_datatable_render() {
    if (revenue_budget.mix_dashboard && frappe.query_report) {
      revenue_budget.mix_dashboard.refresh(frappe.query_report);
    }
  },

  filters: [{
    fieldname:"fiscal_year", label:__("Fiscal Year"), fieldtype:"Link", options:"Fiscal Year", reqd:1, on_change(report) {
      if (!report._no_refresh) {
        report.refresh(true);
        if (revenue_budget.mix_dashboard) revenue_budget.mix_dashboard.refresh(report);
      }
    }},{
    fieldname:"company", label:__("Company"), fieldtype:"Link", options:"Company", on_change(report) {
      if (!report._no_refresh) {
        report.refresh(true);
        if (revenue_budget.mix_dashboard) revenue_budget.mix_dashboard.refresh(report);
      }
    }},{
    fieldname:"customer_category", label:__("Customer Category"), fieldtype:"Link", options:"Revenue Budget Customer Category", on_change(report) {
      if (!report._no_refresh) {
        report.refresh(true);
        if (revenue_budget.mix_dashboard) revenue_budget.mix_dashboard.refresh(report);
      }
    }},{
    fieldname:"customer", label:__("Customer"), fieldtype:"Link", options:"Customer", on_change(report) {
      if (!report._no_refresh) {
        report.refresh(true);
        if (revenue_budget.mix_dashboard) revenue_budget.mix_dashboard.refresh(report);
      }
    }},{
    fieldname:"item_group", label:__("Item Group"), fieldtype:"Link", options:"Item Group", on_change(report) {
      if (!report._no_refresh) {
        report.refresh(true);
        if (revenue_budget.mix_dashboard) revenue_budget.mix_dashboard.refresh(report);
      }
    }},{
    fieldname:"item_code", label:__("Item"), fieldtype:"Link", options:"Item", on_change(report) {
      if (!report._no_refresh) {
        report.refresh(true);
        if (revenue_budget.mix_dashboard) revenue_budget.mix_dashboard.refresh(report);
      }
    }},{
    fieldname:"group_by", label:__("Tree Grouping"), fieldtype:"Select", options:"\nNone\nCustomer Category\nItem Group\nCustomer Category > Item Group\nItem Group > Customer Category", default:"Customer Category", on_change(report) {
      if (!report._no_refresh) {
        report.refresh(true);
        if (revenue_budget.mix_dashboard) revenue_budget.mix_dashboard.refresh(report);
      }
    }}],
  tree: true,
  name_field: "row_id",
  parent_field: "parent_id",
  initial_depth: 2
};