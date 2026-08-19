/**
 * Workflow progress bar.
 *
 * Renders any active Frappe Workflow as a layered graph: every state and every
 * transition is drawn, so branches ("Approve" vs "Reject"), merges and
 * loop-backs are all visible — not just one flattened path.
 *
 * Visual tokens come from the "ERP Designs" Figma component set
 * (Workflow / Stepper Node + Workflow / Progress Bar).
 */

frappe.provide('workflow_progress');

// ---------------------------------------------------------------------------
// Registration — bind to every DocType that has an active workflow
// ---------------------------------------------------------------------------

// Both maps survive a second evaluation of this file. Reassigning them would
// wipe the guard below, re-register every form handler, and render twice.
workflow_progress.bound = workflow_progress.bound || {};
workflow_progress.render_token = workflow_progress.render_token || {};

$(document).on('app_ready', function () {
    // Preferred: the list ships in boot, so binding happens before any form
    // renders. Add this to your hooks.py to enable it:
    //
    //   extend_bootinfo = "moi_app.utils.boot_workflow_doctypes"
    //
    //   def boot_workflow_doctypes(bootinfo):
    //       bootinfo.workflow_doctypes = get_workflow_doctypes()
    let booted = frappe.boot && frappe.boot.workflow_doctypes;
    if (booted && booted.length) {
        booted.forEach(bind_doctype);
        return;
    }

    // Fallback: fetch the list. This races the form's own load, so any form
    // already on screen is re-rendered once binding completes.
    frappe.call({
        method: 'moi_app.utils.get_workflow_doctypes',
        callback: function (r) {
            (r.message || []).forEach(bind_doctype);
            catch_up_open_form(r.message || []);
        },
        error: function (err) {
            console.error('[workflow-progress] Could not list workflow DocTypes:', err);
        }
    });
});

/**
 * Render into a form that opened before its handler was bound.
 *
 * Best effort and fully guarded: if the form cannot be located the handler
 * still fires on the next refresh, so nothing is permanently lost.
 */
function catch_up_open_form(doctypes) {
    let route = frappe.get_route ? frappe.get_route() : null;
    if (!route || route[0] !== 'Form') return;

    let doctype = route[1];
    if (doctypes.indexOf(doctype) === -1) return;

    let view = frappe.views && frappe.views.formview && frappe.views.formview[doctype];
    let frm = view && view.frm;
    if (!frm || !frm.doc || frm.is_new()) return;

    wf_debug('Catching up on already-open form', doctype);
    add_workflow_styles();
    load_workflow_graph(frm);
}

function bind_doctype(doctype) {
    if (workflow_progress.bound[doctype]) return;
    workflow_progress.bound[doctype] = true;

    let handler = function (frm) {
        if (frm.is_new()) return;
        add_workflow_styles();
        load_workflow_graph(frm);
    };

    frappe.ui.form.on(doctype, {
        refresh: handler,
        // Re-render as soon as the state changes, without waiting for a reload.
        workflow_state: handler
    });
}

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------

// Diagnostics stay out of the production console; they only surface in dev mode.
function wf_debug() {
    if (frappe.boot && frappe.boot.developer_mode) {
        console.log.apply(console, ['[workflow-progress]'].concat(Array.prototype.slice.call(arguments)));
    }
}

function wf_escape(value) {
    return frappe.utils.escape_html(String(value == null ? '' : value));
}

// Renders a message into the progress bar field.
function wf_show_message(frm, message, indicator) {
    wf_paint(frm, `<div class="alert alert-${indicator}">${wf_escape(message)}</div>`);
}

// Writes html into the target field, falling back to the dashboard area.
function wf_paint(frm, html) {
    // Clear every earlier render before drawing. Class selectors remove *all*
    // matches, unlike the id selector this replaced, which removed only the
    // first and so let duplicates accumulate. Both placements are cleared: a
    // form can fall back to the dashboard on one render and find its HTML field
    // on the next, and the stale copy would otherwise stay on screen.
    $('.wf-injected, .workflow-progress-container').remove();

    let field = wf_target_field(frm);
    if (field) {
        field.html(html);
        frm.refresh_field(field.df.fieldname);
        return field.$wrapper;
    }
    wf_debug('No HTML field found; falling back to dashboard');
    return insert_above_dashboard(frm, html);
}

