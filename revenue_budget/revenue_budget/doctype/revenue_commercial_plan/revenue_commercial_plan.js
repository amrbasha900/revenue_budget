/* Commercial planning: field explanations, conditional fields, and preview. */
frappe.ui.form.on("Revenue Commercial Plan", {
  refresh(frm) {
    revenue_commercial_help(frm);
    if (frm.doc.company && frm.doc.customer && frm.doc.fiscal_year) {
      frm.add_custom_button(__("Preview 12-Month Plan"), () => revenue_commercial_preview(frm), __("Planning"));
    }
    if (frm.doc.docstatus === 1 && frm.doc.plan_status === "Active") {
      frm.add_custom_button(__("Create Revision"), () => {
        frappe.call({
          method: "revenue_budget.revenue_budget.doctype.revenue_commercial_plan.revenue_commercial_plan.create_revision",
          args: {name: frm.doc.name}, freeze: true,
          callback: result => {
            if (result.message) frappe.set_route("Form", "Revenue Commercial Plan", result.message);
          }
        });
      }, __("Planning"));
    }
  },
  company(frm) { revenue_commercial_help(frm); },
  discount_rules_on_form_rendered(frm) {
    revenue_commercial_toggle(frm);
    revenue_commercial_help(frm);
  },
  tier_rules_on_form_rendered(frm) { revenue_commercial_help(frm); },
});

frappe.ui.form.on("Revenue Commercial Discount Rule", {
  calculation_type(frm) { revenue_commercial_toggle(frm); },
  scope_type(frm) { revenue_commercial_toggle(frm); },
  settlement_type(frm) { revenue_commercial_toggle(frm); },
  fixed_frequency(frm) { revenue_commercial_toggle(frm); },
  form_render(frm) { revenue_commercial_toggle(frm); revenue_commercial_help(frm); },
});

function revenue_commercial_toggle(frm) {
  const grid = frm.fields_dict.discount_rules?.grid;
  if (!grid) return;
  const gridRow = grid.grid_rows?.find(row => row.grid_form && row.grid_form.wrapper.is(":visible"));
  if (!gridRow) return;
  const rule = gridRow.doc;
  const show = {
    percentage: rule.calculation_type === "Percentage",
    fixed_amount: rule.calculation_type === "Fixed Amount",
    fixed_frequency: rule.calculation_type === "Fixed Amount",
    target_period: rule.calculation_type === "Tiered",
    tier_method: rule.calculation_type === "Tiered",
    item_group: rule.scope_type === "Item Group",
    item_code: rule.scope_type === "Item",
    settlement_month: rule.settlement_type === "Specific Month",
    settlement_year: rule.settlement_type === "Specific Month",
  };
  Object.entries(show).forEach(([key, visible]) => {
    const field = gridRow.grid_form.fields_dict[key];
    if (field) field.$wrapper.toggle(visible);
  });
}

const revenueCommercialOptions = {
  calculation_type: [
    "Percentage: Multiply eligible planned sales by the rate.",
    "Fixed Amount: A fixed amount monthly or once.",
    "Tiered: Select discount based on monthly, quarterly or annual target sales."
  ],
  base_type: [
    "Before Item Discount: Use planned gross sales.",
    "After Item Discount: Use item-line planned net sales. Other commercial rules are not subtracted."
  ],
  settlement_type: [
    "With Sales Collection: Reduces collection after the customer's month lag.",
    "Specific Month: Entire calculated award reduces collection once, in the specified month and year."
  ],
  target_period: [
    "Monthly: Each month independently qualifies for a tier.",
    "Quarterly: Sales of each calendar quarter determine the discount.",
    "Annual: Full-year sales determine the tier, even though reports show monthly impact."
  ],
  tier_method: [
    "Whole Band: Selected rate applies to the entire period sales value.",
    "Progressive: Each tier rate applies only to sales inside its range."
  ],
  fixed_frequency: [
    "Monthly: Apply the fixed amount for every month in the From/To range.",
    "Once: Apply the fixed amount once in the first eligible month."
  ],
  scope_type: [
    "All Items: Every budget item is eligible.",
    "Item Group: Only products in one Item Group count toward the discount.",
    "Item: Only one item counts toward the discount."
  ],
  debt_age_months: [
    "0 means collect during the sale month.",
    "1 means collect the next month; 2 means January sales collected in March.",
    "Prior-year sales carried into this year follow the prior-year plan's own terms."
  ],
};
function revenue_commercial_help(frm) {
  const withInfo = (field, options) => {
    if (!field || !field.$wrapper) return;
    const label = field.$wrapper.find(".control-label").first();
    if (!label.length || label.find(".rb-help-icon").length) return;
    const desc = field.df.description || "";
    const optionText = (options || []).join("\n");
    const content = [desc, optionText].filter(Boolean).join("\n\n");
    if (!content) return;
    const icon = $('<span class="rb-help-icon" role="img" aria-label="Field help" tabindex="0" style="margin-inline-start:7px;cursor:help;color:var(--text-muted);font-size:13px">ⓘ</span>');
    icon.attr("title", content).attr("aria-description", content);
    label.append(icon);
  };
  Object.entries(frm.fields_dict).forEach(([name, field]) => withInfo(field, revenueCommercialOptions[name]));
  for (const table of ["discount_rules", "tier_rules"]) {
    const grid = frm.fields_dict[table]?.grid;
    if (!grid) continue;
    grid.grid_rows?.forEach(row => {
      if (!row.grid_form) return;
      Object.entries(row.grid_form.fields_dict || {}).forEach(([name, field]) => withInfo(field, revenueCommercialOptions[name]));
    });
  }
}

