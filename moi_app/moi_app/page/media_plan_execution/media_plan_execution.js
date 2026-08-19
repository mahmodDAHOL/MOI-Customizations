frappe.pages["media-plan-execution"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __("Media Plan Execution"),
    single_column: false,
  });
  frappe.require("media_plan_execution_page.bundle.css", () => {
    wrapper.media_plan_execution_page = new MediaPlanExecutionPage(page);
  });
};

frappe.pages["media-plan-execution"].on_page_show = function (wrapper) {
  wrapper.media_plan_execution_page?.refreshIfStale();
};

class MediaPlanExecutionPage {
  constructor(page) {
    this.page = page;
    this.root = null;
    this.timer = null;
    this.loadedAt = 0;
    this.state = {
      items: [], query: "", scopeMode: "mine", assignedUser: "", itemType: "", status: "",
      mediaPlan: frappe.utils.get_url_arg("media_plan") || "", nextStart: 0, hasMore: false,
      total: 0, loading: false, userOptions: [], scope: {}, canCreateProduction: false, canCreateWorkItem: false,
    };
    this.init();
  }

  async init() {
    this.renderShell();
    this.bindEvents();
    await this.load(false);
  }

  renderShell() {
    this.page.main.html(`
      <section class="mpe-wrapper" data-mpe-root dir="${frappe.utils.is_rtl() ? "rtl" : "ltr"}">
        <header class="mpe-hero">
          <div><span>${this.escape(__("Plan Execution"))}</span><h2>${this.escape(__("My Media Plan Assignments"))}</h2><p>${this.escape(__("Execute planned and unplanned media production and coordination work from one place."))}</p></div>
          <div class="mpe-hero-actions">
            <button type="button" class="btn btn-default" data-new-work hidden>＋ ${this.escape(__("New Work Item"))}</button>
            <button type="button" class="btn btn-primary" data-new-production hidden>＋ ${this.escape(__("New Media Production"))}</button>
          </div>
        </header>
        <nav class="mpe-scope-tabs" aria-label="${this.escape(__("Execution scope"))}">
          <button type="button" class="is-active" data-scope="mine">${this.escape(__("My Assignments"))}</button>
          <button type="button" data-scope="team">${this.escape(__("Team View"))}</button>
        </nav>
        <section class="mpe-toolbar">
          <label class="mpe-search"><span>⌕</span><input type="search" data-search placeholder="${this.escape(__("Search assignments"))}"></label>
          <label><span>${this.escape(__("Assigned User"))}</span><select data-user><option value="">${this.escape(__("All Assigned Users"))}</option></select></label>
          <label><span>${this.escape(__("Type"))}</span><select data-type><option value="">${this.escape(__("All Types"))}</option><option value="production">${this.escape(__("Media Production"))}</option><option value="work_item">${this.escape(__("Media Work Item"))}</option></select></label>
          <label><span>${this.escape(__("Status"))}</span><select data-status><option value="">${this.escape(__("All States"))}</option>${["Planned", "Draft", "Started", "In Progress", "Completed", "Approved", "Cancelled"].map((value) => `<option value="${value}">${this.escape(__(value))}</option>`).join("")}</select></label>
          <button type="button" class="btn btn-default" data-refresh>↻ ${this.escape(__("Refresh"))}</button>
        </section>
        <div class="mpe-summary"><strong data-total>0</strong><span>${this.escape(__("assignments"))}</span><small data-plan-scope></small></div>
        <div class="mpe-feedback" data-feedback hidden></div>
        <main class="mpe-grid" data-grid></main>
        <footer class="mpe-pagination"><button type="button" class="btn btn-default" data-more hidden>${this.escape(__("Load More"))}</button></footer>
      </section>
    `);
    this.root = this.page.main.find("[data-mpe-root]")[0];
  }