// The field to draw into. Prefers a conventional name, else the first HTML
// field on the form, so this works on DocTypes we know nothing about.
function wf_target_field(frm) {
    let preferred = ['custom_progress_bar', 'workflow_progress', 'progress_bar'];
    for (let name of preferred) {
        if (frm.fields_dict[name]) return frm.fields_dict[name];
    }
    for (let df of frm.meta.fields) {
        if (df.fieldtype === 'HTML' && frm.fields_dict[df.fieldname]) {
            return frm.fields_dict[df.fieldname];
        }
    }
    return null;
}

function load_workflow_graph(frm) {
    // `refresh` and `workflow_state` can both fire for one state change, so two
    // requests are often in flight at once. Only the newest is allowed to paint;
    // without this both callbacks render and the second lands beside the first.
    let key = frm.doctype + '/' + frm.doc.name;
    let token = (workflow_progress.render_token[key] || 0) + 1;
    workflow_progress.render_token[key] = token;

    frappe.call({
        method: 'moi_app.utils.get_workflow_graph',
        args: { doctype: frm.doctype, docname: frm.doc.name },
        callback: function (r) {
            if (workflow_progress.render_token[key] !== token) {
                wf_debug('Superseded by a newer render; dropping this response');
                return;
            }
            if (!r.message) {
                // No active workflow on this DocType — draw nothing at all.
                wf_debug('No active workflow for', frm.doctype);
                wf_paint(frm, '');
                return;
            }
            let graph = build_graph(r.message);
            if (!graph.nodes.length) {
                wf_show_message(frm, __('No workflow states configured'), 'info');
                return;
            }
            let $wrapper = wf_paint(frm, render_graph(graph));
            // Edges need real geometry, so they are drawn after layout settles.
            if ($wrapper) draw_edges($wrapper, graph);
        },
        error: function (err) {
            console.error('[workflow-progress] Error loading workflow:', err);
            wf_show_message(frm, __('Could not load the workflow progress.'), 'danger');
        }
    });
}

// ---------------------------------------------------------------------------
// Graph model
// ---------------------------------------------------------------------------

// Default badge label per state, mirroring STATE_STYLES.badgeLabel in the design.
const WF_STATE_BADGE = {
    completed: 'Completed',
    current: 'Current',
    paused: 'Under Review',
    rejected: 'Rejected',
    upcoming: null,
    unreachable: null
};

/**
 * Turn the server payload into a laid-out graph.
 *
 * Layering uses the workflow's own state order to split edges into "forward"
 * (order increases) and "back" (a rejection or resubmit loop). Only forward
 * edges feed the depth calculation, which guarantees termination even though
 * real workflows are full of cycles.
 */
function build_graph(payload) {
    let names = payload.states.map(function (s) { return s.name; });
    let order = {};
    payload.states.forEach(function (s) { order[s.name] = s.order; });

    let edges = payload.transitions.map(function (t) {
        return {
            from: t.from_state,
            to: t.to_state,
            action: t.action,
            allowed: t.allowed,
            condition: t.condition,
            satisfied: t.satisfied,
            traversed: t.traversed,
            applies: t.applies
        };
    });

    // Split the edges by walking the graph, NOT by comparing the declared
    // state order. The Workflow's States table is authored in whatever
    // sequence rows were added, which often is not the order of the flow —
    // when it is not, comparing positions mislabels ordinary steps as
    // loop-backs and the layout collapses.
    let back_edges = find_back_edges(names, edges, order);
    let forward = edges.filter(function (e) { return !back_edges.has(e); });
    let back = edges.filter(function (e) { return back_edges.has(e); });

    let depth = compute_depth(names, forward);
    let reachable = compute_reachable(payload.current_state, forward.concat(back));

    let nodes = payload.states.map(function (s) {
        return {
            name: s.name,
            order: s.order,
            doc_status: s.doc_status,
            style: s.style,
            depth: depth[s.name] || 0,
            state: resolve_node_state(s, payload, reachable),
            // Where the document sits, independent of how the node is styled:
            // a terminal state renders as completed but is still the current one.
            is_current: s.name === payload.current_state,
            phase: s.phase,
            meta: payload.history[s.name] || null
        };
    });

    // Group into columns, then sort within a column by the workflow's own order.
    let columns = [];
    nodes.forEach(function (n) {
        (columns[n.depth] = columns[n.depth] || []).push(n);
    });
    columns = columns.filter(Boolean);
    columns.forEach(function (col) { col.sort(function (a, b) { return a.order - b.order; }); });

    return {
        workflow: payload.workflow,
        doctype: payload.doctype,
        current_state: payload.current_state,
        nodes: nodes,
        columns: columns,
        forward: forward,
        back: back,
        accent: accent_for(payload.current_state, nodes)
    };
}

