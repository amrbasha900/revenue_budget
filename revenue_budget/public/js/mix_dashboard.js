// Shared Frappe v15 dashboard for both standard Script Reports.
// Uses report filters and a server-side active-only aggregate. No additional dependencies.
frappe.provide("revenue_budget");

revenue_budget.mix_dashboard = {
  setup(report) {
    const host = report.$report;
    if (!host || !host.length) return;
    let panel = report.page.main.find(".rb-mix-dashboard");
    if (!panel.length) {
      panel = $(`<section class="rb-mix-dashboard" style="margin:14px 0 22px">
        <div class="rb-mix-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:12px;margin-bottom:14px"></div>
        <div class="rb-mix-charts" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px">
          <div class="rb-card"><h5 class="rb-title"></h5><div class="rb-chart rb-chart-groups"></div></div>
          <div class="rb-card"><h5 class="rb-title"></h5><div class="rb-chart rb-chart-months"></div></div>
          <div class="rb-card"><h5 class="rb-title"></h5><div class="rb-chart rb-chart-stack"></div></div>
          <div class="rb-card"><h5 class="rb-title"></h5><div class="rb-chart rb-chart-share"></div></div>
        </div>
      </section>`);
      panel.find(".rb-card").css({background:"var(--card-bg, var(--fg-color))",border:"1px solid var(--border-color)",borderRadius:"9px",padding:"14px",minWidth:0});
      panel.find(".rb-title").css({fontWeight:600,marginBottom:"12px"});
    }
    panel.insertBefore(host);
    report._rb_mix_panel = panel;
  },

  refresh(report) {
    if (!report || !report.get_filter_values) return;
    this.setup(report);
    const panel = report._rb_mix_panel;
    const filters = report.get_filter_values();
    // Every refresh gets a generation so slower callbacks cannot overwrite newer filters.
    const generation = (report._rb_mix_generation || 0) + 1;
    report._rb_mix_generation = generation;
    if (!filters.fiscal_year || !filters.company) {
      panel.find(".rb-mix-kpis").html('<div class="text-muted">' + __("Select Fiscal Year and Company to show dashboard") + "</div>");
      panel.find(".rb-chart").empty();
      return;
    }
    panel.find(".rb-mix-kpis").html('<div class="text-muted">' + __("Loading dashboard...") + "</div>");
    frappe.call({
      method:"revenue_budget.revenue_budget.report.mix_dashboard.get_dashboard",
      args:{filters:filters},
      callback: (r) => {
        if (generation !== report._rb_mix_generation) return;
        if (frappe.query_report !== report) return;
        const data = r.message;
        if (!data) return;
        this.render(report, data);
      },
      error: () => {
        if (generation === report._rb_mix_generation) {
          panel.find(".rb-mix-kpis").text(__("Dashboard could not be loaded"));
          panel.find(".rb-chart").empty();
        }
      }
    });
  },

  render(report, data) {
    const panel = report._rb_mix_panel;
    if (!panel) return;
    const safe = (value) => frappe.utils.escape_html(String(value ?? ""));
    const fmt = (num) => frappe.format(Number(num || 0), {fieldtype:"Float", precision:2});
    const kpis = [
      [__(data.is_percent ? "Selected Net Revenue (Base)" : (data.value_mode + " (Base)")), fmt(data.total)],
      [__("Customers"), data.customer_count],
      [__("Items"), data.item_count],
      [data.group_label + " · " + __("Groups"), data.group_count]
    ];
    panel.find(".rb-mix-kpis").html(kpis.map(([name, value]) =>
      `<div style="padding:13px 16px;border:1px solid var(--border-color);border-radius:9px;background:var(--card-bg, var(--fg-color))">
        <div class="text-muted small">${safe(name)}</div><div style="font-size:22px;font-weight:700;margin-top:6px">${safe(value)}</div></div>`
    ).join(""));
    const titles = [
      __(data.is_percent ? "Customer Mix % by" : "Annual Revenue by") + " " + data.group_label,
      __(data.is_percent ? "Monthly Customer Mix %" : "Monthly Revenue Trend"),
      __(data.is_percent ? "Monthly Customer Mix % by" : "Monthly Revenue by") + " " + data.group_label,
      __(data.is_percent ? "Annual Customer Mix % by" : "Annual Revenue Share by") + " " + data.group_label
    ];
    panel.find(".rb-title").each((idx, element) => $(element).text(titles[idx]));
    const targets = ["groups","months","stack","share"];
    const chartNodes = targets.map(key => panel.find(".rb-chart-"+key).empty()[0]);
    if (!data.groups.length || data.is_empty) {
      panel.find(".rb-chart").text(__("No data for selected filters"));
      return;
    }
    if (typeof frappe.Chart !== "function") {
      panel.find(".rb-chart").text(__("Chart library is unavailable"));
      return;
    }
    const groupLabels = data.groups.map(g => g.name);
    const groupValues = data.groups.map(g => g.value);
    const monthLabels = data.months;
    // Always create one bar per distinct group, regardless of whether the
    // chosen grouping is category, item group, or a nested hierarchy.
    const charts = [
      {type:"bar",height:280,data:{labels:groupLabels,datasets:[{name:__("Net Revenue"),values:groupValues}]}},
      {type:"line",height:280,data:{labels:monthLabels,datasets:[{name:__("Net Revenue"),values:data.monthly_totals}]}},
      {type:"bar",height:280,data:{labels:monthLabels,datasets:data.group_monthly.map(g=>({name:g.name,values:g.values}))},barOptions:{stacked:true}},
      {type:"pie",height:280,data:{labels:groupLabels,datasets:[{values:groupValues}]}}
    ];
    charts.forEach((options, i) => {
      try { new frappe.Chart(chartNodes[i], options); }
      catch (error) {
        console.error("Revenue Budget dashboard chart", error);
        $(chartNodes[i]).text(__("Unable to render chart"));
      }
    });
  }
};
