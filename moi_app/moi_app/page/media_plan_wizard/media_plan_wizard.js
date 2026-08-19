frappe.pages["media-plan-wizard"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __("Media Plan Wizard"),
    single_column: false,
  });

  frappe.require("media_plan_wizard_page.bundle.css", () => {
    wrapper.media_plan_wizard = new MediaPlanWizardPage(page, wrapper);
  });
};

frappe.pages["media-plan-wizard"].on_page_show = function (wrapper) {
  wrapper.media_plan_wizard?.handleRouteChange();
};

class MediaPlanWizardPage {
  constructor(page, wrapper) {
    this.page = page;
    this.wrapper = wrapper;
    this.root = null;
    this.controls = new Map();
    this.state = {
      currentStep: 0,
      maxVisited: 0,
      isSaving: false,
      documentName: null,
      modified: null,
      canWrite: true,
      workflowDoc: null,
      workflowStateField: "workflow_state",
      workflowActions: [],
      isApplyingWorkflow: false,
      metadata: {},
      basic: {},
      planned_production: [],
      planned_work_items: [],
      risks: [],
      opportunities: [],
      inferred_goals: [],
      inferred_audiences: [],
      goal_audience_distribution: [],
    };
    this.steps = [
      { label: "Basic Information", key: "basic" },
      { label: "Media Production", key: "planned_production" },
      { label: "Media Work Items", key: "planned_work_items" },
      { label: "Opportunities and Risks", key: "risks_opportunities" },
      { label: "Goals and Target Audience Distribution", key: "distribution" },
      { label: "Preview", key: "preview" },
    ];
    this.init();
  }

  async init() {
    this.renderShell();
    this.setLoading(true, __("Loading Media Plan Wizard..."));
    try {
      const response = await frappe.call({
        method: "press_affairs_app.moi.page.media_plan_wizard.media_plan_wizard.get_bootstrap",
        type: "GET",
      });
      const bootstrap = response.message || {};
      this.state.metadata = bootstrap.fields || {};
      this.state.canWrite = Boolean(bootstrap.can_create);
      this.initBasicControls(bootstrap.user || frappe.session.user);

      const requestedPlan = frappe.utils.get_url_arg("media_plan");
      if (requestedPlan) await this.loadPlan(requestedPlan);
      if (!requestedPlan && !this.state.canWrite) {
        this.showError(__("You do not have permission to create Media Plan."));
      }

      this.renderStep();
      this.bindShellEvents();
      await this.loadWorkflowActions();
    } catch (error) {
      this.showError(this.errorMessage(error));
    } finally {
      this.setLoading(false);
    }
  }

  renderShell() {
    this.page.main.html(`
      <div class="mpp-wrapper" data-mpp-root dir="${frappe.utils.is_rtl() ? "rtl" : "ltr"}">
        <section class="mpp-hero">
          <div>
            <span class="mpp-eyebrow">${this.escape(__("Government Media"))}</span>
            <h2>${this.escape(__("Build a Media Plan"))}</h2>
            <p data-mpp-subtitle>${this.escape(__("Complete the plan through six focused steps."))}</p>
          </div>
          <div class="mpp-hero-actions">
            <button class="btn btn-default" data-mpp-open-execution hidden>${this.escape(__("Open Execution"))}</button>
            <button class="btn btn-default" data-mpp-open-form hidden>${this.escape(__("Open Standard Form"))}</button>
            <span class="mpp-step-count" data-mpp-step-count>1 / 6</span>
          </div>
        </section>
        <section class="mpp-workflow-bar" data-mpp-workflow-bar hidden>
          <div class="mpp-workflow-state">
            <span class="mpp-workflow-dot" aria-hidden="true"></span>
            <div>
              <small>${this.escape(__("Current Status"))}</small>
              <strong data-mpp-workflow-state></strong>
            </div>
          </div>
          <div class="mpp-workflow-actions" data-mpp-workflow-actions></div>
        </section>
        <div class="mpp-alert" data-mpp-alert hidden></div>
        <div class="mpp-loading" data-mpp-loading hidden><span class="mpp-spinner"></span><span data-mpp-loading-text></span></div>
        <nav class="mpp-stepper" data-mpp-stepper aria-label="${this.escape(__("Wizard steps"))}">
          ${this.steps.map((step, index) => `
            <button type="button" class="mpp-step ${index === 0 ? "is-active" : ""}" data-mpp-step="${index}">
              <span class="mpp-step-number">${index + 1}</span>
              <span class="mpp-step-label">${this.escape(__(step.label))}</span>
            </button>
          `).join("")}
        </nav>
        <main class="mpp-card">
          <div class="mpp-panel" data-mpp-panel></div>
          <footer class="mpp-actions">
            <button type="button" class="btn btn-default" data-mpp-action="previous">${this.escape(__("Previous"))}</button>
            <div>
              <button type="button" class="btn btn-primary" data-mpp-action="next">${this.escape(__("Next"))}</button>
              <button type="button" class="btn btn-primary" data-mpp-action="save" hidden>${this.escape(__("Save Media Plan"))}</button>
            </div>
          </footer>
        </main>
      </div>
    `);
    this.root = this.page.main.find("[data-mpp-root]")[0];
  }