/**
 * Find the edges that loop back on themselves, by depth-first search.
 *
 * An edge is a loop-back only if it points at a state already open on the
 * current search path — a real cycle such as "Rejected -> Draft". Everything
 * else moves the flow forward, whatever position the states happen to occupy
 * in the Workflow's States table.
 */
function find_back_edges(names, edges, order) {
    let adjacency = {};
    let indegree = {};
    names.forEach(function (n) { adjacency[n] = []; indegree[n] = 0; });
    edges.forEach(function (e) {
        if (adjacency[e.from]) adjacency[e.from].push(e);
        if (indegree[e.to] !== undefined) indegree[e.to]++;
    });

    // Start from the real entry points. A workflow with no entry point is
    // entirely cyclic, so fall back to the first declared state to keep the
    // walk deterministic.
    let by_order = names.slice().sort(function (a, b) { return order[a] - order[b]; });
    let roots = by_order.filter(function (n) { return indegree[n] === 0; });
    let starts = roots.length ? roots : by_order.slice(0, 1);

    const WHITE = 0, GREY = 1, BLACK = 2;
    let colour = {};
    names.forEach(function (n) { colour[n] = WHITE; });

    let back = new Set();

    // Iterative DFS: frames hold the node and how far through its edges we are.
    function walk(root) {
        let stack = [{ node: root, index: 0 }];
        colour[root] = GREY;
        while (stack.length) {
            let frame = stack[stack.length - 1];
            let outgoing = adjacency[frame.node];
            if (frame.index >= outgoing.length) {
                colour[frame.node] = BLACK;
                stack.pop();
                continue;
            }
            let edge = outgoing[frame.index++];
            if (colour[edge.to] === GREY) {
                // Points at a state still open on this path — a genuine cycle.
                back.add(edge);
            } else if (colour[edge.to] === WHITE) {
                colour[edge.to] = GREY;
                stack.push({ node: edge.to, index: 0 });
            }
            // BLACK: already finished, so this is a cross edge, not a loop.
        }
    }

    starts.forEach(function (n) { if (colour[n] === WHITE) walk(n); });
    // Anything unreachable from an entry point still needs classifying.
    by_order.forEach(function (n) { if (colour[n] === WHITE) walk(n); });

    return back;
}

/**
 * Longest path to each state over forward edges only.
 *
 * With loop-backs removed the remainder is a DAG, so Kahn's algorithm settles
 * every predecessor before its successors and terminates on cyclic workflows.
 */
function compute_depth(names, forward) {
    let adjacency = {};
    let indegree = {};
    let depth = {};
    names.forEach(function (n) { adjacency[n] = []; indegree[n] = 0; depth[n] = 0; });

    forward.forEach(function (e) {
        if (!adjacency[e.from] || indegree[e.to] === undefined) return;
        adjacency[e.from].push(e.to);
        indegree[e.to]++;
    });

    let queue = names.filter(function (n) { return indegree[n] === 0; });
    while (queue.length) {
        let node = queue.shift();
        adjacency[node].forEach(function (next) {
            if (depth[next] < depth[node] + 1) depth[next] = depth[node] + 1;
            if (--indegree[next] === 0) queue.push(next);
        });
    }

    return depth;
}

