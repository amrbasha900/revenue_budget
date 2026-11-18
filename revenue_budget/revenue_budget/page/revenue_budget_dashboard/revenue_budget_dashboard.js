/* Revenue Budget executive dashboard (Frappe Desk v15). No external libraries. */
frappe.pages["revenue-budget-dashboard"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper, title: __("Revenue Budget Dashboard"), single_column: true
  });
  page.main.html(`
    <style>
      .rbd{--rbd-accent:#3164d2;--rbd-muted:var(--text-muted);padding:16px 4px 30px}
      .rbd *{box-sizing:border-box}
      .rbd-hero{background:linear-gradient(120deg,#182847,#27528a);border-radius:17px;color:white;padding:24px 28px;display:flex;justify-content:space-between;align-items:center;gap:18px;flex-wrap:wrap;margin-bottom:20px}
      .rbd-hero h2{font-weight:750;font-size:25px;color:white;margin:0 0 6px}
      .rbd-hero p{color:#dbeafe;margin:0;font-size:13px}
      .rbd-tag{padding:7px 11px;border-radius:999px;background:#ffffff24;color:white;font-size:12px;font-weight:600}
      .rbd-filters{display:grid;grid-template-columns:repeat(auto-fit,minmax(185px,1fr));gap:12px;padding:18px;margin:0 0 20px;background:var(--card-bg,var(--fg-color));border:1px solid var(--border-color);border-radius:13px;align-items:end}
      .rbd-filter{min-width:0}.rbd-filter .form-group{margin-bottom:0}.rbd-filter .control-label{font-size:12px;font-weight:600}
      .rbd-summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:18px}
      .rbd-card,.rbd-panel{background:var(--card-bg,var(--fg-color));border:1px solid var(--border-color);border-radius:13px;min-width:0}
      .rbd-card{padding:17px;min-height:118px;display:flex;flex-direction:column;gap:6px;overflow:hidden}
      .rbd-label{font-size:12px;color:var(--text-muted);line-height:1.5}
      .rbd-val{font-size:clamp(17px,1.5vw,23px);line-height:1.3;font-weight:750;overflow-wrap:break-word;word-break:normal;font-variant-numeric:tabular-nums}.rbd-val.rbd-num{white-space:normal;direction:ltr;text-align:start}.rbd-card small{display:block;overflow-wrap:anywhere;line-height:1.45}
      .rbd-card small{font-size:11px;color:var(--text-muted)}
      .rbd-panels{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
      .rbd-panel{padding:19px;overflow:hidden}
      .rbd-panel h4{font-size:15px;font-weight:700;margin:0 0 15px}
      .rbd-panel.wide{grid-column:span 2}
      .rbd-chart{min-height:260px}
      .rbd-rank{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:center;margin:13px 0}
      .rbd-rank-title{display:block;font-weight:600;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
      .rbd-rank-sub{display:block;color:var(--text-muted);font-size:11px}
      .rbd-rank-value{text-align:end;font-size:12px;font-weight:700}
      .rbd-progress{height:5px;border-radius:5px;background:var(--border-color);margin-top:6px;overflow:hidden}
      .rbd-progress>span{display:block;height:100%;background:var(--rbd-accent);border-radius:5px}
      .rbd-empty{padding:65px 20px;text-align:center;color:var(--text-muted)}
      @media(max-width:850px){.rbd-panels{grid-template-columns:1fr}.rbd-panel.wide{grid-column:span 1}.rbd-hero{padding:18px}}
    </style>
    <div class="rbd">
      <div class="rbd-hero">
        <div><h2>${__("Revenue Performance Overview")}</h2>
        <p>${__("Planned budgets only · Submitted active versions · After-discount rankings")}</p></div>
        <span class="rbd-tag">${__("Budget Intelligence")}</span>
      </div>
      <div class="rbd-filters" aria-label="Revenue Budget Filters"></div>
      <div class="rbd-body"><div class="rbd-empty">${__("Select company and fiscal year to view the dashboard")}</div></div>
    </div>`);
  const root = page.main.find(".rbd");
  const fields = {};
  const definitions = [
    ["company", "Company", "Link", "Company", true],
    ["fiscal_year", "Fiscal Year", "Link", "Fiscal Year", true],
    ["customer_category", "Customer Category", "Link", "Revenue Budget Customer Category"],
    ["customer", "Customer", "Link", "Customer"],
    ["item_group", "Item Group", "Link", "Item Group"],
    ["budget_month", "Month", "Select", "January\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember"]
  ];
  let generation = 0;
  let refreshTimer;
  // Render filters explicitly in the dashboard body. The Desk toolbar
  // can collapse or hide page.add_field controls depending on the layout.
  const filterHost = root.find(".rbd-filters");
  let initializing = true;
  definitions.forEach(([fieldname, label, fieldtype, options, reqd]) => {
    const container = $('<div class="rbd-filter"></div>').appendTo(filterHost);
    fields[fieldname] = frappe.ui.form.make_control({
      parent: container,
      df: {
        fieldname, label: __(label), fieldtype, options, reqd: !!reqd,
        change: () => {
          if (initializing) return;
          clearTimeout(refreshTimer);
          refreshTimer = setTimeout(load, 220);
        }
      },
      render_input: true
    });
  });
  // Choose a sensible initial company, then the matching fiscal year.
  const defaultCompany = frappe.defaults.get_user_default("Company");
  const defaultFiscalYear = frappe.defaults.get_user_default("fiscal_year");
  if (defaultCompany) fields.company.set_value(defaultCompany);
  if (defaultFiscalYear) fields.fiscal_year.set_value(defaultFiscalYear);
  initializing = false;
  if (defaultCompany && defaultFiscalYear) setTimeout(load, 0);
  const escape = value => frappe.utils.escape_html(String(value ?? ""));
  // frappe.format returns markup (e.g. numeric alignment divs); never embed it in a KPI value.\n  const numberFormatter = precision => new Intl.NumberFormat("en-US", {minimumFractionDigits:precision,maximumFractionDigits:precision});\n  const format = (value, precision=0) => numberFormatter(precision).format(Number(value || 0));
  const money = (value, currency) => format(value, 2) + (currency ? " " + escape(currency) : "");
  const card = (label, value, subtitle="", numeric=false) => `<div class="rbd-card">
    <div class="rbd-label">${escape(label)}</div><div class="rbd-val ${numeric ? "rbd-num" : ""}" title="${escape(String(value).replace(/<[^>]*>/g, ""))}">${value}</div>
    <small>${escape(subtitle)}</small></div>`;
  const panel = (title, body, wide=false) => `<section class="rbd-panel ${wide?"wide":""}">
    <h4>${escape(title)}</h4>${body}</section>`;

  function rank(items, numeric, currency, max, isQty=false) {
    if (!items.length) return `<div class="rbd-empty">${__("No results")}</div>`;
    return items.map((item, index) => {
      const name = item.name || item.label || item.code;
      const value = Number(item[numeric] || 0);
      const display = isQty
        ? format(value, 2) + " " + escape(item.uom || "")
        : money(value, currency);
      const fraction = max > 0 ? Math.max(0, value/max*100) : 0;
      return `<div class="rbd-rank">
        <div><span class="rbd-rank-title">${index+1}. ${escape(name)}</span>
          <span class="rbd-rank-sub">${escape(item.code || "")}</span>
          <div class="rbd-progress"><span style="width:${Math.min(100,fraction)}%"></span></div>
        </div><div class="rbd-rank-value">${display}</div>
      </div>`;
    }).join("");
  }
  function createChart(selector, opts) {
    const target = root.find(selector)[0];
    if (!target) return;
    if (typeof frappe.Chart !== "function") {
      $(target).text(__("Charts unavailable")); return;
    }
    try {new frappe.Chart(target, opts);}
    catch (err) {console.error("Revenue Budget chart",err);$(target).text(__("Chart could not load"));}
  }
  function render(data) {
    const cur = data.currency;
    const customer = data.top_customer;
    const qty = data.top_item_qty;
    const value = data.top_item_value;
    const best = data.best_month;
    const topGroup = data.item_groups[0];
    const kpis = [
      card(__("Planned Net Revenue"), money(data.net,cur), __("After discount"), true),
      card(__("Planned Gross Revenue"), money(data.gross,cur), __("Before discount"), true),
      card(__("Planned Discount"), money(data.discount,cur), format(data.discount_rate,1)+"%", true),
      card(__("Active Budgets"), format(data.budget_count), __("Current versions only"), true),
      card(__("Customers"), format(data.customer_count), "", true),
      card(__("Items"), format(data.item_count), "", true),
      card(__("Top Customer"), customer?escape(customer.label):"—", customer?money(customer.net,cur):""),
      card(__("Top Item by Value"), value?escape(value.name):"—", value?money(value.net,cur):""),
      card(__("Top Item by Quantity"), qty?escape(qty.name):"—", qty?format(qty.qty,2)+" "+escape(qty.uom):""),
      card(__("Best Month"), best?escape(best.month):"—", best?money(best.value,cur):""),
      card(__("Top 5 Customers Share"), format(data.top_5_share,1)+"%", __("Revenue concentration"), true),
      card(__("Leading Item Group"), topGroup?escape(topGroup.name):"—", topGroup?money(topGroup.value,cur):"")
    ].join("");
    const topCustomerMax = data.top_customers[0]?.net || 0;
    const topQtyMax = data.top_items_qty[0]?.qty || 0;
    const topValueMax = data.top_items_value[0]?.net || 0;
    root.find(".rbd-body").html(`
      <div class="rbd-summary">${kpis}</div>
      <div class="rbd-panels">
        ${panel(__("Monthly Revenue: Gross vs Net"),'<div class="rbd-chart rbd-monthly"></div>',true)}
        ${panel(__("Top Customers by Net Revenue"),'<div class="rbd-chart rbd-customers-chart"></div>')}
        ${panel(__("Item Groups by Net Revenue"),'<div class="rbd-chart rbd-groups-chart"></div>')}
        ${panel(__("Top Items by Planned Quantity"),rank(data.top_items_qty,"qty",cur,topQtyMax,true))}
        ${panel(__("Top Items by Planned Net Value"),rank(data.top_items_value,"net",cur,topValueMax))}
        ${panel(__("Top 10 Customers"),rank(data.top_customers,"net",cur,topCustomerMax),true)}
      </div>`);
    if (!data.budget_count) {
      root.find(".rbd-panels").html('<div class="rbd-empty">' + __("No active submitted budgets match the selected filters") + '</div>');
      return;
    }
    createChart(".rbd-monthly",{
      type:"bar",height:280,data:{labels:data.months,datasets:[
        {name:__("Before Discount"),values:data.monthly_gross},
        {name:__("After Discount"),values:data.monthly_net}
      ]}
    });
    createChart(".rbd-customers-chart",{
      type:"bar",height:280,
      data:{labels:data.top_customers.slice(0,7).map(x=>x.code),
        datasets:[{name:__("Planned Net"),values:data.top_customers.slice(0,7).map(x=>x.net)}]}
    });
    const topGroups = data.item_groups.slice(0,8);
    createChart(".rbd-groups-chart",{
      type:"bar",height:280,
      data:{labels:topGroups.map(x=>x.name),datasets:[{name:__("Planned Net"),values:topGroups.map(x=>x.value)}]}
    });
  }
  function load() {
    const args = {};
    for (const [key, control] of Object.entries(fields)) args[key] = control.get_value() || null;
    const requestId = ++generation;
    if (!args.company || !args.fiscal_year) {
      root.find(".rbd-body").html(`<div class="rbd-empty">${__("Select company and fiscal year to view the dashboard")}</div>`);
      return;
    }
    root.find(".rbd-body").html(`<div class="rbd-empty">${__("Loading dashboard...")}</div>`);
    frappe.call({
      method:"revenue_budget.dashboard.get_dashboard",args,
      callback: response => {
        if (requestId!==generation) return;
        if (response.message) render(response.message);
      },
      error: () => {
        if (requestId===generation) root.find(".rbd-body").html(`<div class="rbd-empty">${__("Unable to load dashboard")}</div>`);
      }
    });
  }
  page.set_primary_action(__("Refresh"), load, "refresh");
  // Clear pending delayed refreshes when a user immediately chooses a page action.
  $(wrapper).on("remove", () => {clearTimeout(refreshTimer);++generation;});
};