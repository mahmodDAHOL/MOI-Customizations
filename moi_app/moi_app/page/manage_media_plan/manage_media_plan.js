frappe.pages["manage-media-plan"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __("Manage Media Plan"),
    single_column: false,
  });

  frappe.require("manage_media_plan_page.bundle.css", () => {
    wrapper.manage_media_plan_page = new ManageMediaPlanPage(page);
  });
};

frappe.pages["manage-media-plan"].on_page_show = function (wrapper) {
  wrapper.manage_media_plan_page?.refreshIfStale();
};

class ManageMediaPlanPage {
  constructor(page) {
    this.page = page;
    this.root = null;
    this.searchTimer = null;
    this.initializedAt = 0;
    this.state = {
      plans: [],
      query: "",
      planOwner: "",
      workflowState: "",
      nextStart: 0,
      hasMore: false,
      isLoading: false,
      canCreate: false,
      ownerOptions: [],
      workflowStates: [],
      workflowStateField: "workflow_state",
      scope: {},
    };
    this.init();
  }

  async init() {
    this.renderShell();
    this.bindEvents();
    await this.loadPlans(false);
  }

  renderShell() {
    this.page.main.html(`
      <section class="mplp-wrapper" data-mplp-root dir="${frappe.utils.is_rtl() ? "rtl" : "ltr"}">
        <header class="mplp-hero">
          <div class="mplp-hero-copy">
            <span class="mplp-eyebrow">${this.escape(__("Media Planning"))}</span>
            <h2>${this.escape(__("Media Plans"))}</h2>
            <p>${this.escape(__("View your plans and the plans of employees in your reporting hierarchy."))}</p>
          </div>
          <button type="button" class="btn btn-primary mplp-new-plan" data-mplp-new-plan hidden>
            <span aria-hidden="true">＋</span>${this.escape(__("New Media Plan"))}
          </button>
        </header>

        <div class="mplp-scope" data-mplp-scope>
          <span class="mplp-scope-icon" aria-hidden="true">◇</span>
          <strong data-mplp-scope-text></strong>
          <small data-mplp-result-count></small>
        </div>

        <section class="mplp-toolbar" aria-label="${this.escape(__("Media Plan filters"))}">
          <label class="mplp-search">
            <span aria-hidden="true">⌕</span>
            <input type="search" data-mplp-search placeholder="${this.escape(__("Search plans, projects, or references"))}">
          </label>
          <label class="mplp-filter">
            <span>${this.escape(__("Plan Owner"))}</span>
            <select data-mplp-owner><option value="">${this.escape(__("All Plan Owners"))}</option></select>
          </label>
          <label class="mplp-filter">
            <span>${this.escape(__("Status"))}</span>
            <select data-mplp-state><option value="">${this.escape(__("All States"))}</option></select>
          </label>
          <button type="button" class="btn btn-default mplp-refresh" data-mplp-refresh title="${this.escape(__("Refresh"))}">
            <span aria-hidden="true">↻</span><span>${this.escape(__("Refresh"))}</span>
          </button>
        </section>

        <div class="mplp-feedback" data-mplp-feedback hidden></div>
        <section class="mplp-list-shell">
          <div class="mplp-list-head" aria-hidden="true">
            <span>${this.escape(__("Media Plan"))}</span>
            <span>${this.escape(__("Plan Owner"))}</span>
            <span>${this.escape(__("Period"))}</span>
            <span>${this.escape(__("Priority"))}</span>
            <span>${this.escape(__("Status"))}</span>
            <span></span>
          </div>
          <div class="mplp-list" data-mplp-list></div>
        </section>
        <footer class="mplp-pagination">
          <button type="button" class="btn btn-default" data-mplp-load-more hidden>${this.escape(__("Load More"))}</button>
        </footer>
      </section>
    `);
    this.root = this.page.main.find("[data-mplp-root]")[0];
  }

  bindEvents() {
    this.root.querySelector("[data-mplp-new-plan]").addEventListener("click", () => {
      frappe.set_route("media-plan-wizard");
    });
    this.root.querySelector("[data-mplp-refresh]").addEventListener("click", () => this.loadPlans(false));
    this.root.querySelector("[data-mplp-load-more]").addEventListener("click", () => this.loadPlans(true));
    this.root.querySelector("[data-mplp-owner]").addEventListener("change", (event) => {
      this.state.planOwner = event.target.value;
      this.loadPlans(false);
    });
    this.root.querySelector("[data-mplp-state]").addEventListener("change", (event) => {
      this.state.workflowState = event.target.value;
      this.loadPlans(false);
    });
    this.root.querySelector("[data-mplp-search]").addEventListener("input", (event) => {
      this.state.query = event.target.value.trim();
      window.clearTimeout(this.searchTimer);
      this.searchTimer = window.setTimeout(() => this.loadPlans(false), 280);
    });
  }