  bindShellEvents() {
    this.root.querySelector("[data-mpp-action='previous']").addEventListener("click", () => {
      if (this.state.currentStep > 0) this.showStep(this.state.currentStep - 1, false);
    });
    this.root.querySelector("[data-mpp-action='next']").addEventListener("click", () => {
      if (!this.validateStep(this.state.currentStep)) return;
      this.showStep(this.state.currentStep + 1, false);
    });
    this.root.querySelector("[data-mpp-action='save']").addEventListener("click", () => this.savePlan());
    this.root.querySelector("[data-mpp-open-form]").addEventListener("click", () => {
      if (this.state.documentName) frappe.set_route("Form", "Media Plan", this.state.documentName);
    });
    this.root.querySelector("[data-mpp-open-execution]").addEventListener("click", () => {
      if (this.state.documentName) frappe.set_route("media-plan-execution", { media_plan: this.state.documentName });
    });
    this.root.querySelectorAll("[data-mpp-step]").forEach((button) => {
      button.addEventListener("click", () => {
        const requested = Number(button.dataset.mppStep);
        const canJump = Boolean(this.state.documentName) || requested <= this.state.maxVisited + 1;
        if (!canJump) {
          this.showError(__("Complete the current step before opening a later step."));
          return;
        }
        if (!this.state.documentName && requested > this.state.currentStep && !this.validateStep(this.state.currentStep)) {
          return;
        }
        this.showStep(requested, true);
      });
    });
  }

  initBasicControls(user) {
    this.state.basic = {
      plan_name: "",
      plan_name_ar: "",
      project: "",
      plan_owner: user,
      start_date: "",
      end_date: "",
      priority: "Medium",
      description: "",
    };
  }

  async loadPlan(name) {
    const response = await frappe.call({
      method: "press_affairs_app.moi.page.media_plan_wizard.media_plan_wizard.get_plan",
      type: "GET",
      args: { name },
    });
    const data = response.message || {};
    const doc = data.doc || {};
    this.state.documentName = doc.name;
    this.state.modified = doc.modified || null;
    this.state.canWrite = Boolean(data.can_write);
    this.state.workflowDoc = data.workflow_doc || (doc.name ? {
      doctype: "Media Plan",
      name: doc.name,
      docstatus: doc.docstatus || 0,
      workflow_state: doc.workflow_state || "",
      status: doc.status || "",
      modified: doc.modified || "",
    } : null);
    this.state.workflowStateField = data.workflow_state_field || "workflow_state";
    Object.keys(this.state.basic).forEach((fieldname) => {
      this.state.basic[fieldname] = doc[fieldname] ?? this.state.basic[fieldname];
    });
    ["planned_production", "planned_work_items", "risks", "opportunities"].forEach((key) => {
      this.state[key] = (doc[key] || []).map((row) => this.normalizeLoadedRow(row));
    });
    this.state.inferred_goals = (doc.inferred_goals || []).map((row) => ({ ...row }));
    this.state.goal_audience_distribution = (doc.goal_audience_distribution || []).map((row) => ({
      goal: row.goal || row.media_goal || "",
      target_audience: row.target_audience || "",
      selected: Number(row.selected ?? 1) !== 0,
      allocation_percentage: row.allocation_percentage ?? "",
      priority: row.priority || "",
      notes: row.notes || "",
    }));
    this.syncInferredDistribution();
    this.state.maxVisited = this.steps.length - 1;
    this.root.querySelector("[data-mpp-subtitle]").textContent = `${__("Editing")} · ${doc.name}`;
    this.root.querySelector("[data-mpp-open-form]").hidden = false;
    this.root.querySelector("[data-mpp-open-execution]").hidden = false;
  }

  async handleRouteChange() {
    const requestedPlan = frappe.utils.get_url_arg("media_plan") || null;
    if (!requestedPlan || requestedPlan === this.state.documentName || !this.root) return;
    this.setLoading(true, __("Loading Media Plan..."));
    try {
      await this.loadPlan(requestedPlan);
      this.renderStep();
      await this.loadWorkflowActions();
    } catch (error) {
      this.showError(this.errorMessage(error));
    } finally {
      this.setLoading(false);
    }
  }

  normalizeLoadedRow(row) {
    const result = { ...row };
    result._ref = row._ref || this.makeReference();
    result.goals = this.unique(row.goals || []);
    result.audiences = this.unique(row.audiences || []);
    return result;
  }

  currentWorkflowState() {
    const workflowDoc = this.state.workflowDoc || {};
    return workflowDoc[this.state.workflowStateField]
      || workflowDoc.workflow_state
      || workflowDoc.status
      || (Number(workflowDoc.docstatus) === 1 ? "Submitted" : "Draft");
  }