function revenue_commercial_preview(frm) {
  const isSaved = !frm.is_new() && !frm.is_dirty();
  frappe.call({
    method: isSaved ? "revenue_budget.commercial_forecast.preview" : "revenue_budget.commercial_forecast.preview_draft",
    args: isSaved ? {plan_name: frm.doc.name} : {doc: frm.doc},
    freeze: true, freeze_message: __("Calculating planned collections..."),
    callback: (r) => {
      if (!r.message) return;
      const data = r.message;
      const fmt = n => new Intl.NumberFormat("en-US",{minimumFractionDigits:2,maximumFractionDigits:2}).format(Number(n||0));
      const escape = s => frappe.utils.escape_html(String(s??""));
      const headers = ["Month","Gross Sales","Sales after Item Discount","Commercial Discounts on Sales","Planned Net Revenue","Opening-Year Collections","Current-Year Collections","Collection Discounts","Expected Net Collection"];
      const keys = ["month","gross_sales","sales_after_item_discount","commercial_discount_on_sales","planned_net_revenue","collections_prior_year","collections_current_year","discount_on_collection","expected_net_collection"];
      const warnings = (data.warnings||[]).map(w=>'<p style="color:var(--orange-500)">'+escape(w)+'</p>').join("");
      const head = '<thead><tr>'+headers.map(x=>'<th>'+__(x)+'</th>').join("")+'</tr></thead>';
      const body = '<tbody>'+data.rows.map(row=>'<tr>'+keys.map(k=>'<td>'+ (k==="month" ? escape(__(row[k])) : fmt(row[k])) +'</td>').join("")+'</tr>').join("")+'</tbody>';
      const details = (data.rule_details || []).map(d=>'<tr><td>'+escape(d.rule)+'</td><td>'+escape(d.sales_month)+'</td><td>'+escape(d.settlement_month)+' '+d.settlement_year+'</td><td>'+fmt(d.discount)+'</td></tr>').join("");
      const dialog = new frappe.ui.Dialog({
        title: __("Planned Sales & Collection - ") + data.year,
        size: "extra-large",
        fields: [{fieldtype:"HTML",fieldname:"preview"}],
      });
      dialog.fields_dict.preview.$wrapper.html('<div style="overflow:auto;max-height:65vh">'+warnings+
        '<p class="text-muted">'+__("Forecast only, no actual invoices or payments.")+' · '+escape(data.currency)+'</p>'+
        '<table class="table table-bordered table-sm">'+head+body+'</table>'+
        '<h5>'+__("Discount settlement breakdown")+'</h5>'+
        '<table class="table table-sm"><thead><tr><th>'+__("Rule")+'</th><th>'+__("Source Sales Period")+'</th><th>'+__("Settlement Period")+'</th><th>'+__("Amount")+'</th></tr></thead><tbody>'+details+'</tbody></table></div>');
      dialog.show();
    }
  });
}
