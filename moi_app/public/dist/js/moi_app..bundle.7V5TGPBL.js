(() => {
  // ../moi_app/moi_app/public/js/workflow_progress.js
  frappe.provide("workflow_progress");
  workflow_progress.bound = {};
  $(document).on("app_ready", function() {
    let booted = frappe.boot && frappe.boot.workflow_doctypes;
    if (booted && booted.length) {
      booted.forEach(bind_doctype);
      return;
    }
    frappe.call({
      method: "moi_app.utils.get_workflow_doctypes",
      callback: function(r) {
        (r.message || []).forEach(bind_doctype);
        catch_up_open_form(r.message || []);
      },
      error: function(err) {
        console.error("[workflow-progress] Could not list workflow DocTypes:", err);
      }
    });
  });
  function catch_up_open_form(doctypes) {
    let route = frappe.get_route ? frappe.get_route() : null;
    if (!route || route[0] !== "Form")
      return;
    let doctype = route[1];
    if (doctypes.indexOf(doctype) === -1)
      return;
    let view = frappe.views && frappe.views.formview && frappe.views.formview[doctype];
    let frm = view && view.frm;
    if (!frm || !frm.doc || frm.is_new())
      return;
    wf_debug("Catching up on already-open form", doctype);
    add_workflow_styles();
    load_workflow_graph(frm);
  }
  function bind_doctype(doctype) {
    if (workflow_progress.bound[doctype])
      return;
    workflow_progress.bound[doctype] = true;
    let handler = function(frm) {
      if (frm.is_new())
        return;
      add_workflow_styles();
      load_workflow_graph(frm);
    };
    frappe.ui.form.on(doctype, {
      refresh: handler,
      workflow_state: handler
    });
  }
  function wf_debug() {
    if (frappe.boot && frappe.boot.developer_mode) {
      console.log.apply(console, ["[workflow-progress]"].concat(Array.prototype.slice.call(arguments)));
    }
  }
  function wf_escape(value) {
    return frappe.utils.escape_html(String(value == null ? "" : value));
  }
  function wf_show_message(frm, message, indicator) {
    wf_paint(frm, `<div class="alert alert-${indicator}">${wf_escape(message)}</div>`);
  }
  function wf_paint(frm, html) {
    let field = wf_target_field(frm);
    if (field) {
      field.html(html);
      frm.refresh_field(field.df.fieldname);
      return field.$wrapper;
    }
    wf_debug("No HTML field found; falling back to dashboard");
    return insert_above_dashboard(frm, html);
  }
  function wf_target_field(frm) {
    let preferred = ["custom_progress_bar", "workflow_progress", "progress_bar"];
    for (let name of preferred) {
      if (frm.fields_dict[name])
        return frm.fields_dict[name];
    }
    for (let df of frm.meta.fields) {
      if (df.fieldtype === "HTML" && frm.fields_dict[df.fieldname]) {
        return frm.fields_dict[df.fieldname];
      }
    }
    return null;
  }
  function load_workflow_graph(frm) {
    frappe.call({
      method: "moi_app.utils.get_workflow_graph",
      args: { doctype: frm.doctype, docname: frm.doc.name },
      callback: function(r) {
        if (!r.message) {
          wf_debug("No active workflow for", frm.doctype);
          wf_paint(frm, "");
          return;
        }
        let graph = build_graph(r.message);
        if (!graph.nodes.length) {
          wf_show_message(frm, __("No workflow states configured"), "info");
          return;
        }
        let $wrapper = wf_paint(frm, render_graph(graph));
        if ($wrapper)
          draw_edges($wrapper, graph);
      },
      error: function(err) {
        console.error("[workflow-progress] Error loading workflow:", err);
        wf_show_message(frm, __("Could not load the workflow progress."), "danger");
      }
    });
  }
  var WF_STATE_BADGE = {
    completed: "Completed",
    current: "Under Review",
    paused: "Under Review",
    rejected: "Rejected",
    upcoming: null,
    unreachable: null
  };
  function build_graph(payload) {
    let order = {};
    payload.states.forEach(function(s) {
      order[s.name] = s.order;
    });
    let forward = [];
    let back = [];
    payload.transitions.forEach(function(t) {
      let edge = {
        from: t.from_state,
        to: t.to_state,
        action: t.action,
        allowed: t.allowed,
        condition: t.condition,
        satisfied: t.satisfied
      };
      if (order[t.to_state] > order[t.from_state]) {
        forward.push(edge);
      } else {
        back.push(edge);
      }
    });
    let depth = compute_depth(payload.states, forward, order);
    let reachable = compute_reachable(payload.current_state, forward.concat(back));
    let nodes = payload.states.map(function(s) {
      return {
        name: s.name,
        order: s.order,
        doc_status: s.doc_status,
        style: s.style,
        depth: depth[s.name] || 0,
        state: resolve_node_state(s, payload, reachable),
        meta: payload.history[s.name] || null
      };
    });
    let columns = [];
    nodes.forEach(function(n) {
      (columns[n.depth] = columns[n.depth] || []).push(n);
    });
    columns = columns.filter(Boolean);
    columns.forEach(function(col) {
      col.sort(function(a, b) {
        return a.order - b.order;
      });
    });
    return {
      workflow: payload.workflow,
      doctype: payload.doctype,
      current_state: payload.current_state,
      nodes,
      columns,
      forward,
      back,
      accent: accent_for(payload.current_state, nodes)
    };
  }
  function compute_depth(states, forward, order) {
    let depth = {};
    states.forEach(function(s) {
      depth[s.name] = 0;
    });
    let incoming = {};
    forward.forEach(function(e) {
      (incoming[e.to] = incoming[e.to] || []).push(e.from);
    });
    states.slice().sort(function(a, b) {
      return a.order - b.order;
    }).forEach(function(s) {
      (incoming[s.name] || []).forEach(function(from) {
        depth[s.name] = Math.max(depth[s.name], depth[from] + 1);
      });
    });
    return depth;
  }
  function compute_reachable(current_state, edges) {
    let reachable = {};
    if (!current_state)
      return reachable;
    let adjacency = {};
    edges.forEach(function(e) {
      (adjacency[e.from] = adjacency[e.from] || []).push(e.to);
    });
    let queue = [current_state];
    reachable[current_state] = true;
    while (queue.length) {
      let node = queue.shift();
      (adjacency[node] || []).forEach(function(next) {
        if (!reachable[next]) {
          reachable[next] = true;
          queue.push(next);
        }
      });
    }
    return reachable;
  }
  function resolve_node_state(state, payload, reachable) {
    let name = state.name;
    let style = (state.style || "").toLowerCase();
    let key = name.toLowerCase();
    let is_rejection = style === "danger" || state.doc_status === 2 || key.includes("reject") || key.includes("cancel");
    let is_hold = style === "warning" || key.includes("hold") || key.includes("pause");
    if (name === payload.current_state) {
      if (is_rejection)
        return "rejected";
      if (is_hold)
        return "paused";
      let has_exit = payload.transitions.some(function(t) {
        return t.from_state === name;
      });
      return has_exit ? "current" : "completed";
    }
    if (payload.history[name])
      return "completed";
    if (reachable[name])
      return "upcoming";
    return "unreachable";
  }
  function accent_for(current_state, nodes) {
    let node = nodes.filter(function(n) {
      return n.name === current_state;
    })[0];
    return node ? node.state : "upcoming";
  }
  var WF_ICON_PATHS = {
    check: '<path d="M20 6 9 17l-5-5"/>',
    pause: '<rect x="14" y="4" width="4" height="16" rx="1"/><rect x="6" y="4" width="4" height="16" rx="1"/>',
    close: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    user: '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    calendar: '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/>'
  };
  function wf_icon(name, size, stroke) {
    return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${stroke}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${WF_ICON_PATHS[name]}</svg>`;
  }
  function wf_node_glyph(step_state, number) {
    if (step_state === "completed")
      return wf_icon("check", 18, 2.5);
    if (step_state === "rejected")
      return wf_icon("close", 18, 2.5);
    if (step_state === "current" || step_state === "paused")
      return wf_icon("pause", 18, 2.5);
    return `<span class="wf-step-number">${number}</span>`;
  }
  function wf_meta_block(meta, elevate) {
    if (!meta)
      return "";
    let who = meta.user ? frappe.user.full_name(meta.user) || meta.user : __("Unassigned");
    let when = meta.on ? frappe.datetime.str_to_user(meta.on) : __("Pending");
    return `
        <div class="wf-step-meta${elevate ? " is-elevated" : ""}">
            <div class="wf-meta-row">${wf_icon("user", 12, 2)}<span>${wf_escape(who)}</span></div>
            <div class="wf-meta-row">${wf_icon("calendar", 12, 2)}<span>${wf_escape(when)}</span></div>
        </div>
    `;
  }
  function render_graph(graph) {
    let html = `
        <div class="workflow-progress-container is-${graph.accent}">
            <div class="workflow-header">
                <div class="workflow-header-text">
                    <div class="workflow-title">${__("Workflow Progress")}</div>
                </div>
            </div>
            <div class="workflow-steps-container">
                <div class="workflow-graph">
                    <svg class="wf-edges" aria-hidden="true"></svg>
    `;
    graph.columns.forEach(function(column, col_index) {
      html += `<div class="wf-column">`;
      column.forEach(function(node) {
        html += render_node(node, col_index);
      });
      html += `</div>`;
    });
    html += `
                </div>
            </div>
        </div>
    `;
    return html;
  }
  function render_node(node, col_index) {
    let badge_label = WF_STATE_BADGE[node.state];
    let is_alert = node.state === "paused" || node.state === "rejected";
    let elevate = node.state === "current" || node.state === "paused";
    let ring = node.state === "current" || is_alert ? '<span class="wf-step-ring"></span>' : "";
    let badge = badge_label ? `<span class="wf-step-badge${is_alert ? " is-alert" : ""}">${__(badge_label)}</span>` : "";
    return `
        <div class="workflow-step is-${node.state}" style="--i:${col_index}" data-state="${wf_escape(node.name)}">
            <div class="wf-step-indicator">
                ${ring}
                <div class="wf-step-node">${wf_node_glyph(node.state, node.order + 1)}</div>
            </div>
            <div class="wf-step-title">${__(node.name)}</div>
            ${badge}
            ${wf_meta_block(node.meta, elevate)}
        </div>
    `;
  }
  var WF_EDGE_COLOR = {
    completed: "#10B981",
    current: "#F59E0B",
    paused: "#F59E0B",
    rejected: "#EF4444",
    upcoming: "#E5E7EB",
    unreachable: "#F3F4F6"
  };
  function draw_edges($wrapper, graph) {
    let $graph = $wrapper.find(".workflow-graph");
    let $svg = $graph.find("svg.wf-edges");
    if (!$graph.length || !$svg.length)
      return;
    let origin = $graph[0].getBoundingClientRect();
    let anchors = {};
    $graph.find(".workflow-step").each(function() {
      let name = $(this).attr("data-state");
      let node = $(this).find(".wf-step-node")[0];
      if (!node)
        return;
      let box = node.getBoundingClientRect();
      anchors[name] = {
        left: box.left - origin.left,
        right: box.right - origin.left,
        top: box.top - origin.top,
        bottom: box.bottom - origin.top,
        cx: box.left - origin.left + box.width / 2,
        cy: box.top - origin.top + box.height / 2
      };
    });
    let node_state = {};
    graph.nodes.forEach(function(n) {
      node_state[n.name] = n.state;
    });
    let paths = [];
    graph.forward.forEach(function(edge) {
      let a = anchors[edge.from];
      let b = anchors[edge.to];
      if (!a || !b)
        return;
      let dx = Math.max(24, (b.left - a.right) * 0.5);
      let d = `M ${a.right} ${a.cy} C ${a.right + dx} ${a.cy}, ${b.left - dx} ${b.cy}, ${b.left} ${b.cy}`;
      paths.push(edge_path(d, node_state[edge.from], edge, false));
    });
    graph.back.forEach(function(edge) {
      let a = anchors[edge.from];
      let b = anchors[edge.to];
      if (!a || !b)
        return;
      let drop = Math.max(a.bottom, b.bottom) + 26;
      let d = `M ${a.cx} ${a.bottom} C ${a.cx} ${drop}, ${b.cx} ${drop}, ${b.cx} ${b.bottom}`;
      paths.push(edge_path(d, node_state[edge.from], edge, true));
    });
    let width = $graph[0].scrollWidth;
    let height = $graph[0].scrollHeight;
    $svg.attr("viewBox", `0 0 ${width} ${height}`).attr("width", width).attr("height", height).html(paths.join(""));
  }
  function edge_path(d, from_state, edge, is_back) {
    let color = WF_EDGE_COLOR[from_state] || WF_EDGE_COLOR.upcoming;
    let dashed = is_back || edge.satisfied === false;
    let title = edge.action ? `<title>${wf_escape(edge.action)}</title>` : "";
    return `<path d="${d}" fill="none" stroke="${color}" stroke-width="3" stroke-linecap="round"${dashed ? ' stroke-dasharray="6 6"' : ""}>${title}</path>`;
  }
  function add_workflow_styles() {
    if ($("#workflow-figma-styles").length)
      return;
    $("#workflow-custom-styles").remove();
    let styles = `
        <style id="workflow-figma-styles">
            /* ------------------------------------------------------------------
               Workflow Stepper \u2014 tokens from the "ERP Designs" Figma component set
               (Workflow / Stepper Node + Workflow / Progress Bar).
               Every rule is scoped to .workflow-progress-container so nothing
               leaks into Frappe's own .progress / .badge styles.
               ------------------------------------------------------------------ */

            .workflow-progress-container {
                --wf-neutral-line: #E5E7EB;
                --wf-text-primary: #111827;
                --wf-text-muted: #6B7280;

                padding: 24px;
                background: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
                box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
                margin: 15px 0;
            }

            /* ---- Header ---- */

            .workflow-progress-container .workflow-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 16px;
                flex-wrap: wrap;
                margin-bottom: 20px;
            }

            .workflow-progress-container .workflow-title {
                margin: 0;
                font-size: 16px;
                font-weight: 600;
                line-height: 1.4;
                color: var(--wf-text-primary);
            }

            /* ---- Graph rail ---- */

            .workflow-progress-container .workflow-steps-container {
                overflow-x: auto;
                padding-bottom: 8px;
            }

            /* Columns are laid out left to right; branches stack within a column. */
            .workflow-progress-container .workflow-graph {
                position: relative;
                display: flex;
                align-items: flex-start;
                gap: 56px;
                min-width: max-content;
                padding: 0 8px 34px;
            }

            .workflow-progress-container .wf-column {
                display: flex;
                flex-direction: column;
                gap: 24px;
            }

            /* Edges sit behind the nodes and never intercept clicks. */
            .workflow-progress-container .wf-edges {
                position: absolute;
                left: 0;
                top: 0;
                pointer-events: none;
                overflow: visible;
                z-index: 0;
            }

            /* ---- Step node ---- */

            .workflow-progress-container .workflow-step {
                --wf-node: #FFFFFF;
                --wf-border: #D1D5DB;
                --wf-fg: #9CA3AF;
                --wf-ring: transparent;
                --wf-badge-bg: transparent;
                --wf-badge-fg: #9CA3AF;

                position: relative;
                z-index: 1;
                display: flex;
                flex-direction: column;
                align-items: center;
                text-align: center;
                gap: 8px;
                width: 160px;
                flex: 0 0 160px;
            }

            .workflow-progress-container .workflow-step.is-completed {
                --wf-node: #10B981;
                --wf-border: #10B981;
                --wf-fg: #FFFFFF;
                --wf-ring: rgba(16, 185, 129, 0.25);
                --wf-badge-bg: #D1FAE5;
                --wf-badge-fg: #065F46;
            }

            .workflow-progress-container .workflow-step.is-current,
            .workflow-progress-container .workflow-step.is-paused {
                --wf-node: #F59E0B;
                --wf-border: #F59E0B;
                --wf-fg: #FFFFFF;
                --wf-ring: rgba(245, 158, 11, 0.3);
                --wf-badge-bg: #FEF3C7;
                --wf-badge-fg: #92400E;
            }

            .workflow-progress-container .workflow-step.is-rejected {
                --wf-node: #EF4444;
                --wf-border: #EF4444;
                --wf-fg: #FFFFFF;
                --wf-ring: rgba(239, 68, 68, 0.3);
                --wf-badge-bg: #FEE2E2;
                --wf-badge-fg: #991B1B;
            }

            /* A branch the document can no longer reach \u2014 present, but muted. */
            .workflow-progress-container .workflow-step.is-unreachable {
                --wf-border: #E5E7EB;
                --wf-fg: #D1D5DB;
                opacity: 0.55;
            }

            .workflow-progress-container .wf-step-indicator {
                position: relative;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 44px;
            }

            .workflow-progress-container .wf-step-ring {
                position: absolute;
                width: 52px;
                height: 52px;
                border-radius: 999px;
                background: var(--wf-ring);
                animation: wf-ring-pulse 2.4s ease-in-out infinite;
            }

            .workflow-progress-container .wf-step-node {
                position: relative;
                display: flex;
                align-items: center;
                justify-content: center;
                width: 40px;
                height: 40px;
                border-radius: 999px;
                background: var(--wf-node);
                border: 2px solid var(--wf-border);
                color: var(--wf-fg);
                animation: wf-node-appear 0.45s ease-out backwards;
                animation-delay: calc(var(--i, 0) * 0.35s);
            }

            .workflow-progress-container .workflow-step.is-paused .wf-step-node,
            .workflow-progress-container .workflow-step.is-rejected .wf-step-node {
                animation-name: wf-node-shake;
            }

            .workflow-progress-container .wf-step-number {
                font-size: 15px;
                font-weight: 600;
                line-height: 1;
                color: var(--wf-fg);
            }

            .workflow-progress-container .wf-step-title {
                font-size: 14px;
                font-weight: 600;
                line-height: 1.4;
                color: var(--wf-text-primary);
            }

            .workflow-progress-container .workflow-step.is-unreachable .wf-step-title {
                color: var(--wf-text-muted);
            }

            /* ---- Badge ---- */

            .workflow-progress-container .wf-step-badge {
                display: inline-block;
                font-size: 12px;
                font-weight: 500;
                line-height: 1.5;
                padding: 2px 8px;
                border-radius: 4px;
                background: var(--wf-badge-bg);
                color: var(--wf-badge-fg);
                animation: wf-badge-fade 0.3s ease-out backwards;
                animation-delay: calc(var(--i, 0) * 0.35s + 0.1s);
            }

            .workflow-progress-container .wf-step-badge.is-alert {
                animation-name: wf-badge-pop;
                animation-timing-function: cubic-bezier(0.34, 1.56, 0.64, 1);
                animation-delay: calc(var(--i, 0) * 0.35s + 0.15s);
            }

            /* ---- Metadata block ---- */

            .workflow-progress-container .wf-step-meta {
                margin-top: 4px;
                width: 100%;
                display: flex;
                flex-direction: column;
                gap: 4px;
                padding: 8px 10px;
                border-radius: 8px;
                background: transparent;
                border: 1px solid transparent;
            }

            .workflow-progress-container .wf-step-meta.is-elevated {
                background: #F9FAFB;
                border-color: #F3F4F6;
            }

            .workflow-progress-container .wf-meta-row {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                font-size: 12px;
                font-weight: 400;
                line-height: 1.4;
                color: var(--wf-text-muted);
            }

            .workflow-progress-container .wf-meta-row svg {
                flex: 0 0 auto;
            }

            /* ---- Animations ---- */

            @keyframes wf-ring-pulse {
                0%, 100% { opacity: 0.9; transform: scale(1); }
                50% { opacity: 0.35; transform: scale(1.1); }
            }

            @keyframes wf-node-appear {
                0% { transform: scale(0.8); opacity: 0; }
                70% { transform: scale(1.05); opacity: 1; }
                100% { transform: scale(1); opacity: 1; }
            }

            @keyframes wf-node-shake {
                0% { transform: translateX(0); opacity: 0; }
                20% { transform: translateX(-4px); opacity: 1; }
                40% { transform: translateX(4px); }
                60% { transform: translateX(-3px); }
                80% { transform: translateX(3px); }
                100% { transform: translateX(0); opacity: 1; }
            }

            @keyframes wf-badge-fade {
                from { opacity: 0; }
                to { opacity: 1; }
            }

            @keyframes wf-badge-pop {
                0% { transform: scale(0); }
                60% { transform: scale(1.15); }
                100% { transform: scale(1); }
            }

            /* ---- Responsive ---- */
            @media (max-width: 768px) {
                .workflow-progress-container {
                    padding: 16px;
                }
                .workflow-progress-container .workflow-graph {
                    gap: 40px;
                }
                .workflow-progress-container .workflow-step {
                    width: 132px;
                    flex: 0 0 132px;
                }
            }

            @media (prefers-reduced-motion: reduce) {
                .workflow-progress-container .wf-step-ring,
                .workflow-progress-container .wf-step-node,
                .workflow-progress-container .wf-step-badge {
                    animation: none;
                }
            }
        </style>
    `;
    $("head").append(styles);
  }
  function insert_above_dashboard(frm, html) {
    $("#custom-above-dashboard-wrapper").remove();
    var $dashboard = $(".form-dashboard");
    if ($dashboard.length === 0)
      $dashboard = $(".form-dashboard-section");
    if ($dashboard.length === 0)
      $dashboard = $(".dashboard-section");
    if ($dashboard.length === 0)
      $dashboard = $(".form-dashboard-wrapper");
    var $content = $('<div id="custom-above-dashboard-wrapper">').append($(html));
    if ($dashboard.length > 0) {
      $dashboard.before($content);
      wf_debug("Content inserted before dashboard");
    } else {
      var $lastSection = $(".section-break").last();
      if ($lastSection.length > 0) {
        $lastSection.after($content);
        wf_debug("Content inserted after last section");
      } else {
        $(".form-body").append($content);
        wf_debug("Content appended to form body");
      }
    }
    return $content;
  }
})();
//# sourceMappingURL=moi_app..bundle.7V5TGPBL.js.map