// Every state still reachable from where the document sits now.
function compute_reachable(current_state, edges) {
    let reachable = {};
    if (!current_state) return reachable;

    let adjacency = {};
    edges.forEach(function (e) {
        (adjacency[e.from] = adjacency[e.from] || []).push(e.to);
    });

    let queue = [current_state];
    reachable[current_state] = true;
    while (queue.length) {
        let node = queue.shift();
        (adjacency[node] || []).forEach(function (next) {
            if (!reachable[next]) {
                reachable[next] = true;
                queue.push(next);
            }
        });
    }
    return reachable;
}

/**
 * Map a workflow state onto one of the design's visual states.
 *
 * The Workflow State `style` field is the designer's own intent, so it wins
 * over name guessing; doc_status 2 (cancelled) is treated as a dead end.
 */
function resolve_node_state(state, payload, reachable) {
    let name = state.name;
    let style = (state.style || '').toLowerCase();
    let key = name.toLowerCase();

    let is_rejection = style === 'danger' || state.doc_status === 2 ||
        key.includes('reject') || key.includes('cancel');
    let is_hold = style === 'warning' || key.includes('hold') || key.includes('pause');

    if (name === payload.current_state) {
        if (is_rejection) return 'rejected';
        if (is_hold) return 'paused';
        // A state with nothing leading out of it means the flow has finished.
        let has_exit = payload.transitions.some(function (t) { return t.from_state === name; });
        return has_exit ? 'current' : 'completed';
    }

    // The server derives past/future from the graph itself, which stays correct
    // on DocTypes that keep no Version history.
    if (state.phase === 'past') return 'completed';
    if (state.phase === 'future') return 'upcoming';
    if (state.phase === 'other') return 'unreachable';

    // Fallback for a payload without phases.
    if (payload.history[name]) return 'completed';
    if (reachable[name]) return 'upcoming';
    // A branch the document can no longer take (e.g. Rejected once approved).
    return 'unreachable';
}