  bindEvents() {
    this.root.querySelector("[data-new-production]").addEventListener("click", () => frappe.new_doc("Media Production", { execution_source: "Unplanned", responsible_user: frappe.session.user, media_plan: this.state.mediaPlan || undefined }));
    this.root.querySelector("[data-new-work]").addEventListener("click", () => frappe.new_doc("Media Work Item", { execution_source: "Unplanned", assigned_user: frappe.session.user, media_plan: this.state.mediaPlan || undefined }));
    this.root.querySelector("[data-refresh]").addEventListener("click", () => this.load(false));
    this.root.querySelector("[data-more]").addEventListener("click", () => this.load(true));
    this.root.querySelectorAll("[data-scope]").forEach((button) => button.addEventListener("click", () => {
      this.state.scopeMode = button.dataset.scope;
      this.state.assignedUser = "";
      this.root.querySelectorAll("[data-scope]").forEach((candidate) => candidate.classList.toggle("is-active", candidate === button));
      this.load(false);
    }));
    this.root.querySelector("[data-search]").addEventListener("input", (event) => {
      this.state.query = event.target.value.trim();
      window.clearTimeout(this.timer);
      this.timer = window.setTimeout(() => this.load(false), 260);
    });
    [["[data-user]", "assignedUser"], ["[data-type]", "itemType"], ["[data-status]", "status"]].forEach(([selector, key]) => {
      this.root.querySelector(selector).addEventListener("change", (event) => { this.state[key] = event.target.value; this.load(false); });
    });
  }

  async load(append) {
    if (this.state.loading) return;
    this.state.loading = true;
    const feedback = this.root.querySelector("[data-feedback]");
    feedback.hidden = false;
    feedback.className = "mpe-feedback is-loading";
    feedback.textContent = append ? __("Loading more assignments...") : __("Loading assignments...");
    try {
      const response = await frappe.call({
        method: "press_affairs_app.moi.page.media_plan_execution.media_plan_execution.get_assignments",
        type: "GET",
        args: {
          query: this.state.query, scope_mode: this.state.scopeMode, assigned_user: this.state.assignedUser,
          item_type: this.state.itemType, status: this.state.status, media_plan: this.state.mediaPlan,
          limit_start: append ? this.state.nextStart : 0, page_length: 40,
        },
      });
      const data = response.message || {};
      const incoming = Array.isArray(data.items) ? data.items : [];
      this.state.items = append ? this.state.items.concat(incoming) : incoming;
      this.state.nextStart = Number(data.next_start || this.state.items.length);
      this.state.hasMore = Boolean(data.has_more);
      this.state.total = Number(data.total || 0);
      this.state.userOptions = data.user_options || [];
      this.state.scope = data.scope || {};
      this.state.canCreateProduction = Boolean(data.can_create_production);
      this.state.canCreateWorkItem = Boolean(data.can_create_work_item);
      this.populateUsers();
      this.render();
      feedback.hidden = true;
      this.loadedAt = Date.now();
    } catch (error) {
      feedback.className = "mpe-feedback is-error";
      feedback.textContent = this.errorMessage(error);
    } finally {
      this.state.loading = false;
      this.root.querySelector("[data-more]").hidden = !this.state.hasMore;
    }
  }

  populateUsers() {
    const select = this.root.querySelector("[data-user]");
    select.innerHTML = `<option value="">${this.escape(__("All Assigned Users"))}</option>` + this.state.userOptions.map((option) => `<option value="${this.escape(option.value)}">${this.escape(option.label)}</option>`).join("");
    select.value = this.state.assignedUser;
    select.closest("label").hidden = this.state.scopeMode === "mine" || (this.state.userOptions.length <= 1 && !this.state.assignedUser);
    this.root.querySelector('[data-scope="team"]').hidden = !this.state.scope.is_administrator && Number(this.state.scope.team_user_count || 0) === 0;
    this.root.querySelector("[data-new-production]").hidden = !this.state.canCreateProduction;
    this.root.querySelector("[data-new-work]").hidden = !this.state.canCreateWorkItem;
  }