  async loadWorkflowActions() {
    const bar = this.root?.querySelector("[data-mpp-workflow-bar]");
    const host = this.root?.querySelector("[data-mpp-workflow-actions]");
    const stateLabel = this.root?.querySelector("[data-mpp-workflow-state]");
    if (!bar || !host || !stateLabel) return;

    host.innerHTML = "";
    this.state.workflowActions = [];
    if (!this.state.documentName) {
      bar.hidden = false;
      stateLabel.textContent = __("Draft");
      const message = document.createElement("small");
      message.className = "mpp-workflow-empty";
      message.textContent = __("Save the Media Plan first to activate workflow actions.");
      host.appendChild(message);
      return;
    }

    if (!this.state.workflowDoc) {
      bar.hidden = false;
      stateLabel.textContent = __("Draft");
      const message = document.createElement("small");
      message.className = "mpp-workflow-error";
      message.textContent = __("Reload the saved Media Plan to load workflow actions.");
      host.appendChild(message);
      return;
    }

    bar.hidden = false;
    stateLabel.textContent = __(this.currentWorkflowState());
    host.innerHTML = `<span class="mpp-workflow-loading">${this.escape(__("Loading workflow actions..."))}</span>`;

    try {
      const response = await frappe.call({
        method: "frappe.model.workflow.get_transitions",
        type: "POST",
        args: { doc: JSON.stringify(this.state.workflowDoc) },
      });
      const transitions = Array.isArray(response.message) ? response.message : [];
      this.state.workflowActions = transitions;
      host.innerHTML = "";

      transitions.forEach((transition) => {
        if (!transition?.action) return;
        const button = document.createElement("button");
        button.type = "button";
        button.className = `btn btn-sm mpp-workflow-button ${this.workflowActionClass(transition)}`;
        button.textContent = __(transition.action);
        if (transition.next_state) {
          button.title = `${__("Next State")}: ${__(transition.next_state)}`;
        }
        button.addEventListener("click", () => this.confirmWorkflowAction(transition, button));
        host.appendChild(button);
      });

      if (!host.children.length) {
        const message = document.createElement("small");
        message.className = "mpp-workflow-empty";
        message.textContent = __("No workflow actions are available for your role.");
        host.appendChild(message);
      }
    } catch (error) {
      host.innerHTML = "";
      const message = document.createElement("small");
      message.className = "mpp-workflow-error";
      message.textContent = __("Unable to load workflow actions.");
      host.appendChild(message);
      console.warn("Media Plan Wizard: workflow transitions unavailable.", error);
    }
  }

  workflowActionClass(transition) {
    const value = `${transition.action || ""} ${transition.next_state || ""}`.toLowerCase();
    if (/(reject|cancel|decline)/.test(value)) return "is-negative";
    if (/(approve|review|submit|complete)/.test(value)) return "is-positive";
    return "is-neutral";
  }

  confirmWorkflowAction(transition, button) {
    if (this.state.isApplyingWorkflow || !transition?.action) return;
    const message = __("Apply workflow action {0}?", [__(transition.action)]);
    frappe.confirm(message, () => this.applyWorkflowAction(transition.action, button));
  }

  async applyWorkflowAction(action, button) {
    if (this.state.isApplyingWorkflow || !this.state.workflowDoc) return;
    this.state.isApplyingWorkflow = true;
    this.root.querySelectorAll(".mpp-workflow-button").forEach((actionButton) => {
      actionButton.disabled = true;
    });
    if (button) button.classList.add("is-loading");
    frappe.dom.freeze(__("Applying workflow action..."));

    try {
      const response = await frappe.call({
        method: "frappe.model.workflow.apply_workflow",
        type: "POST",
        args: {
          doc: JSON.stringify(this.state.workflowDoc),
          action,
        },
      });
      if (!response.message) throw new Error(__("Workflow action failed."));

      await this.loadPlan(this.state.documentName);
      this.renderStep();
      await this.loadWorkflowActions();
      frappe.show_alert({ message: __("Workflow updated successfully."), indicator: "green" });
    } catch (error) {
      this.showError(this.errorMessage(error) || __("Workflow action failed."));
      await this.loadWorkflowActions();
    } finally {
      frappe.dom.unfreeze();
      this.state.isApplyingWorkflow = false;
    }
  }