  async loadPlans(append) {
    if (this.state.isLoading) return;
    this.state.isLoading = true;
    const feedback = this.root.querySelector("[data-mplp-feedback]");
    const loadMore = this.root.querySelector("[data-mplp-load-more]");
    feedback.hidden = false;
    feedback.className = "mplp-feedback is-loading";
    feedback.textContent = append ? __("Loading more Media Plans...") : __("Loading Media Plans...");
    loadMore.disabled = true;

    try {
      const response = await frappe.call({
        method: "press_affairs_app.moi.page.manage_media_plan.manage_media_plan.get_plans",
        type: "GET",
        args: {
          query: this.state.query,
          plan_owner: this.state.planOwner,
          workflow_state: this.state.workflowState,
          limit_start: append ? this.state.nextStart : 0,
          page_length: 30,
        },
      });
      const data = response.message || {};
      const incoming = Array.isArray(data.plans) ? data.plans : [];
      this.state.plans = append ? this.state.plans.concat(incoming) : incoming;
      this.state.nextStart = Number(data.next_start || this.state.plans.length);
      this.state.hasMore = Boolean(data.has_more);
      this.state.canCreate = Boolean(data.can_create);
      this.state.ownerOptions = data.owner_options || [];
      this.state.workflowStates = data.workflow_states || [];
      this.state.workflowStateField = data.workflow_state_field || "workflow_state";
      this.state.scope = data.scope || {};
      this.populateFilters();
      this.renderScope();
      this.renderPlans();
      this.root.querySelector("[data-mplp-new-plan]").hidden = !this.state.canCreate;
      feedback.hidden = true;
      this.initializedAt = Date.now();
    } catch (error) {
      feedback.hidden = false;
      feedback.className = "mplp-feedback is-error";
      feedback.textContent = this.errorMessage(error);
    } finally {
      this.state.isLoading = false;
      loadMore.disabled = false;
      loadMore.hidden = !this.state.hasMore;
    }
  }

  populateFilters() {
    const owner = this.root.querySelector("[data-mplp-owner]");
    owner.innerHTML = `<option value="">${this.escape(__("All Plan Owners"))}</option>` + this.state.ownerOptions
      .map((option) => `<option value="${this.escape(option.value)}">${this.escape(option.label || option.value)}</option>`)
      .join("");
    owner.value = this.state.planOwner;
    // Never hide an active filter; the user must always be able to clear it.
    owner.closest(".mplp-filter").hidden = this.state.ownerOptions.length <= 1 && !this.state.planOwner;

    const state = this.root.querySelector("[data-mplp-state]");
    state.innerHTML = `<option value="">${this.escape(__("All States"))}</option>` + this.state.workflowStates
      .map((value) => `<option value="${this.escape(value)}">${this.escape(__(value))}</option>`)
      .join("");
    state.value = this.state.workflowState;
    state.closest(".mplp-filter").hidden = !this.state.workflowStates.length;
  }

  renderScope() {
    const scopeText = this.root.querySelector("[data-mplp-scope-text]");
    const resultCount = this.root.querySelector("[data-mplp-result-count]");
    if (this.state.scope.is_administrator) {
      scopeText.textContent = __("Administrative view: all Media Plans are available.");
    } else if (Number(this.state.scope.team_user_count || 0) > 0) {
      scopeText.textContent = __("You can view your plans and the plans of {0} team members.", [this.state.scope.team_user_count]);
    } else {
      scopeText.textContent = __("Only Media Plans assigned to you are shown.");
    }
    resultCount.textContent = __("{0} plans shown", [this.state.plans.length]);
  }

  renderPlans() {
    const host = this.root.querySelector("[data-mplp-list]");
    if (!this.state.plans.length) {
      host.innerHTML = `
        <div class="mplp-empty">
          <span aria-hidden="true">◌</span>
          <h3>${this.escape(__("No Media Plans found"))}</h3>
          <p>${this.escape(__("Create a new plan or change the search and filter values."))}</p>
        </div>
      `;
      return;
    }

    host.innerHTML = this.state.plans.map((plan) => this.planRow(plan)).join("");
    host.querySelectorAll("[data-mplp-plan]").forEach((row) => {
      row.addEventListener("click", () => {
        window.location.assign(`/app/media-plan-wizard?media_plan=${encodeURIComponent(row.dataset.mplpPlan)}`);
      });
    });
  }

  planRow(plan) {
    const title = plan.plan_name || plan.plan_name_ar || plan.name;
    const state = this.planStatus(plan);
    const owner = this.state.ownerOptions.find((option) => option.value === plan.plan_owner);
    const ownerLabel = owner?.label || plan.plan_owner || "—";
    const initial = String(title || "M").trim().slice(0, 1).toUpperCase();
    return `
      <button type="button" class="mplp-plan" data-mplp-plan="${this.escape(plan.name)}">
        <span class="mplp-plan-main">
          <span class="mplp-plan-mark">${this.escape(initial)}</span>
          <span><strong>${this.escape(title)}</strong><small>${this.escape(plan.name)} · ${this.escape(plan.project)}</small></span>
        </span>
        <span class="mplp-owner"><small>${this.escape(__("Plan Owner"))}</small><strong>${this.escape(ownerLabel)}</strong></span>
        <span class="mplp-period"><small>${this.escape(__("Period"))}</small><strong>${this.escape(this.userDate(plan.start_date))} — ${this.escape(this.userDate(plan.end_date))}</strong></span>
        <span class="mplp-priority mplp-priority-${this.statusClass(plan.priority)}">${this.escape(__(plan.priority || "—"))}</span>
        <span class="mplp-status mplp-status-${this.statusClass(state)}">${this.escape(__(state))}</span>
        <span class="mplp-open" aria-hidden="true">›</span>
      </button>
    `;
  }

  planStatus(plan) {
    return plan[this.state.workflowStateField]
      || plan.workflow_state
      || plan.status
      || (Number(plan.docstatus) === 1 ? "Submitted" : "Draft");
  }

  statusClass(value) {
    return String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, "-") || "default";
  }

  userDate(value) {
    if (!value) return "—";
    return frappe.datetime?.str_to_user ? frappe.datetime.str_to_user(value) : value;
  }

  refreshIfStale() {
    if (this.root && Date.now() - this.initializedAt > 15000 && !this.state.isLoading) {
      this.loadPlans(false);
    }
  }

  errorMessage(error) {
    return error?.message || error?._server_messages || __("Unable to load Media Plans.");
  }

  escape(value) {
    return frappe.utils.escape_html(String(value ?? "—"));
  }
}