  render() {
    this.root.querySelector("[data-total]").textContent = this.state.total;
    this.root.querySelector("[data-plan-scope]").textContent = this.state.mediaPlan ? `${__("Media Plan")}: ${this.state.mediaPlan}` : "";
    const grid = this.root.querySelector("[data-grid]");
    if (!this.state.items.length) {
      grid.innerHTML = `<div class="mpe-empty"><span>◌</span><h3>${this.escape(__("No execution assignments found"))}</h3><p>${this.escape(__("Change the filters or create an unplanned execution item."))}</p></div>`;
      return;
    }
    grid.innerHTML = this.state.items.map((item) => this.card(item)).join("");
    grid.querySelectorAll("[data-start]").forEach((button) => button.addEventListener("click", () => this.startItem(button.dataset.type, button.dataset.start, button)));
    grid.querySelectorAll("[data-open]").forEach((button) => button.addEventListener("click", () => frappe.set_route("Form", button.dataset.doctype, button.dataset.open)));
  }

  card(item) {
    const typeLabel = item.item_type === "production" ? __("Media Production") : __("Media Work Item");
    const progress = Math.max(0, Math.min(Number(item.progress || 0), 100));
    return `<article class="mpe-card mpe-status-${this.className(item.status)}">
      <header><span class="mpe-type">${this.escape(typeLabel)}</span><span class="mpe-status">${this.escape(__(item.status || "Draft"))}</span></header>
      <h3>${this.escape(item.title)}</h3><p>${this.escape(item.detail || item.entity || "—")}</p>
      <dl><div><dt>${this.escape(__("Media Plan"))}</dt><dd>${this.escape(item.media_plan || __("Unplanned"))}</dd></div><div><dt>${this.escape(__("Responsible User"))}</dt><dd>${this.escape(item.responsible_user || __("Unassigned"))}</dd></div><div><dt>${this.escape(__("Due Date"))}</dt><dd>${this.escape(this.userDate(item.end_date))}</dd></div></dl>
      <div class="mpe-progress"><span style="width:${progress}%"></span></div>
      <footer><small>${Math.round(progress)}%</small>${item.can_start ? `<button type="button" class="btn btn-primary btn-sm" data-start="${this.escape(item.planned_row)}" data-type="${this.escape(item.item_type)}">${this.escape(__("Start Execution"))}</button>` : `<button type="button" class="btn btn-default btn-sm" data-open="${this.escape(item.name)}" data-doctype="${this.escape(item.doctype)}">${this.escape(__("Open"))}</button>`}</footer>
    </article>`;
  }

  async startItem(type, rowName, button) {
    button.disabled = true;
    frappe.dom.freeze(__("Starting execution..."));
    try {
      const response = await frappe.call({
        method: "press_affairs_app.moi.page.media_plan_execution.media_plan_execution.start_planned_item",
        type: "POST",
        args: { item_type: type, row_name: rowName },
      });
      const result = response.message || {};
      if (!result.name || !result.doctype) throw new Error(__("Unable to start execution."));
      frappe.set_route("Form", result.doctype, result.name);
    } catch (error) {
      button.disabled = false;
      frappe.msgprint({ title: __("Unable to start execution"), message: this.escape(this.errorMessage(error)), indicator: "red" });
    } finally {
      frappe.dom.unfreeze();
    }
  }

  refreshIfStale() { if (this.root && Date.now() - this.loadedAt > 15000 && !this.state.loading) this.load(false); }
  userDate(value) { return value ? (frappe.datetime?.str_to_user ? frappe.datetime.str_to_user(value) : value) : "—"; }
  className(value) { return String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, "-") || "default"; }
  errorMessage(error) { return error?.message || error?._server_messages || __("Unable to load assignments."); }
  escape(value) { return frappe.utils.escape_html(String(value ?? "—")); }
}