  showStep(index, fromStepper) {
    if (index < 0 || index >= this.steps.length) return;
    this.clearAlert();
    this.state.maxVisited = Math.max(this.state.maxVisited, index);
    this.state.currentStep = index;
    if (index === 4 || index === 5) this.syncInferredDistribution();
    this.renderStep();
    this.root.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  renderStep() {
    this.controls.clear();
    const step = this.state.currentStep;
    if (step === 0) this.renderBasicStep();
    else if (step === 1) this.renderSourceStep("planned_production", "Media Production");
    else if (step === 2) this.renderSourceStep("planned_work_items", "Media Work Items");
    else if (step === 3) this.renderRiskOpportunityStep();
    else if (step === 4) this.renderDistributionStep();
    else this.renderPreviewStep();
    this.updateNavigation();
  }

  renderBasicStep() {
    const panel = this.panel();
    panel.innerHTML = this.panelHeader(
      "Basic Information",
      "Define the plan identity, owner, project and implementation period."
    ) + `<div class="mpp-form-grid" data-mpp-basic-grid></div>`;
    const fields = [
      { fieldname: "plan_name", label: "Plan Name", fieldtype: "Data", reqd: 1 },
      { fieldname: "plan_name_ar", label: "Project Name", fieldtype: "Data" },
      { fieldname: "project", label: "Project", fieldtype: "Link", options: "Project", reqd: 1 },
      { fieldname: "plan_owner", label: "Plan Owner", fieldtype: "Link", options: "User" },
      { fieldname: "start_date", label: "Start Date", fieldtype: "Date", reqd: 1 },
      { fieldname: "end_date", label: "End Date", fieldtype: "Date", reqd: 1 },
      {
        fieldname: "geographic_coverage",
        label: "Geographic Coverage",
        fieldtype: "Select",
        options: "محلي (محافظة واحدة)\nعدة محافظات\nدولي",
      },
      { fieldname: "priority", label: "Priority", fieldtype: "Select", options: "High\nMedium\nLow" },
      { fieldname: "description", label: "Description", fieldtype: "Small Text" },
    ].filter((df) => df.fieldname !== "geographic_coverage");
    const grid = panel.querySelector("[data-mpp-basic-grid]");
    fields.forEach((df) => {
      const control = this.makeControl(grid, df, this.state.basic[df.fieldname], (value) => {
        this.state.basic[df.fieldname] = value;
      });
      this.controls.set(`basic:${df.fieldname}`, control);
    });
    this.setControlsReadOnly(!this.state.canWrite);
  }

  renderSourceStep(key, title) {
    const panel = this.panel();
    const description = key === "planned_production"
      ? "Add every planned media product, then select its goal and target audience."
      : "Add coordination and execution work items, then select their goal and target audience.";
    panel.innerHTML = this.panelHeader(title, description) + `
      <div class="mpp-section-toolbar">
        <span class="mpp-record-count">${this.state[key].length} ${this.escape(__("items"))}</span>
        <button type="button" class="btn btn-primary btn-sm" data-mpp-add-source ${this.state.canWrite ? "" : "disabled"}>+ ${this.escape(__("Add Row"))}</button>
      </div>
      <div class="mpp-source-list" data-mpp-source-list></div>
    `;
    panel.querySelector("[data-mpp-add-source]").addEventListener("click", () => {
      this.state[key].push(this.newSourceRow(key));
      this.renderSourceStep(key, title);
      const cards = panel.querySelectorAll(".mpp-source-card");
      cards[cards.length - 1]?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
    if (!this.state[key].length) this.state[key].push(this.newSourceRow(key));
    const list = panel.querySelector("[data-mpp-source-list]");
    this.state[key].forEach((row, index) => this.renderSourceCard(list, key, row, index));
    this.setControlsReadOnly(!this.state.canWrite);
  }

  newSourceRow(key) {
    const targetFields = this.sourceTargetFields(key);
    const row = {
      _ref: this.makeReference(),
      planned_start_date: this.state.basic.start_date || "",
      planned_end_date: this.state.basic.end_date || "",
      goals: [],
      audiences: [],
      _open: true,
      _key: key,
    };
    if (targetFields.goal) row[targetFields.goal] = "";
    if (targetFields.audience) row[targetFields.audience] = "";
    return row;
  }

  renderSourceCard(host, key, row, index) {
    const card = document.createElement("article");
    card.className = "mpp-source-card";
    card.dataset.rowRef = row._ref;
    const summary = this.sourceSummary(key, row, index);
    card.innerHTML = `
      <header class="mpp-source-head">
        <button type="button" class="mpp-source-toggle" data-mpp-toggle-row>
          <span class="mpp-source-index">${index + 1}</span>
          <span><b data-mpp-row-summary>${this.escape(summary)}</b><small>${this.escape(__(key === "planned_production" ? "Media Production" : "Media Work Item"))}</small></span>
        </button>
        <button type="button" class="btn btn-xs btn-default mpp-danger" data-mpp-remove-row ${this.state.canWrite ? "" : "disabled"}>${this.escape(__("Remove"))}</button>
      </header>
      <div class="mpp-source-body" data-mpp-source-body>
        <div class="mpp-form-grid" data-mpp-row-fields></div>
      </div>
    `;
    host.appendChild(card);
    const body = card.querySelector("[data-mpp-source-body]");
    if (row._open === false) body.hidden = true;
    card.querySelector("[data-mpp-toggle-row]").addEventListener("click", () => {
      row._open = body.hidden;
      body.hidden = !body.hidden;
    });
    card.querySelector("[data-mpp-remove-row]").addEventListener("click", () => {
      this.state[key] = this.state[key].filter((item) => item._ref !== row._ref);
      this.renderSourceStep(key, key === "planned_production" ? "Media Production" : "Media Work Items");
    });

    const fieldsHost = card.querySelector("[data-mpp-row-fields]");
    const targetFields = this.sourceTargetFields(key);
    (this.state.metadata[key] || []).forEach((df) => {
      const control = this.makeControl(fieldsHost, df, row[df.fieldname] ?? df.default ?? "", async (value) => {
        row[df.fieldname] = value;
        if (df.fieldname === targetFields.goal) row.goals = value ? [value] : [];
        if (df.fieldname === targetFields.audience) row.audiences = value ? [value] : [];
        card.querySelector("[data-mpp-row-summary]").textContent = this.sourceSummary(key, row, index);
        if (key === "planned_production" && df.fieldname === "material" && value) {
          await this.fillMaterialDefaults(row, card, value);
        }
      });
      this.controls.set(`${key}:${row._ref}:${df.fieldname}`, control);
    });
  }

  async fillMaterialDefaults(row, card, material) {
    try {
      const result = await frappe.db.get_value(
        "Media Product Catalog",
        material,
        ["material_type", "standard_weight"]
      );
      const values = result.message || {};
      row.material_type = values.material_type || row.material_type || "";
      row.weight_percent = values.standard_weight ?? row.weight_percent ?? "";
      row.material_name = row.material_name || material;
      ["material_type", "weight_percent", "material_name"].forEach((fieldname) => {
        const control = this.controls.get(`planned_production:${row._ref}:${fieldname}`);
        if (control && row[fieldname] !== undefined) control.set_value(row[fieldname]);
      });
    } catch (error) {
      this.showError(this.errorMessage(error));
    }
  }

  renderRiskOpportunityStep() {
    const panel = this.panel();
    panel.innerHTML = this.panelHeader(
      "Opportunities and Risks",
      "Record the conditions that may help or hinder successful execution."
    ) + `<div class="mpp-split-sections"><section data-simple-section="opportunities"></section><section data-simple-section="risks"></section></div>`;
    this.renderSimpleSection(panel.querySelector("[data-simple-section='opportunities']"), "opportunities", "Opportunities");
    this.renderSimpleSection(panel.querySelector("[data-simple-section='risks']"), "risks", "Risks");
    this.setControlsReadOnly(!this.state.canWrite);
  }

  renderSimpleSection(host, key, title) {
    host.className = "mpp-simple-section";
    host.innerHTML = `
      <div class="mpp-section-toolbar"><h3>${this.escape(__(title))}</h3><button type="button" class="btn btn-default btn-sm" data-add-simple ${this.state.canWrite ? "" : "disabled"}>+ ${this.escape(__("Add Row"))}</button></div>
      <div data-simple-list></div>
    `;
    host.querySelector("[data-add-simple]").addEventListener("click", () => {
      this.state[key].push({ _ref: this.makeReference() });
      this.renderRiskOpportunityStep();
    });
    if (!this.state[key].length) this.state[key].push({ _ref: this.makeReference() });
    const list = host.querySelector("[data-simple-list]");
    this.state[key].forEach((row, index) => {
      const item = document.createElement("article");
      item.className = "mpp-simple-row";
      item.innerHTML = `<div class="mpp-simple-row-head"><b>${this.escape(__(title))} ${index + 1}</b><button type="button" class="btn btn-xs btn-default mpp-danger" ${this.state.canWrite ? "" : "disabled"}>${this.escape(__("Remove"))}</button></div><div class="mpp-form-grid"></div>`;
      item.querySelector("button").addEventListener("click", () => {
        this.state[key] = this.state[key].filter((candidate) => candidate._ref !== row._ref);
        this.renderRiskOpportunityStep();
      });
      const grid = item.querySelector(".mpp-form-grid");
      (this.state.metadata[key] || []).forEach((df) => {
        const control = this.makeControl(grid, df, row[df.fieldname] ?? df.default ?? "", (value) => {
          row[df.fieldname] = value;
        });
        this.controls.set(`${key}:${row._ref}:${df.fieldname}`, control);
      });
      list.appendChild(item);
    });
  }

  syncInferredDistribution() {
    const goals = [];
    const audiences = [];
    const allowedPairs = new Map();
    ["planned_production", "planned_work_items"].forEach((key) => {
      this.state[key].forEach((row) => {
        const rowGoals = this.unique(row.goals || []);
        const rowAudiences = this.unique(row.audiences || []);
        rowGoals.forEach((goal) => {
          if (!goals.includes(goal)) goals.push(goal);
          rowAudiences.forEach((audience) => {
            const key = this.relationKey(goal, audience);
            if (!allowedPairs.has(key)) allowedPairs.set(key, { goal, targetAudience: audience });
          });
        });
        rowAudiences.forEach((audience) => { if (!audiences.includes(audience)) audiences.push(audience); });
      });
    });
    const existingGoals = new Map((this.state.inferred_goals || []).map((row) => [row.media_goal || row.goal, row]));
    this.state.inferred_goals = goals.map((goal) => ({
      media_goal: goal,
      goal_type: existingGoals.get(goal)?.goal_type || "Short Term",
      priority: existingGoals.get(goal)?.priority || "",
    }));
    this.state.inferred_audiences = audiences;

    const existing = new Map(
      (this.state.goal_audience_distribution || []).map((row) => [
        this.relationKey(row.goal || row.media_goal, row.target_audience),
        row,
      ])
    );
    this.state.goal_audience_distribution = Array.from(allowedPairs.entries()).map(([key, relation]) => {
      const { goal, targetAudience } = relation;
      const previous = existing.get(key) || {};
      return {
        goal,
        target_audience: targetAudience,
        selected: previous.selected ?? true,
        allocation_percentage: previous.allocation_percentage ?? "",
        priority: previous.priority || "",
        notes: previous.notes || "",
      };
    });
  }

  renderDistributionStep() {
    const panel = this.panel();
    panel.innerHTML = this.panelHeader(
      "Goals and Target Audience Distribution",
      "Goals and audiences below were inferred from Media Production and Media Work Items."
    ) + `<div data-distribution-content></div>`;
    const content = panel.querySelector("[data-distribution-content]");
    if (!this.state.inferred_goals.length) {
      content.innerHTML = `<div class="mpp-empty-state"><h3>${this.escape(__("No inferred goals"))}</h3><p>${this.escape(__("No goals or target audiences were inferred. You can continue when these fields are optional."))}</p></div>`;
      return;
    }
    content.innerHTML = `<div class="mpp-inference-summary"><span>${this.state.inferred_goals.length} ${this.escape(__("goals"))}</span><span>${this.state.inferred_audiences.length} ${this.escape(__("target audiences"))}</span><span>${this.state.goal_audience_distribution.length} ${this.escape(__("relations"))}</span></div><div class="mpp-goal-grid" data-goal-grid></div>`;
    const grid = content.querySelector("[data-goal-grid]");
    this.state.inferred_goals.forEach((goalRow) => {
      const goal = goalRow.media_goal;
      const rows = this.state.goal_audience_distribution.filter((row) => row.goal === goal);
      const total = rows.reduce((sum, row) => sum + (row.allocation_percentage === "" ? 0 : Number(row.allocation_percentage || 0)), 0);
      const hasPercentages = rows.some((row) => row.allocation_percentage !== "" && row.allocation_percentage !== null);
      const status = !hasPercentages ? "is-pending" : Math.abs(total - 100) <= 0.01 ? "is-valid" : "is-invalid";
      const card = document.createElement("article");
      card.className = `mpp-goal-card ${status}`;
      card.innerHTML = `
        <header><div><span>${this.escape(__("Media Goal"))}</span><h3>${this.escape(goal)}</h3></div><label><span>${this.escape(__("Goal Type"))}</span><select data-goal-type ${this.state.canWrite ? "" : "disabled"}><option value="Short Term" ${goalRow.goal_type === "Short Term" ? "selected" : ""}>${this.escape(__("Short Term"))}</option><option value="Long Term" ${goalRow.goal_type === "Long Term" ? "selected" : ""}>${this.escape(__("Long Term"))}</option></select></label></header>
        <div class="mpp-allocation-list">
          ${rows.map((row) => `<label class="mpp-allocation-row"><span>${this.escape(row.target_audience)}</span><span class="mpp-percent-input"><input type="number" min="0" max="100" step="0.01" value="${this.escapeAttribute(row.allocation_percentage)}" data-allocation-audience="${this.escapeAttribute(row.target_audience)}" ${this.state.canWrite ? "" : "disabled"}><b>%</b></span></label>`).join("")}
        </div>
        <footer><span>${this.escape(__("Total"))}</span><strong data-goal-total>${total.toFixed(2).replace(".00", "")}%</strong><small>${this.escape(!hasPercentages ? __("Percentages are optional. If entered, the total must equal 100%." ) : Math.abs(total - 100) <= 0.01 ? __("Distribution is complete.") : __("The total must equal 100%."))}</small></footer>
      `;
      card.querySelector("[data-goal-type]").addEventListener("change", (event) => {
        goalRow.goal_type = event.target.value;
      });
      card.querySelectorAll("[data-allocation-audience]").forEach((input) => {
        input.addEventListener("change", () => {
          const row = rows.find((item) => item.target_audience === input.dataset.allocationAudience);
          row.allocation_percentage = input.value;
          this.renderDistributionStep();
        });
      });
      grid.appendChild(card);
    });
  }

  renderPreviewStep() {
    const panel = this.panel();
    const production = this.nonEmptyRows("planned_production");
    const workItems = this.nonEmptyRows("planned_work_items");
    const risks = this.nonEmptyRows("risks");
    const opportunities = this.nonEmptyRows("opportunities");
    panel.innerHTML = this.panelHeader(
      "Preview",
      "Review the inferred strategy and execution scope before saving."
    ) + `
      <div class="mpp-preview-hero"><div><span>${this.escape(__("Media Plan"))}</span><h2>${this.escape(this.state.basic.plan_name || __("Untitled Plan"))}</h2><p>${this.escape(this.state.basic.description || __("No description"))}</p></div><div><b>${this.escape(this.state.basic.start_date || "—")}</b><span>→</span><b>${this.escape(this.state.basic.end_date || "—")}</b></div></div>
      <div class="mpp-preview-kpis">
        ${this.previewKpi(production.length, "Media Products")}
        ${this.previewKpi(workItems.length, "Media Work Items")}
        ${this.previewKpi(this.state.inferred_goals.length, "Media Goals")}
        ${this.previewKpi(this.state.inferred_audiences.length, "Target Audiences")}
        ${this.previewKpi(opportunities.length, "Opportunities")}
        ${this.previewKpi(risks.length, "Risks")}
      </div>
      <div class="mpp-preview-sections">
        ${this.previewExecutionSection("Media Production", production, "planned_production")}
        ${this.previewExecutionSection("Media Work Items", workItems, "planned_work_items")}
        ${this.previewDistributionSection()}
      </div>
    `;
  }

  previewKpi(value, label) {
    return `<div class="mpp-preview-kpi"><strong>${value}</strong><span>${this.escape(__(label))}</span></div>`;
  }

  previewExecutionSection(title, rows, key) {
    const cards = rows.length ? rows.map((row, index) => `
      <div class="mpp-preview-row"><span>${index + 1}</span><div><b>${this.escape(this.sourceSummary(key, row, index))}</b><small>${this.escape((row.goals || []).join("، "))}</small><small>${this.escape((row.audiences || []).join("، "))}</small></div></div>
    `).join("") : `<p class="mpp-empty-inline">${this.escape(__("No items"))}</p>`;
    return `<section class="mpp-preview-section"><h3>${this.escape(__(title))}</h3>${cards}</section>`;
  }

  previewDistributionSection() {
    return `<section class="mpp-preview-section"><h3>${this.escape(__("Audience Distribution by Goal"))}</h3>${this.state.inferred_goals.map((goal) => {
      const rows = this.state.goal_audience_distribution.filter((row) => row.goal === goal.media_goal);
      return `<div class="mpp-preview-goal"><b>${this.escape(goal.media_goal)}</b><div>${rows.map((row) => `<span>${this.escape(row.target_audience)}${row.allocation_percentage !== "" ? ` · ${this.escape(row.allocation_percentage)}%` : ""}</span>`).join("")}</div></div>`;
    }).join("")}</section>`;
  }

  validateStep(step) {
    this.clearAlert();
    if (step === 0) return this.validateBasic();
    if (step === 1) return this.validateSourceRows("planned_production");
    if (step === 2) return this.validateSourceRows("planned_work_items");
    if (step === 3) return this.validateSimpleRows();
    if (step === 4) return this.validateDistribution();
    return true;
  }

  validateBasic() {
    const required = ["plan_name", "project", "start_date", "end_date"];
    for (const fieldname of required) {
      if (!this.state.basic[fieldname]) {
        this.showError(__("Complete all required basic information fields."));
        return false;
      }
    }
    if (frappe.datetime.str_to_obj(this.state.basic.end_date) < frappe.datetime.str_to_obj(this.state.basic.start_date)) {
      this.showError(__("End Date cannot be before Start Date."));
      return false;
    }
    return true;
  }

  validateSourceRows(key) {
    const rows = this.nonEmptyRows(key);
    const metadata = this.state.metadata[key] || [];
    for (const row of rows) {
      for (const df of metadata.filter((field) => field.reqd)) {
        if (row[df.fieldname] === undefined || row[df.fieldname] === null || row[df.fieldname] === "") {
          this.showError(`${__(df.label)}: ${__("This field is required.")}`);
          return false;
        }
      }
      const start = row.planned_start_date || this.state.basic.start_date;
      const end = row.planned_end_date || this.state.basic.end_date;
      if (start && end && frappe.datetime.str_to_obj(end) < frappe.datetime.str_to_obj(start)) {
        this.showError(__("Planned End Date cannot be before Planned Start Date."));
        return false;
      }
    }
    return true;
  }

  validateSimpleRows() {
    for (const key of ["risks", "opportunities"]) {
      const metadata = this.state.metadata[key] || [];
      for (const row of this.nonEmptyRows(key)) {
        for (const df of metadata.filter((field) => field.reqd)) {
          if (!row[df.fieldname]) {
            this.showError(`${__(df.label)}: ${__("This field is required.")}`);
            return false;
          }
        }
      }
    }
    return true;
  }

  validateDistribution() {
    this.syncInferredDistribution();
    for (const goal of this.state.inferred_goals) {
      const rows = this.state.goal_audience_distribution.filter((row) => row.goal === goal.media_goal);
      const percentages = rows.filter((row) => row.allocation_percentage !== "" && row.allocation_percentage !== null);
      if (!percentages.length) continue;
      if (percentages.length !== rows.length) {
        this.showError(`${goal.media_goal}: ${__("Enter percentages for all inferred audiences or leave all percentages empty.")}`);
        return false;
      }
      const total = percentages.reduce((sum, row) => sum + Number(row.allocation_percentage || 0), 0);
      if (total < 99.99 || total > 100.01) {
        this.showError(`${goal.media_goal}: ${__("The audience allocation total must equal 100%.")} (${total}%)`);
        return false;
      }
    }
    return true;
  }

  async savePlan() {
    for (let step = 0; step < 5; step += 1) {
      if (!this.validateStep(step)) {
        this.showStep(step, true);
        return;
      }
    }
    if (!this.state.canWrite || this.state.isSaving) return;
    this.state.isSaving = true;
    this.updateNavigation();
    frappe.dom.freeze(__("Saving Media Plan..."));
    try {
      const response = await frappe.call({
        method: "press_affairs_app.moi.page.media_plan_wizard.media_plan_wizard.save_plan",
        args: {
          name: this.state.documentName || null,
          expected_modified: this.state.modified || null,
          payload: JSON.stringify(this.buildPayload()),
        },
      });
      const result = response.message || {};
      this.state.documentName = result.name;
      this.state.modified = result.modified || this.state.modified;
      this.root.querySelector("[data-mpp-open-form]").hidden = false;
      frappe.show_alert({ message: __("Media Plan saved successfully."), indicator: "green" });
      window.location.assign(`/app/media-plan-wizard?media_plan=${encodeURIComponent(result.name)}`);
    } catch (error) {
      this.showError(this.errorMessage(error));
    } finally {
      frappe.dom.unfreeze();
      this.state.isSaving = false;
      this.updateNavigation();
    }
  }

  buildPayload() {
    this.syncInferredDistribution();
    return {
      ...this.state.basic,
      planned_production: this.nonEmptyRows("planned_production").map((row) => this.cleanStateRow(row)),
      planned_work_items: this.nonEmptyRows("planned_work_items").map((row) => this.cleanStateRow(row)),
      risks: this.nonEmptyRows("risks").map((row) => this.cleanStateRow(row)),
      opportunities: this.nonEmptyRows("opportunities").map((row) => this.cleanStateRow(row)),
      inferred_goals: this.state.inferred_goals.map((row) => ({ ...row })),
      goal_audience_distribution: this.state.goal_audience_distribution.map((row) => ({ ...row, selected: 1 })),
    };
  }

  cleanStateRow(row) {
    const clean = {};
    Object.keys(row).forEach((key) => {
      if (!key.startsWith("_")) clean[key] = row[key];
    });
    return clean;
  }

  updateNavigation() {
    const step = this.state.currentStep;
    this.root.querySelector("[data-mpp-step-count]").textContent = `${step + 1} / ${this.steps.length}`;
    this.root.querySelector("[data-mpp-action='previous']").disabled = step === 0 || this.state.isSaving;
    this.root.querySelector("[data-mpp-action='next']").hidden = step === this.steps.length - 1;
    const save = this.root.querySelector("[data-mpp-action='save']");
    save.hidden = step !== this.steps.length - 1;
    save.disabled = !this.state.canWrite || this.state.isSaving;
    this.root.querySelectorAll("[data-mpp-step]").forEach((button) => {
      const index = Number(button.dataset.mppStep);
      button.classList.toggle("is-active", index === step);
      button.classList.toggle("is-complete", index < step || index <= this.state.maxVisited && index !== step);
      button.classList.toggle("is-clickable", Boolean(this.state.documentName) || index <= this.state.maxVisited + 1);
    });
  }

  makeControl(parent, df, value, onChange) {
    const holder = document.createElement("div");
    holder.className = "mpp-control";
    parent.appendChild(holder);
    const control = frappe.ui.form.make_control({
      parent: holder,
      df: { ...df, label: __(df.label || df.fieldname) },
      render_input: true,
    });
    control.refresh();
    if (value !== undefined && value !== null) control.set_value(value);
    if (control.$input) {
      control.$input.on("change input awesomplete-selectcomplete", () => onChange(control.get_value()));
    }
    return control;
  }

  setControlsReadOnly(readOnly) {
    if (!readOnly) return;
    this.controls.forEach((control) => {
      if (control.df) control.df.read_only = 1;
      control.refresh();
    });
    this.root.querySelectorAll("input, select, textarea, button[data-mpp-target-add], button[data-chip-value]").forEach((element) => {
      element.disabled = true;
    });
  }

  nonEmptyRows(key) {
    const metadata = this.state.metadata[key] || [];
    return (this.state[key] || []).filter((row) => {
      if ((row.goals || []).length || (row.audiences || []).length) return true;
      return metadata.some((df) => {
        if (["planned_start_date", "planned_end_date"].includes(df.fieldname)) return false;
        return row[df.fieldname] !== undefined && row[df.fieldname] !== null && row[df.fieldname] !== "";
      });
    });
  }

  sourceSummary(key, row, index) {
    if (key === "planned_production") return row.material_name || row.material || `${__("Media Product")} ${index + 1}`;
    return row.work_item_title || row.work_item_type || `${__("Media Work Item")} ${index + 1}`;
  }

  sourceTargetFields(key) {
    const fields = this.state.metadata[key] || [];
    return {
      goal: fields.find((df) => df.fieldtype === "Link" && df.options === "Media Goal")?.fieldname || null,
      audience: fields.find((df) => df.fieldtype === "Link" && df.options === "Target Audience")?.fieldname || null,
    };
  }

  panelHeader(title, description) {
    return `<header class="mpp-panel-head"><span>${this.state.currentStep + 1}</span><div><h2>${this.escape(__(title))}</h2><p>${this.escape(__(description))}</p></div></header>`;
  }

  panel() {
    return this.root.querySelector("[data-mpp-panel]");
  }

  setLoading(loading, text = "") {
    const loader = this.root.querySelector("[data-mpp-loading]");
    loader.hidden = !loading;
    loader.querySelector("[data-mpp-loading-text]").textContent = text;
  }

  showError(message) {
    const alert = this.root.querySelector("[data-mpp-alert]");
    alert.hidden = false;
    alert.textContent = message;
    alert.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  clearAlert() {
    this.root.querySelector("[data-mpp-alert]").hidden = true;
  }

  errorMessage(error) {
    return error?.message || error?._server_messages || __("An unexpected error occurred.");
  }

  unique(values) {
    return Array.from(new Set((values || []).map((value) => String(value || "").trim()).filter(Boolean)));
  }

  relationKey(goal, targetAudience) {
    return JSON.stringify([String(goal || ""), String(targetAudience || "")]);
  }

  makeReference() {
    if (window.crypto?.randomUUID) return window.crypto.randomUUID();
    return `row_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
  }

  escape(value) {
    return frappe.utils.escape_html(String(value ?? ""));
  }

  escapeAttribute(value) {
    return this.escape(value).replace(/`/g, "&#96;");
  }
}