function accent_for(current_state, nodes) {
    let node = nodes.filter(function (n) { return n.name === current_state; })[0];
    return node ? node.state : 'upcoming';
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

// Lucide icon paths, matching the glyphs used in the Figma component set.
const WF_ICON_PATHS = {
    check: '<path d="M20 6 9 17l-5-5"/>',
    pause: '<rect x="14" y="4" width="4" height="16" rx="1"/><rect x="6" y="4" width="4" height="16" rx="1"/>',
    close: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    user: '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    calendar: '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/>'
};

function wf_icon(name, size, stroke) {
    return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${stroke}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${WF_ICON_PATHS[name]}</svg>`;
}

// The glyph inside the circular node: icon for resolved states, number otherwise.
function wf_node_glyph(step_state, number) {
    if (step_state === 'completed') return wf_icon('check', 18, 2.5);
    if (step_state === 'rejected') return wf_icon('close', 18, 2.5);
    if (step_state === 'current' || step_state === 'paused') return wf_icon('pause', 18, 2.5);
    return `<span class="wf-step-number">${number}</span>`;
}

// Formatted for the user's locale, without seconds — the exact second a step
// was actioned is noise at this size.
function wf_datetime(value) {
    let text = frappe.datetime.str_to_user(value) || '';
    // Trim a trailing :ss off the time part, whatever the date format is.
    return text.replace(/(\d{1,2}:\d{2}):\d{2}/, '$1');
}

// Links through to the User record. Desk routes are /app/<doctype>/<name>.
function wf_user_link(user, label) {
    return `<a class="wf-user-link" href="/app/user/${encodeURIComponent(user)}">${wf_escape(label)}</a>`;
}

// Subtle surface card carrying assignee + timestamp.
function wf_meta_block(meta, elevate, phase) {
    if (!meta) return '';
    // A step already behind us was not "pending" — say plainly that nothing was
    // recorded, which happens when the DocType does not track changes.
    let unknown = phase === 'past' ? __('Not recorded') : null;

    // Only a real user is linked; the fallbacks are plain text.
    let who = meta.user
        ? wf_user_link(meta.user, frappe.user.full_name(meta.user) || meta.user)
        : wf_escape(unknown || __('Unassigned'));
    let when = meta.on
        ? wf_escape(wf_datetime(meta.on))
        : wf_escape(unknown || __('Pending'));

    return `
        <div class="wf-step-meta${elevate ? ' is-elevated' : ''}">
            <div class="wf-meta-row">${wf_icon('user', 12, 2)}<span>${who}</span></div>
            <div class="wf-meta-row">${wf_icon('calendar', 12, 2)}<span>${when}</span></div>
        </div>
    `;
}

function render_graph(graph) {
    let html = `
        <div class="workflow-progress-container is-${graph.accent}">
            <div class="workflow-header">
                <div class="workflow-header-text">
                    <div class="workflow-title">${__('Workflow Progress')}</div>
                </div>
            </div>
            <div class="workflow-steps-container">
                <div class="workflow-graph">
                    <svg class="wf-edges" aria-hidden="true"></svg>
    `;

    graph.columns.forEach(function (column, col_index) {
        html += `<div class="wf-column">`;
        column.forEach(function (node) {
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
    let is_alert = node.state === 'paused' || node.state === 'rejected';
    // The design elevates the metadata behind the node that owns the workflow
    // right now, so the reader can see at a glance who it is waiting on.
    let elevate = node.is_current;

    // Every step the document has been through, plus the one it sits on, shows
    // a metadata block; upcoming steps carry none, per the design. The block is
    // rendered even with nothing recorded, so the steps in between do not lose
    // it just because the DocType keeps no Version history.
    let shows_meta = node.phase
        ? (node.phase === 'past' || node.phase === 'current')
        : (node.state !== 'upcoming' && node.state !== 'unreachable');

    let meta = node.meta;
    if (!meta && shows_meta) meta = {};

    let ring = (node.state === 'current' || is_alert)
        ? '<span class="wf-step-ring"></span>'
        : '';

    let badge = badge_label
        ? `<span class="wf-step-badge${is_alert ? ' is-alert' : ''}">${__(badge_label)}</span>`
        : '';

    // data-state keys the SVG edge endpoints to this node.
    return `
        <div class="workflow-step is-${node.state}" style="--i:${col_index}" data-state="${wf_escape(node.name)}">
            <div class="wf-step-indicator">
                ${ring}
                <div class="wf-step-node">${wf_node_glyph(node.state, node.depth + 1)}</div>
            </div>
            <div class="wf-step-title">${__(node.name)}</div>
            ${badge}
            ${wf_meta_block(meta, elevate, node.phase)}
        </div>
    `;
}

// ---------------------------------------------------------------------------
// Edges
// ---------------------------------------------------------------------------

const WF_EDGE_COLOR = {
    completed: '#10B981',
    current: '#F59E0B',
    paused: '#F59E0B',
    rejected: '#EF4444',
    upcoming: '#E5E7EB',
    unreachable: '#F3F4F6'
};

/**
 * Draw every transition as an SVG path once the nodes have real geometry.
 *
 * Straight-ish curves for forward edges; back edges (rejection loops,
 * resubmits) sweep underneath so they never sit on top of a forward path.
 */
function draw_edges($wrapper, graph) {
    let $graph = $wrapper.find('.workflow-graph');
    let $svg = $graph.find('svg.wf-edges');
    if (!$graph.length || !$svg.length) return;

    let origin = $graph[0].getBoundingClientRect();
    let anchors = {};

    $graph.find('.workflow-step').each(function () {
        let name = $(this).attr('data-state');
        let node = $(this).find('.wf-step-node')[0];
        if (!node) return;
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
    graph.nodes.forEach(function (n) { node_state[n.name] = n.state; });

    let paths = [];

    graph.forward.forEach(function (edge) {
        let a = anchors[edge.from];
        let b = anchors[edge.to];
        if (!a || !b) return;
        // Leave the source on its right edge, enter the target on its left.
        let dx = Math.max(24, (b.left - a.right) * 0.5);
        let d = `M ${a.right} ${a.cy} C ${a.right + dx} ${a.cy}, ${b.left - dx} ${b.cy}, ${b.left} ${b.cy}`;
        paths.push(edge_path(d, node_state[edge.from], edge, false));
    });

    graph.back.forEach(function (edge) {
        let a = anchors[edge.from];
        let b = anchors[edge.to];
        if (!a || !b) return;
        // Sweep below the rail so a loop-back never overlaps a forward edge.
        let drop = Math.max(a.bottom, b.bottom) + 26;
        let d = `M ${a.cx} ${a.bottom} C ${a.cx} ${drop}, ${b.cx} ${drop}, ${b.cx} ${b.bottom}`;
        paths.push(edge_path(d, node_state[edge.from], edge, true));
    });

    let width = $graph[0].scrollWidth;
    let height = $graph[0].scrollHeight;
    $svg.attr('viewBox', `0 0 ${width} ${height}`)
        .attr('width', width)
        .attr('height', height)
        .html(paths.join(''));
}

function edge_path(d, from_state, edge, is_back) {
    let color = WF_EDGE_COLOR[from_state] || WF_EDGE_COLOR.upcoming;
    // Dash a branch this record's own data rules out — a fork it will not take.
    // `applies` already treats session-user checks as true, so a step merely
    // waiting on someone else is not dashed. Traversed edges stay solid.
    let dashed = is_back || (edge.applies === false && !edge.traversed);
    let title = edge.action ? `<title>${wf_escape(edge.action)}</title>` : '';
    return `<path d="${d}" fill="none" stroke="${color}" stroke-width="3" stroke-linecap="round"${dashed ? ' stroke-dasharray="6 6"' : ''}>${title}</path>`;
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

function add_workflow_styles() {
    if ($('#workflow-figma-styles').length) return;
    $('#workflow-custom-styles').remove();

    let styles = `
        <style id="workflow-figma-styles">
            /* ------------------------------------------------------------------
               Workflow Stepper — tokens from the "ERP Designs" Figma component set
               (Workflow / Stepper Node + Workflow / Progress Bar).
               Every rule is scoped to .workflow-progress-container so nothing
               leaks into Frappe's own .progress / .badge styles.
               ------------------------------------------------------------------ */

            .workflow-progress-container {
                --wf-neutral-line: #E5E7EB;
                --wf-text-primary: #111827;
                --wf-text-muted: #6B7280;

                width: 100%;
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

            /* Columns are laid out left to right; branches stack within a column.
               The rail spans the full width and spreads its columns across it;
               the gap then acts as minimum spacing, and min-width keeps the
               container scrollable once the flow outgrows the space. */
            .workflow-progress-container .workflow-graph {
                position: relative;
                display: flex;
                align-items: flex-start;
                justify-content: space-between;
                width: 100%;
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
                width: 170px;
                flex: 0 0 170px;
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

            /* A branch the document can no longer reach — present, but muted. */
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

            /* The actor links through to their User record. It stays muted so
               the metadata keeps its supporting role, and only reads as a link
               on hover. */
            .workflow-progress-container .wf-user-link {
                color: inherit;
                text-decoration: none;
                border-bottom: 1px dotted #D1D5DB;
            }

            .workflow-progress-container .wf-user-link:hover,
            .workflow-progress-container .wf-user-link:focus {
                color: var(--wf-text-primary);
                border-bottom-color: currentColor;
                text-decoration: none;
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

    $('head').append(styles);
}

// ---------------------------------------------------------------------------
// Fallback placement when the form has no HTML field
// ---------------------------------------------------------------------------

function insert_above_dashboard(frm, html) {
    // Remove every previous wrapper, not just the first match.
    $('.wf-injected, #custom-above-dashboard-wrapper').remove();

    var $dashboard = $('.form-dashboard');
    if ($dashboard.length === 0) $dashboard = $('.form-dashboard-section');
    if ($dashboard.length === 0) $dashboard = $('.dashboard-section');
    if ($dashboard.length === 0) $dashboard = $('.form-dashboard-wrapper');

    var $content = $('<div class="wf-injected" id="custom-above-dashboard-wrapper">').append($(html));

    if ($dashboard.length > 0) {
        $dashboard.before($content);
        wf_debug('Content inserted before dashboard');
    } else {
        var $lastSection = $('.section-break').last();
        if ($lastSection.length > 0) {
            $lastSection.after($content);
            wf_debug('Content inserted after last section');
        } else {
            $('.form-body').append($content);
            wf_debug('Content appended to form body');
        }
    }
    return $content;
}
