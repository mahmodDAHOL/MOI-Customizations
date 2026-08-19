// File: task_board.js
// Place this in your ERPNext custom scripts or as a Page script

frappe.pages['my-tasks'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('my tasks'),
        single_column: true
    });

    // Create container for the my tasks
    let container = $('<div id="my-tasks-container"></div>').appendTo(page.body);
    
    // Load the my tasks
    loadTaskBoard(container[0]);
};

function loadTaskBoard(container) {
    // Configuration
    const CONFIG = {
        doctype: "Task",
        dateField: "exp_end_date",
        defaultLang: frappe.boot.user.language || "en",
        defaultGroup: "status",
        maxRows: 500,
        quickAdd: true,
        rememberFilters: true,
        liveUpdates: true,
        assignFromBoard: true
    };

    // Status colors
    const STATUS_COLOR = {
        "Open": "#C4B69C",
        "Working": "#1C615D",
        "Pending Review": "#948065",
        "Overdue": "#9C4A3C",
        "Completed": "#0E4442",
        "Cancelled": "#8A9694"
    };

    const PRIORITY_COLOR = {
        "Low": "#77B0A8",
        "Medium": "#948065",
        "High": "#B4713F",
        "Urgent": "#9C4A3C"
    };

    const PRIORITY_RANK = {
        "Urgent": 0,
        "High": 1,
        "Medium": 2,
        "Low": 3
    };

    // Translations
    const STR = {
        en: {
            title: "my tasks",
            subtitle: "Ministry of Information · IT & Digital Transformation Directorate",
            refresh: "Refresh",
            export: "Excel",
            exportCsv: "CSV",
            langLabel: "ع",
            groupBy: "Group by",
            tree: "Tree",
            treeTitle: "Projects & tasks",
            treeEmpty: "No project matches the filters.",
            treeNoMatch: "Nothing matches in the tree.",
            treeSearchPh: "Search the tree…",
            newProject: "Project",
            addProject: "Project",
            expandAll: "Expand all",
            collapseAll: "Collapse all",
            edit: "Edit",
            addChild: "Add child",
            addTask: "New task",
            addMultiple: "Add multiple",
            del: "Delete",
            filterBoard: "Filter board",
            showOnBoard: "Show on board",
            askProject: "New project name",
            askTask: "Task subject",
            askMultiple: "One subject per line",
            askDelete: (n) => `Delete "${n}" permanently?`,
            projectAdded: "Project created",
            taskAdded: "Task created",
            tasksAdded: (n) => `${n} tasks created`,
            deleted: "Deleted",
            openForm: "Open",
            subtasks: "subtasks",
            g_status: "Status",
            g_date: "Due date",
            g_priority: "Priority",
            g_assignee: "Assignee",
            g_project: "Project",
            searchPh: "Search…",
            filters: "Filters",
            clearAll: "Clear all",
            fStatus: "Status",
            fPriority: "Priority",
            fProject: "Project",
            fAssignee: "Assigned to",
            fDue: "Due range",
            fSort: "Sort",
            fViews: "Saved views",
            saveView: "Save",
            delView: "Delete",
            viewNamePh: "View name",
            viewSaved: "View saved",
            viewDeleted: "View deleted",
            noViews: "No saved view",
            mine: "My tasks",
            openOnly: "Not done only",
            unassigned: "Unassigned",
            any: "Any",
            noProject: "No project",
            noPriority: "No priority",
            noAssignee: "Unassigned",
            preset_: "Custom range",
            preset_overdue: "Overdue",
            preset_today: "Today",
            preset_week: "This week",
            preset_month: "This month",
            preset_next7: "Next 7 days",
            preset_next30: "Next 30 days",
            preset_none: "No due date",
            sort_due_asc: "Due · soonest first",
            sort_due_desc: "Due · latest first",
            sort_priority: "Priority",
            sort_modified: "Last modified",
            sort_subject: "Subject A–Z",
            from: "From",
            to: "To",
            search: "Search",
            k_open: "In progress",
            k_overdue: "Overdue",
            k_today: "Due today",
            k_week: "This week",
            k_unassigned: "Unassigned",
            k_done: "Done this week",
            k_doneTip: "Completed tasks last modified within the current week",
            counted: (n, m) => `Showing ${n} of ${m} tasks`,
            noMatch: "No task matches the current filters.",
            addPh: "New task…",
            empty: "Nothing here",
            dropHere: "Drop here",
            overdue: "Overdue",
            today: "Today",
            week: "This week",
            month: "This month",
            later: "Later",
            none: "No due date",
            dueToday: "Today",
            dueTomorrow: "Tomorrow",
            dueIn: (n) => `in ${n} days`,
            lateBy: (n) => n === 1 ? "1 day late" : `${n} days late`,
            mMove: "Move to",
            mPriority: "Priority",
            mDue: "Due",
            mAssign: "Assignment",
            mOpen: "Open task",
            mToMe: "Assign to me",
            mClearDue: "Clear date",
            mTomorrow: "Tomorrow",
            mEndWeek: "End of week",
            mNextWeek: "Next week",
            mPickUser: "Pick a user…",
            mAssignBtn: "Assign",
            moved: (s) => `Moved to ${s}`,
            dated: (d) => `Due date set to ${d}`,
            cleared: "Due date cleared",
            added: "Task added",
            prioSet: (p) => `Priority set to ${p}`,
            assigned: (u) => `Assigned to ${u}`,
            unassignedOk: "Assignment removed",
            errLoad: "Could not load tasks.",
            errSave: "Not saved: ",
            lockedCol: "This column is read-only — you cannot drop into it.",
            lockedOverdue: "Overdue is derived automatically — you cannot drop into it.",
            capped: `First ${CONFIG.maxRows} tasks`,
            exported: "Exported the visible tasks",
            xlTitle: "my tasks — export",
            xlSummary: "Executive summary",
            xlPivot: "Interactive analysis — use the PivotTable filters above",
            xlPivotName: "Task analysis",
            shData: "Tasks",
            shPivot: "Analysis",
            shSummary: "Summary",
            colId: "ID",
            colSubject: "Subject",
            colBucket: "Period",
            colDue: "Due date",
            colLate: "Days late",
            colProgress: "Progress",
            colModified: "Modified",
            total: "Total",
            count: "Count",
            notSet: "(not set)",
            values: "Values",
            countOf: "Task count",
            kpiTitle: "Indicators",
            crossTitle: "Status × Priority",
            stampOn: "Exported on",
            noFilters: "no filters",
            includeDone: "including completed",
            xlBusy: "Preparing the file…",
            hint: "Drag cards between columns, or use ⋮ to move and assign. Shortcuts: / search · f filters · r refresh"
        },
        ar: {
            title: "لوحة المهام",
            subtitle: "وزارة الإعلام · مديرية تقانة المعلومات والتحول الرقمي",
            refresh: "تحديث",
            export: "Excel",
            exportCsv: "CSV",
            langLabel: "EN",
            groupBy: "التجميع",
            tree: "الشجرة",
            treeTitle: "المشاريع والمهام",
            treeEmpty: "لا مشروع يطابق المرشّحات.",
            treeNoMatch: "لا نتيجة في الشجرة.",
            treeSearchPh: "بحث في الشجرة…",
            newProject: "مشروع",
            addProject: "مشروع",
            expandAll: "توسيع الكل",
            collapseAll: "طيّ الكل",
            edit: "تعديل",
            addChild: "مهمة فرعية",
            addTask: "مهمة جديدة",
            addMultiple: "إضافة متعددة",
            del: "حذف",
            filterBoard: "تصفية اللوحة",
            showOnBoard: "إظهار في اللوحة",
            askProject: "اسم المشروع الجديد",
            askTask: "عنوان المهمة",
            askMultiple: "عنوان في كل سطر",
            askDelete: (n) => `حذف «${n}» نهائياً؟`,
            projectAdded: "أُنشئ المشروع",
            taskAdded: "أُنشئت المهمة",
            tasksAdded: (n) => `أُنشئت ${n} مهمة`,
            deleted: "حُذف العنصر",
            openForm: "فتح",
            subtasks: "مهام فرعية",
            g_status: "الحالة",
            g_date: "تاريخ الاستحقاق",
            g_priority: "الأولوية",
            g_assignee: "المُسنَد إليه",
            g_project: "المشروع",
            searchPh: "بحث…",
            filters: "المرشّحات",
            clearAll: "مسح الكل",
            fStatus: "الحالة",
            fPriority: "الأولوية",
            fProject: "المشروع",
            fAssignee: "مُسنَدة إلى",
            fDue: "مدى الاستحقاق",
            fSort: "الترتيب",
            fViews: "العروض المحفوظة",
            saveView: "حفظ",
            delView: "حذف",
            viewNamePh: "اسم العرض",
            viewSaved: "حُفظ العرض",
            viewDeleted: "حُذف العرض",
            noViews: "بلا عرض محفوظ",
            mine: "مهامي",
            openOnly: "غير المكتملة فقط",
            unassigned: "غير مُسنَدة",
            any: "الكل",
            noProject: "بلا مشروع",
            noPriority: "بلا أولوية",
            noAssignee: "غير مُسنَدة",
            preset_: "مدى مخصّص",
            preset_overdue: "متأخرة",
            preset_today: "اليوم",
            preset_week: "هذا الأسبوع",
            preset_month: "هذا الشهر",
            preset_next7: "خلال 7 أيام",
            preset_next30: "خلال 30 يوماً",
            preset_none: "بلا تاريخ",
            sort_due_asc: "الاستحقاق · الأقرب أولاً",
            sort_due_desc: "الاستحقاق · الأبعد أولاً",
            sort_priority: "الأولوية",
            sort_modified: "آخر تعديل",
            sort_subject: "العنوان أبجدياً",
            from: "من",
            to: "إلى",
            search: "بحث",
            k_open: "قيد الإنجاز",
            k_overdue: "متأخرة",
            k_today: "تستحق اليوم",
            k_week: "هذا الأسبوع",
            k_unassigned: "غير مُسنَدة",
            k_done: "أُنجزت هذا الأسبوع",
            k_doneTip: "مهام مكتملة آخر تعديل عليها ضمن الأسبوع الجاري",
            counted: (n, m) => `معروض ${n} من ${m} مهمة`,
            noMatch: "لا مهمة تطابق المرشّحات الحالية.",
            addPh: "مهمة جديدة…",
            empty: "لا مهام هنا",
            dropHere: "أفلت هنا",
            overdue: "متأخرة",
            today: "اليوم",
            week: "هذا الأسبوع",
            month: "هذا الشهر",
            later: "لاحقاً",
            none: "بلا تاريخ",
            dueToday: "اليوم",
            dueTomorrow: "غداً",
            dueIn: (n) => `بعد ${n} أيام`,
            lateBy: (n) => n === 1 ? "متأخرة يوماً" : `متأخرة ${n} يوماً`,
            mMove: "نقل إلى",
            mPriority: "الأولوية",
            mDue: "الاستحقاق",
            mAssign: "الإسناد",
            mOpen: "فتح المهمة",
            mToMe: "إسنادها لي",
            mClearDue: "إزالة التاريخ",
            mTomorrow: "غداً",
            mEndWeek: "نهاية الأسبوع",
            mNextWeek: "الأسبوع القادم",
            mPickUser: "اختر مستخدماً…",
            mAssignBtn: "إسناد",
            moved: (s) => `نُقلت إلى ${s}`,
            dated: (d) => `أصبح الاستحقاق ${d}`,
            cleared: "أُزيل تاريخ الاستحقاق",
            added: "أُضيفت المهمة",
            prioSet: (p) => `الأولوية الآن ${p}`,
            assigned: (u) => `أُسنِدت إلى ${u}`,
            unassignedOk: "أُزيل الإسناد",
            errLoad: "تعذّر تحميل المهام.",
            errSave: "لم يُحفظ التغيير: ",
            lockedCol: "هذا العمود للقراءة فقط — لا يمكن الإفلات فيه.",
            lockedOverdue: "عمود المتأخرة يُحسب تلقائياً — لا يمكن الإفلات فيه.",
            capped: `أول ${CONFIG.maxRows} مهمة`,
            exported: "صُدِّرت المهام المعروضة",
            xlTitle: "لوحة المهام — تصدير",
            xlSummary: "الملخص التنفيذي",
            xlPivot: "التحليل التفاعلي — استخدم مرشّحات الجدول المحوري أعلاه",
            xlPivotName: "تحليل المهام",
            shData: "المهام",
            shPivot: "التحليل",
            shSummary: "الملخص",
            colId: "الرقم",
            colSubject: "العنوان",
            colBucket: "الفترة",
            colDue: "تاريخ الاستحقاق",
            colLate: "التأخير (أيام)",
            colProgress: "الإنجاز",
            colModified: "آخر تعديل",
            total: "الإجمالي",
            count: "العدد",
            notSet: "(غير محدّد)",
            values: "القيم",
            countOf: "عدد المهام",
            kpiTitle: "المؤشرات",
            crossTitle: "الحالة × الأولوية",
            stampOn: "صُدِّر في",
            noFilters: "بلا مرشّحات",
            includeDone: "بما فيها المكتملة",
            xlBusy: "جارٍ تجهيز الملف…",
            hint: "اسحب البطاقة بين الأعمدة، أو استخدم زر ⋮ للنقل والإسناد · اختصارات: / بحث · f مرشّحات · r تحديث"
        }
    };

    // State
    let lang = frappe.boot.user.language || 'en';
    let group = 'status';
    let tasks = [];
    let statuses = [];
    let priorities = [];
    let projects = [];
    let assignees = [];
    let users = [];
    let projectDocs = [];
    let loadError = null;
    let dragging = false;
    let menuOpen = false;

    const F = {
        q: "",
        status: "",
        priority: "",
        project: "",
        assignee: "",
        preset: "",
        from: "",
        to: "",
        sort: "due_asc",
        mine: false,
        open: true,
        unassigned: false
    };

    const BLANK = Object.assign({}, F);
    const DATE_COLS = [
        { key: "overdue", color: "#9C4A3C", locked: true, canAdd: false },
        { key: "today", color: "#1C615D", locked: false, canAdd: true },
        { key: "week", color: "#2F8078", locked: false, canAdd: true },
        { key: "month", color: "#948065", locked: false, canAdd: true },
        { key: "later", color: "#C4B69C", locked: false, canAdd: true },
        { key: "none", color: "#8A9694", locked: false, canAdd: true }
    ];
    const GROUPS = ["status", "date", "priority", "assignee", "project"];
    const PRESETS = ["", "overdue", "today", "week", "month", "next7", "next30", "none"];
    const SORTS = ["due_asc", "due_desc", "priority", "modified", "subject"];
    const NONE_KEY = "__none__";
    const C = {
        teal: "#1C615D",
        tealDeep: "#0E4442",
        tealMid: "#2F8078",
        tealSoft: "#77B0A8",
        bronze: "#948065",
        bronzeSoft: "#C4B69C",
        grey: "#8A9694",
        alert: "#9C4A3C"
    };

    const AR = {
        "Open": "مفتوحة",
        "Working": "قيد العمل",
        "Pending Review": "بانتظار المراجعة",
        "Overdue": "متأخرة",
        "Completed": "مكتملة",
        "Cancelled": "ملغاة",
        "Low": "منخفضة",
        "Medium": "متوسطة",
        "High": "عالية",
        "Urgent": "عاجلة"
    };

    const t = (key, ...args) => {
        const s = STR[lang] || STR.en;
        const val = s[key];
        if (typeof val === 'function') return val(...args);
        return val || key;
    };

    const esc = (s) => {
        if (!s) return '';
        return String(s).replace(/[&<>"']/g, (c) => {
            const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
            return map[c] || c;
        });
    };

    const tr = (s) => {
        if (lang === 'ar' && AR[s]) return AR[s];
        return s;
    };

    const me = () => frappe.session.user || '';

    // Date helpers
    const ymd = (d) => {
        if (!d) return '';
        return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
    };

    const parse = (s) => {
        if (!s) return null;
        const p = String(s).slice(0, 10).split('-');
        if (p.length !== 3) return null;
        const d = new Date(+p[0], +p[1] - 1, +p[2]);
        return isNaN(d) ? null : d;
    };

    const startOfToday = () => {
        const d = new Date();
        d.setHours(0, 0, 0, 0);
        return d;
    };

    const plusDays = (n) => {
        const d = startOfToday();
        d.setDate(d.getDate() + n);
        return d;
    };

    const endOfWeek = () => {
        const d = startOfToday();
        d.setDate(d.getDate() + (6 - d.getDay() + 7) % 7);
        return d;
    };

    const startOfWeek = () => {
        const d = endOfWeek();
        d.setDate(d.getDate() - 6);
        return d;
    };

    const endOfNextWeek = () => {
        const d = endOfWeek();
        d.setDate(d.getDate() + 7);
        return d;
    };

    const endOfMonth = () => {
        const d = startOfToday();
        return new Date(d.getFullYear(), d.getMonth() + 1, 0);
    };

    const startOfMonth = () => {
        const d = startOfToday();
        return new Date(d.getFullYear(), d.getMonth(), 1);
    };

    const startNextMonth = () => {
        const d = startOfToday();
        return new Date(d.getFullYear(), d.getMonth() + 1, 1);
    };

    const dayDiff = (a, b) => Math.round((a - b) / 86400000);

    const isDone = (k) => ["Completed", "Cancelled"].indexOf(k.status) > -1;

    const assignList = (raw) => {
        try {
            const a = JSON.parse(raw || "[]");
            return Array.isArray(a) ? a : [];
        } catch (e) { return []; }
    };

    const projLabel = (name) => {
        const hit = projectDocs.find(p => p.name === name);
        return (hit && hit.project_name && hit.project_name !== name) ? hit.project_name : name;
    };

    const shortUser = (u) => {
        const hit = users.find(x => x.name === u);
        return (hit && hit.full_name) || String(u).split('@')[0];
    };

    const bucketOf = (k) => {
        const d = parse(k[CONFIG.dateField]);
        if (!d) return "none";
        const today = startOfToday();
        if (d < today) return isDone(k) ? "later" : "overdue";
        if (d.getTime() === today.getTime()) return "today";
        if (d <= endOfWeek()) return "week";
        if (d <= endOfMonth()) return "month";
        return "later";
    };

    const dueStyle = (k) => {
        const d = parse(k[CONFIG.dateField]);
        if (isDone(k)) return { rail: C.tealDeep, bg: "#E6EFEE", fg: C.tealDeep };
        if (!d) return { rail: "#DFE3DE", bg: "#F4F0E8", fg: C.bronze };
        const today = startOfToday();
        if (d < today) return { rail: C.alert, bg: "#F6E9E6", fg: C.alert };
        if (d.getTime() === today.getTime()) return { rail: C.teal, bg: "#E6EFEE", fg: C.tealDeep };
        if (d <= endOfWeek()) return { rail: C.tealSoft, bg: "#E6EFEE", fg: C.tealDeep };
        return { rail: C.bronzeSoft, bg: "#F4F0E8", fg: C.bronze };
    };

    const dueLabel = (k) => {
        const d = parse(k[CONFIG.dateField]);
        if (!d) return null;
        if (isDone(k)) return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
        const n = dayDiff(d, startOfToday());
        if (n === 0) return t('dueToday');
        if (n === 1) return t('dueTomorrow');
        if (n > 1 && n <= 6) return t('dueIn', n);
        return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
    };

    const lateDays = (k) => {
        const d = parse(k[CONFIG.dateField]);
        if (!d || isDone(k)) return 0;
        const n = dayDiff(startOfToday(), d);
        return n > 0 ? n : 0;
    };

    const errText = (e) => {
        const m = (e && (e.message || e._server_messages || e)) || "";
        return String(m).replace(/<[^>]*>/g, "").replace(/[\[\]"\\]/g, " ").trim().slice(0, 220);
    };

    const toast = (msg, kind) => {
        let toastEl = document.getElementById('tb-toast');
        if (!toastEl) {
            toastEl = document.createElement('div');
            toastEl.id = 'tb-toast';
            toastEl.className = 'tb-toast';
            document.body.appendChild(toastEl);
        }
        toastEl.textContent = msg;
        toastEl.className = 'tb-toast' + (kind === 'err' ? ' tb-toast-err' : '');
        toastEl.style.display = 'block';
        clearTimeout(toast._x);
        toast._x = setTimeout(() => {
            toastEl.style.display = 'none';
        }, kind === 'err' ? 6000 : 2600);
    };

    // Data loading
    const withMeta = (dt) => {
        return new Promise((r) => {
            try {
                frappe.model.with_doctype(dt, () => r(frappe.get_meta(dt)));
            } catch (e) {
                r(null);
            }
        });
    };

    const options = (meta, fieldname, fallback) => {
        const f = meta && meta.fields && meta.fields.find(x => x.fieldname === fieldname);
        const o = f && f.options ? String(f.options).split('\n').map(s => s.trim()).filter(Boolean) : [];
        return o.length ? o : fallback;
    };

    const loadProjects = async () => {
        try {
            projectDocs = await frappe.db.get_list("Project", {
                fields: ["name", "project_name"],
                limit: 300,
                order_by: "modified desc"
            }) || [];
        } catch (e) {
            projectDocs = [];
        }
    };

    const loadUsers = async () => {
        if (!CONFIG.assignFromBoard) return;
        try {
            users = await frappe.db.get_list("User", {
                fields: ["name", "full_name"],
                filters: { enabled: 1 },
                limit: 300,
                order_by: "full_name asc"
            }) || [];
        } catch (e) {
            users = [];
        }
    };

    const load = async () => {
        const btn = document.querySelector('[data-role="refresh"]');
        if (btn) btn.classList.add("is-busy");
        loadError = null;

        const meta = await withMeta(CONFIG.doctype);
        statuses = options(meta, "status",
            ["Open", "Working", "Pending Review", "Overdue", "Completed", "Cancelled"])
            .filter(s => s !== "Template");
        priorities = options(meta, "priority", ["Low", "Medium", "High", "Urgent"]);

        const want = ["name", "subject", "status", "priority", CONFIG.dateField,
            "project", "parent_task", "progress", "_assign", "modified"];

        try {
            tasks = await frappe.db.get_list(CONFIG.doctype, {
                fields: want,
                limit: CONFIG.maxRows,
                order_by: "modified desc"
            }) || [];
        } catch (e) {
            try {
                tasks = await frappe.db.get_list(CONFIG.doctype, {
                    fields: ["name", "subject", "status", CONFIG.dateField],
                    limit: CONFIG.maxRows,
                    order_by: "modified desc"
                }) || [];
            } catch (e2) {
                tasks = [];
                loadError = errText(e2) || t('errLoad');
            }
        }

        projects = Array.from(new Set(tasks.map(k => k.project).filter(Boolean))).sort();
        const set = new Set();
        tasks.forEach(k => assignList(k._assign).forEach(u => set.add(u)));
        assignees = Array.from(set).sort();

        if (btn) btn.classList.remove("is-busy");
        buildControls();
        render();
    };

    // Filtering and sorting
    const presetRange = (p) => {
        if (p === "today") return [startOfToday(), startOfToday()];
        if (p === "week") return [startOfWeek(), endOfWeek()];
        if (p === "month") return [startOfMonth(), endOfMonth()];
        if (p === "next7") return [startOfToday(), plusDays(7)];
        if (p === "next30") return [startOfToday(), plusDays(30)];
        return null;
    };

    const matchesDate = (k) => {
        const d = parse(k[CONFIG.dateField]);
        if (F.preset === "none") return !d;
        if (F.preset === "overdue") return !!d && d < startOfToday() && !isDone(k);
        const range = presetRange(F.preset);
        if (range) return !!d && d >= range[0] && d <= range[1];
        const from = parse(F.from),
            to = parse(F.to);
        if (!from && !to) return true;
        if (!d) return false;
        if (from && d < from) return false;
        if (to && d > to) return false;
        return true;
    };

    const visible = () => {
        const q = F.q.trim().toLowerCase(),
            user = me();
        return sortRows(tasks.filter(k => {
            if (F.open && isDone(k)) return false;
            if (F.status && k.status !== F.status) return false;
            if (F.priority && k.priority !== F.priority) return false;
            if (F.project === NONE_KEY ? !!k.project : (F.project && k.project !== F.project)) return false;
            const who = assignList(k._assign);
            if (F.unassigned && who.length) return false;
            if (F.assignee && who.indexOf(F.assignee) === -1) return false;
            if (F.mine && who.indexOf(user) === -1) return false;
            if (!matchesDate(k)) return false;
            if (q) {
                const hay = (k.subject || "") + " " + (k.name || "") + " " + (k.project || "") + " " + who.join(" ");
                if (hay.toLowerCase().indexOf(q) === -1) return false;
            }
            return true;
        }));
    };

    const sortRows = (rows) => {
        const far = 8.64e15;
        const key = (k) => {
            const d = parse(k[CONFIG.dateField]);
            return d ? d.getTime() : null;
        };
        const rank = (p) => (PRIORITY_RANK[p] === undefined ? 9 : PRIORITY_RANK[p]);
        const cmp = {
            due_asc: (a, b) => (key(a) === null ? far : key(a)) - (key(b) === null ? far : key(b)),
            due_desc: (a, b) => (key(b) === null ? -far : key(b)) - (key(a) === null ? -far : key(a)),
            priority: (a, b) => rank(a.priority) - rank(b.priority),
            modified: (a, b) => String(b.modified || "").localeCompare(String(a.modified || "")),
            subject: (a, b) => String(a.subject || "").localeCompare(String(b.subject || ""), lang === 'ar' ? 'ar' : 'en')
        };
        return rows.slice().sort(cmp[F.sort] || cmp.due_asc);
    };

    // KPI helpers
    const KPIS = [
        { id: "open", color: C.teal, f: { open: true } },
        { id: "overdue", color: C.alert, f: { open: true, preset: "overdue" } },
        { id: "today", color: C.tealMid, f: { open: true, preset: "today" } },
        { id: "week", color: C.tealSoft, f: { open: true, preset: "week" } },
        { id: "unassigned", color: C.bronze, f: { open: true, unassigned: true } },
        { id: "done", color: C.tealDeep, f: { open: false, status: "Completed" } }
    ];

    const kpiCount = (id) => {
        const today = startOfToday(),
            sow = startOfWeek(),
            eow = endOfWeek();
        return tasks.filter(k => {
            const d = parse(k[CONFIG.dateField]);
            if (id === "open") return !isDone(k);
            if (id === "overdue") return !isDone(k) && !!d && d < today;
            if (id === "today") return !isDone(k) && !!d && d.getTime() === today.getTime();
            if (id === "week") return !isDone(k) && !!d && d >= today && d <= eow;
            if (id === "unassigned") return !isDone(k) && !assignList(k._assign).length;
            if (id === "done") {
                const m = parse(k.modified);
                return k.status === "Completed" && !!m && m >= sow && m <= eow;
            }
            return false;
        }).length;
    };

    const kpiActive = (kpi) =>
        Object.keys(kpi.f).every(key => String(F[key]) === String(kpi.f[key]));

    // Columns
    const columns = () => {
        if (group === "status") {
            return statuses.map(s => ({
                key: s,
                label: tr(s),
                color: STATUS_COLOR[s] || C.tealMid,
                locked: s === "Overdue",
                canAdd: s !== "Overdue"
            }));
        }
        if (group === "date") {
            return DATE_COLS.map(c => ({
                key: c.key,
                label: t(c.key),
                color: c.color,
                locked: c.locked,
                canAdd: c.canAdd && c.key !== "none"
            }));
        }
        if (group === "priority") {
            return priorities.map((p, i) => ({
                key: p,
                label: tr(p),
                color: PRIORITY_COLOR[p] || C.tealMid,
                locked: false,
                canAdd: true
            })).concat([{ key: NONE_KEY, label: t("noPriority"), color: C.grey, locked: true, canAdd: false }]);
        }
        if (group === "assignee") {
            const ramp = [C.teal, C.tealMid, C.bronze, C.tealSoft, C.bronzeSoft, C.tealDeep];
            return assignees.map((u, i) => ({
                key: u,
                label: shortUser(u),
                color: ramp[i % ramp.length],
                locked: false,
                canAdd: false
            })).concat([{ key: NONE_KEY, label: t("noAssignee"), color: C.grey, locked: false, canAdd: false }]);
        }
        const ramp = [C.teal, C.bronze, C.tealMid, C.bronzeSoft, C.tealSoft];
        return projects.map((p, i) => ({
            key: p,
            label: projLabel(p),
            color: ramp[i % ramp.length],
            locked: true,
            canAdd: false
        })).concat([{ key: NONE_KEY, label: t("noProject"), color: C.grey, locked: true, canAdd: false }]);
    };

    const columnKeyOf = (k) => {
        if (group === "status") return k.status;
        if (group === "date") return bucketOf(k);
        if (group === "priority") return k.priority || NONE_KEY;
        if (group === "project") return k.project || NONE_KEY;
        const who = assignList(k._assign);
        return who.length ? who : [NONE_KEY];
    };

    // Card HTML
    const cardHtml = (k) => {
        const st = dueStyle(k),
            pri = k.priority,
            late = lateDays(k);
        const label = dueLabel(k);
        const who = assignList(k._assign).slice(0, 3);
        const prog = Number(k.progress || 0);

        return `<article class="tb-card" data-name="${esc(k.name)}" style="--due-c:${st.rail};--due-bg:${st.bg};--due-fg:${st.fg}">
            <button class="tb-open tb-nodrag" type="button" title="${esc(k.name)}">↗</button>
            <button class="tb-more tb-nodrag" type="button" aria-haspopup="true">⋯</button>
            <p class="tb-subj">${esc(k.subject || k.name)}</p>
            <div class="tb-meta">
                ${late ? `<span class="tb-late">${esc(t('lateBy', late))}</span>` : 
                 (label ? `<span class="tb-chip tb-chip-due">${esc(label)}</span>` : '')}
                ${pri ? `<span class="tb-chip tb-chip-pri"><i class="tb-pri-dot" style="background:${PRIORITY_COLOR[pri] || C.bronze}"></i>${esc(tr(pri))}</span>` : ''}
                ${k.project && group !== "project" ? `<span class="tb-chip">${esc(projLabel(k.project))}</span>` : ''}
                ${who.map(u => `<span class="tb-who" title="${esc(shortUser(u))}">${esc(shortUser(u).charAt(0).toUpperCase())}</span>`).join('')}
            </div>
            ${prog > 0 ? `<div class="tb-prog"><i style="width:${Math.min(prog, 100)}%"></i></div>` : ''}
        </article>`;
    };

    // Render functions
    const renderKpis = () => {
        const box = document.querySelector('[data-role="kpis"]');
        if (!box) return;
        box.innerHTML = KPIS.map(kpi =>
            `<button type="button" class="tb-kpi${kpiActive(kpi) ? ' is-on' : ''}" data-kpi="${kpi.id}" style="--kpi-c:${kpi.color}" ${kpi.id === 'done' ? `title="${esc(t('k_doneTip'))}"` : ''}>
                <span class="tb-kpi-v">${kpiCount(kpi.id)}</span>
                <span class="tb-kpi-l">${esc(t('k_' + kpi.id))}</span>
            </button>`
        ).join('');

        box.querySelectorAll("[data-kpi]").forEach(b => {
            b.addEventListener("click", () => {
                const kpi = KPIS.find(x => x.id === b.dataset.kpi);
                const on = kpiActive(kpi);
                Object.assign(F, BLANK, { sort: F.sort });
                if (!on) Object.assign(F, kpi.f);
                syncControls();
                render();
            });
        });
    };

    const fillSelect = (sel, items, labeller, anyLabel) => {
        if (!sel) return;
        const v = sel.value;
        sel.innerHTML = `<option value="">${esc(anyLabel)}</option>` +
            items.map(o => {
                const val = typeof o === "string" ? o : o.v;
                const lab = typeof o === "string" ? labeller(o) : o.l;
                return `<option value="${esc(val)}">${esc(lab)}</option>`;
            }).join('');
        sel.value = v;
    };

    const buildControls = () => {
        const gs = document.querySelector('[data-role="group"]');
        if (gs) {
            gs.innerHTML = GROUPS.map(g =>
                `<option value="${g}">${esc(t('g_' + g))}</option>`).join('');
            gs.value = group;
        }

        fillSelect(document.querySelector('[data-role="status"]'), statuses, tr, t('any'));
        fillSelect(document.querySelector('[data-role="priority"]'), priorities, tr, t('any'));
        fillSelect(document.querySelector('[data-role="project"]'),
            [{ v: NONE_KEY, l: t('noProject') }].concat(projects.map(p => ({ v: p, l: projLabel(p) }))), null, t('any'));
        fillSelect(document.querySelector('[data-role="assignee"]'),
            assignees.map(u => ({ v: u, l: shortUser(u) })), null, t('any'));

        const preset = document.querySelector('[data-role="preset"]');
        if (preset) {
            preset.innerHTML = PRESETS.map(p =>
                `<option value="${esc(p)}">${esc(t('preset_' + p))}</option>`).join('');
        }

        const sort = document.querySelector('[data-role="sort"]');
        if (sort) {
            sort.innerHTML = SORTS.map(s =>
                `<option value="${esc(s)}">${esc(t('sort_' + s))}</option>`).join('');
        }

        syncControls();
    };

    const syncControls = () => {
        const q = document.querySelector('[data-role="q"]');
        if (q) q.value = F.q;
        const qClear = document.querySelector('[data-role="q-clear"]');
        if (qClear) qClear.hidden = !F.q;

        const status = document.querySelector('[data-role="status"]');
        if (status) status.value = F.status;
        const priority = document.querySelector('[data-role="priority"]');
        if (priority) priority.value = F.priority;
        const project = document.querySelector('[data-role="project"]');
        if (project) project.value = F.project;
        const assignee = document.querySelector('[data-role="assignee"]');
        if (assignee) assignee.value = F.assignee;
        const preset = document.querySelector('[data-role="preset"]');
        if (preset) preset.value = F.preset;
        const from = document.querySelector('[data-role="from"]');
        if (from) from.value = F.from;
        const to = document.querySelector('[data-role="to"]');
        if (to) to.value = F.to;
        const sort = document.querySelector('[data-role="sort"]');
        if (sort) sort.value = F.sort;
        const mine = document.querySelector('[data-role="mine"]');
        if (mine) mine.checked = F.mine;
        const openonly = document.querySelector('[data-role="openonly"]');
        if (openonly) openonly.checked = F.open;
        const unassigned = document.querySelector('[data-role="unassigned"]');
        if (unassigned) unassigned.checked = F.unassigned;

        const custom = !F.preset;
        if (from) from.disabled = !custom;
        if (to) to.disabled = !custom;
    };

    const activeChips = () => {
        const out = [];
        const add = (key, label, value) => out.push({ key, label, value });
        if (F.q) add('q', t('search'), F.q);
        if (F.status) add('status', t('fStatus'), tr(F.status));
        if (F.priority) add('priority', t('fPriority'), tr(F.priority));
        if (F.project) add('project', t('fProject'), F.project === NONE_KEY ? t('noProject') : projLabel(F.project));
        if (F.assignee) add('assignee', t('fAssignee'), shortUser(F.assignee));
        if (F.preset) add('preset', t('fDue'), t('preset_' + F.preset));
        else if (F.from || F.to) add('range', t('fDue'), (F.from || '…') + ' – ' + (F.to || '…'));
        if (F.mine) add('mine', '', t('mine'));
        if (F.unassigned) add('unassigned', '', t('unassigned'));
        if (!F.open) add('open', '', t('openOnly') + ' ✕');
        return out;
    };

    const clearKey = (key) => {
        if (key === 'range') { F.from = '';
            F.to = ''; } else if (key === 'mine') F.mine = false;
        else if (key === 'unassigned') F.unassigned = false;
        else if (key === 'open') F.open = true;
        else F[key] = '';
        syncControls();
        render();
    };

    const renderChips = () => {
        const box = document.querySelector('[data-role="chips"]');
        const chips = activeChips();
        const badge = document.querySelector('[data-role="fcount"]');
        if (badge) {
            badge.hidden = !chips.length;
            badge.textContent = chips.length;
        }
        if (!box) return;
        if (!chips.length) { box.hidden = true;
            box.innerHTML = ''; return; }
        box.hidden = false;
        box.innerHTML = chips.map(c =>
            `<span class="tb-fchip">${c.label ? `<b>${esc(c.label)}:</b> ` : ''}${esc(c.value)}
            <button type="button" data-clear="${esc(c.key)}" aria-label="remove">✕</button></span>`
        ).join('') +
            `<button type="button" class="tb-clear" data-role="clear-all">${esc(t('clearAll'))}</button>`;

        box.querySelectorAll("[data-clear]").forEach(b =>
            b.addEventListener("click", () => clearKey(b.dataset.clear)));
        const clearAll = box.querySelector('[data-role="clear-all"]');
        if (clearAll) {
            clearAll.addEventListener("click", () => {
                Object.assign(F, BLANK);
                syncControls();
                render();
            });
        }
    };

    const renderTree = (rows) => {
        // Simplified tree rendering - can be expanded
        const panel = document.querySelector('[data-role="tree"]');
        if (!panel || panel.hidden) return;
        // Basic tree implementation
    };

    const render = () => {
        const board = document.querySelector('[data-role="board"]');
        if (!board) return;

        renderKpis();
        renderChips();

        if (loadError) {
            board.innerHTML = `<div class="tb-err">${esc(t('errLoad'))} ${esc(loadError)}</div>`;
            const count = document.querySelector('[data-role="count"]');
            if (count) count.textContent = '';
            return;
        }

        const rows = visible();
        const groups = {};
        rows.forEach(k => {
            const key = columnKeyOf(k);
            (Array.isArray(key) ? key : [key]).forEach(x => (groups[x] = groups[x] || []).push(k));
        });

        board.innerHTML = columns().map(col => {
            const list = groups[col.key] || [];
            const add = (CONFIG.quickAdd && col.canAdd) ?
                `<div class="tb-add"><input type="text" data-role="add" placeholder="${esc(t('addPh'))}"><button type="button" data-role="add-go">+</button></div>` :
                '';
            return `<section class="tb-col" data-key="${esc(col.key)}" data-locked="${col.locked ? '1' : '0'}" style="--col-c:${col.color}">
                <header class="tb-col-head"><span class="tb-col-t" title="${esc(col.label)}">${esc(col.label)}</span>
                ${col.locked ? '<span class="tb-lock">∅</span>' : ''}
                <span class="tb-col-n">${list.length}</span></header>
                <div class="tb-list" data-role="list">
                    ${list.length ? list.map(cardHtml).join('') : `<div class="tb-empty">${esc(col.locked ? t('empty') : t('dropHere'))}</div>`}
                </div>${add}</section>`;
        }).join('');

        const count = document.querySelector('[data-role="count"]');
        if (count) {
            count.textContent = (rows.length ? t('counted', rows.length, tasks.length) : t('noMatch')) +
                (tasks.length >= CONFIG.maxRows ? ' · ' + t('capped') : '');
        }

        renderTree(rows);
        bindBoard();
    };

    // Board interactions
    const bindBoard = () => {
        document.querySelectorAll('.tb-card').forEach(card => {
            card.addEventListener('pointerdown', (e) => startDrag(e, card));
            const openBtn = card.querySelector('.tb-open');
            if (openBtn) {
                openBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    frappe.set_route('Form', CONFIG.doctype, card.dataset.name);
                });
            }
            const moreBtn = card.querySelector('.tb-more');
            if (moreBtn) {
                moreBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    openMenu(e.currentTarget, card.dataset.name);
                });
            }
            card.addEventListener('dblclick', () => {
                frappe.set_route('Form', CONFIG.doctype, card.dataset.name);
            });
        });

        document.querySelectorAll('.tb-col').forEach(col => {
            const input = col.querySelector('[data-role="add"]');
            if (!input) return;
            const fire = () => quickAdd(col.dataset.key, input);
            const goBtn = col.querySelector('[data-role="add-go"]');
            if (goBtn) goBtn.addEventListener('click', fire);
            input.addEventListener('keydown', (e) => { if (e.key === 'Enter') fire(); });
        });
    };

    const colAt = (x, y) => {
        const cols = document.querySelectorAll('.tb-col');
        let best = null,
            bestDist = Infinity;
        for (let i = 0; i < cols.length; i++) {
            const r = cols[i].getBoundingClientRect();
            if (y < r.top - 48 || y > r.bottom + 48) continue;
            if (x >= r.left && x <= r.right) return cols[i];
            const d = x < r.left ? r.left - x : x - r.right;
            if (d < bestDist) { bestDist = d;
                best = cols[i]; }
        }
        return bestDist <= 90 ? best : null;
    };

    const startDrag = (e, card) => {
        if (e.pointerType === 'mouse' && e.button !== 0) return;
        if (e.target.closest('.tb-nodrag')) return;
        const x0 = e.clientX,
            y0 = e.clientY;
        let ghost = null,
            active = false,
            target = null,
            overLocked = false;
        let px = e.clientX,
            py = e.clientY,
            raf = null;

        const evaluate = () => {
            const col = colAt(px, py);
            overLocked = !!(col && col.dataset.locked === '1');
            target = (col && !overLocked) ? col : null;
            document.querySelectorAll('.tb-col').forEach(c => c.classList.toggle('is-over', c === target));
        };

        const tick = () => {
            if (!active) return;
            const sc = document.querySelector('.tb-scroll');
            if (sc) {
                const r = sc.getBoundingClientRect(),
                    zone = 76;
                const speed = (depth) => 3 + Math.min(1, depth) * 8;
                let dx = 0;
                if (px < r.left + zone) dx = -speed((r.left + zone - px) / zone);
                else if (px > r.right - zone) dx = speed((px - (r.right - zone)) / zone);
                if (dx) sc.scrollLeft += dx;
            }
            evaluate();
            raf = requestAnimationFrame(tick);
        };

        const onMove = (ev) => {
            px = ev.clientX;
            py = ev.clientY;
            if (!active) {
                if (Math.abs(ev.clientX - x0) < 7 && Math.abs(ev.clientY - y0) < 7) return;
                if (Math.abs(ev.clientY - y0) > Math.abs(ev.clientX - x0) * 1.6) { cleanup(); return; }
                active = true;
                dragging = true;
                card.classList.add('is-dragging');
                ghost = document.createElement('div');
                ghost.className = 'momc-tb-ghost';
                const task = tasks.find(k => k.name === card.dataset.name);
                ghost.textContent = (task || {}).subject || '';
                ghost.style.width = card.getBoundingClientRect().width + 'px';
                document.body.appendChild(ghost);
                raf = requestAnimationFrame(tick);
            }
            ghost.style.left = (ev.clientX + 12) + 'px';
            ghost.style.top = (ev.clientY + 12) + 'px';
            evaluate();
            ev.preventDefault();
        };

        const onUp = () => {
            const drop = target,
                wasActive = active,
                wasLocked = overLocked;
            const from = card.closest('.tb-col');
            const fromKey = from ? from.dataset.key : null;
            cleanup();
            if (wasActive && !drop && wasLocked) {
                toast(group === 'status' || group === 'date' ? t('lockedOverdue') : t('lockedCol'));
                return;
            }
            if (wasActive && drop && drop.dataset.key !== fromKey) {
                applyDrop(card.dataset.name, drop.dataset.key);
            }
        };

        const cleanup = () => {
            document.removeEventListener('pointermove', onMove);
            document.removeEventListener('pointerup', onUp);
            document.removeEventListener('pointercancel', onUp);
            if (raf) { cancelAnimationFrame(raf);
                raf = null; }
            if (ghost) ghost.remove();
            card.classList.remove('is-dragging');
            document.querySelectorAll('.tb-col').forEach(c => c.classList.remove('is-over'));
            active = false;
            dragging = false;
        };

        document.addEventListener('pointermove', onMove);
        document.addEventListener('pointerup', onUp);
        document.addEventListener('pointercancel', onUp);
    };

    // Drop operations
    const dropPlan = (colKey) => {
        if (group === 'status') return { kind: 'field', field: 'status', value: colKey };
        if (group === 'priority') return { kind: 'field', field: 'priority', value: colKey };
        if (group === 'date') {
            if (colKey === 'none') return { kind: 'field', field: CONFIG.dateField, value: null };
            const d = colKey === 'today' ? startOfToday() :
                colKey === 'week' ? endOfWeek() :
                colKey === 'month' ? endOfMonth() :
                startNextMonth();
            return { kind: 'field', field: CONFIG.dateField, value: ymd(d) };
        }
        if (group === 'assignee') {
            return colKey === NONE_KEY ? { kind: 'unassign' } : { kind: 'assign', user: colKey };
        }
        return null;
    };

    const applyDrop = async (name, colKey) => {
        const task = tasks.find(k => k.name === name);
        const plan = dropPlan(colKey);
        if (!task || !plan) return;

        if (plan.kind === 'field') {
            const before = task[plan.field];
            if (before === plan.value) return;
            task[plan.field] = plan.value;
            render();
            try {
                const patch = {};
                patch[plan.field] = plan.value;
                await frappe.db.set_value(CONFIG.doctype, name, patch);
                if (plan.field === 'status') toast(t('moved', tr(plan.value)));
                else if (plan.field === 'priority') toast(t('prioSet', tr(plan.value)));
                else if (plan.value === null) toast(t('cleared'));
                else toast(t('dated', plan.value));
            } catch (e) {
                task[plan.field] = before;
                toast(t('errSave') + errText(e), 'err');
                render();
            }
            return;
        }

        const before = task._assign;
        const who = assignList(before);
        try {
            if (plan.kind === 'assign') {
                if (who.indexOf(plan.user) > -1) return;
                task._assign = JSON.stringify(who.concat([plan.user]));
                render();
                await frappe.call({
                    method: 'frappe.desk.form.assign_to.add',
                    args: { doctype: CONFIG.doctype, name: name, assign_to: [plan.user] }
                });
                toast(t('assigned', shortUser(plan.user)));
            } else {
                if (!who.length) return;
                task._assign = '[]';
                render();
                for (const u of who) {
                    await frappe.call({
                        method: 'frappe.desk.form.assign_to.remove',
                        args: { doctype: CONFIG.doctype, name: name, assign_to: u }
                    });
                }
                toast(t('unassignedOk'));
            }
            assignees = Array.from(new Set(
                tasks.reduce((a, k) => a.concat(assignList(k._assign)), []))).sort();
            buildControls();
            render();
        } catch (e) {
            task._assign = before;
            toast(t('errSave') + errText(e), 'err');
            render();
        }
    };

    // Card menu
    const openMenu = (anchor, name) => {
        closeMenu();
        const k = tasks.find(x => x.name === name);
        if (!k) return;
        const who = assignList(k._assign);
        const here = columnKeyOf(k);
        const hereKeys = Array.isArray(here) ? here : [here];
        const cols = columns().filter(c => !c.locked && hereKeys.indexOf(c.key) === -1);

        const sec = (label, inner) =>
            `<div class="mn-sec"><span>${esc(label)}</span><div class="mn-row">${inner}</div></div>`;
        const b = (act, val, text, on, dis) =>
            `<button type="button" class="mn-b${on ? ' is-on' : ''}" data-act="${act}" data-val="${esc(val)}"${dis ? ' disabled' : ''}>${esc(text)}</button>`;

        let html = `<h5>${esc(k.subject || k.name)}</h5>`;

        if (cols.length) {
            html += sec(t('mMove'), cols.map(c =>
                b('move', c.key, c.label, false, false)).join(''));
        }
        html += sec(t('mPriority'),
            priorities.map(p =>
                b('prio', p, tr(p), k.priority === p, false)).join(''));
        html += sec(t('mDue'),
            b('due', ymd(startOfToday()), t('today')) +
            b('due', ymd(plusDays(1)), t('mTomorrow')) +
            b('due', ymd(endOfWeek()), t('mEndWeek')) +
            b('due', ymd(endOfNextWeek()), t('mNextWeek')) +
            b('due', '', t('mClearDue')));

        if (CONFIG.assignFromBoard) {
            let assign = who.map(u =>
                `<span class="mn-who">${esc(shortUser(u))}
                <button type="button" data-act="unassign" data-val="${esc(u)}">✕</button></span>`).join('');
            assign += b('assign', me(), t('mToMe'), false, who.indexOf(me()) > -1);
            html += sec(t('mAssign'), assign);
            if (users.length) {
                html += `<div class="mn-sec"><select class="mn-sel" data-role="mn-user">
                    <option value="">${esc(t('mPickUser'))}</option>
                    ${users.filter(u => who.indexOf(u.name) === -1).map(u =>
                        `<option value="${esc(u.name)}">${esc(u.full_name || u.name)}</option>`).join('')}
                </select><div class="mn-row" style="margin-top:6px">
                ${b('assign-picked', '', t('mAssignBtn'))}</div></div>`;
            }
        }

        html += `<div class="mn-foot"><button type="button" class="mn-open" data-act="open">${esc(t('mOpen'))}</button></div>`;

        menuEl = document.createElement('div');
        menuEl.className = 'momc-tb-menu';
        menuEl.setAttribute('dir', lang === 'ar' ? 'rtl' : 'ltr');
        menuEl.innerHTML = html;
        document.body.appendChild(menuEl);

        const r = anchor.getBoundingClientRect(),
            m = menuEl.getBoundingClientRect();
        let left = lang === 'ar' ? r.right - m.width : r.left;
        left = Math.max(8, Math.min(left, window.innerWidth - m.width - 8));
        let top = r.bottom + 6;
        if (top + m.height > window.innerHeight - 8) top = Math.max(8, r.top - m.height - 6);
        menuEl.style.left = left + 'px';
        menuEl.style.top = top + 'px';

        menuEl.addEventListener('click', async (e) => {
            const btn = e.target.closest('[data-act]');
            if (!btn) return;
            const act = btn.dataset.act,
                val = btn.dataset.val;
            if (act === 'open') { closeMenu();
                frappe.set_route('Form', CONFIG.doctype, name); return; }
            if (act === 'assign-picked') {
                const sel = menuEl.querySelector('[data-role="mn-user"]');
                const u = sel && sel.value;
                closeMenu();
                if (u) await assignUser(name, u);
                return;
            }
            closeMenu();
            if (act === 'move') await applyDrop(name, val);
            else if (act === 'prio') {
                const task = tasks.find(x => x.name === name);
                if (task) {
                    const before = task.priority;
                    task.priority = val;
                    render();
                    try {
                        await frappe.db.set_value(CONFIG.doctype, name, { priority: val });
                        toast(t('prioSet', tr(val)));
                    } catch (e) {
                        task.priority = before;
                        toast(t('errSave') + errText(e), 'err');
                        render();
                    }
                }
            } else if (act === 'due') {
                const task = tasks.find(x => x.name === name);
                if (task) {
                    const before = task[CONFIG.dateField];
                    task[CONFIG.dateField] = val || null;
                    render();
                    try {
                        const patch = {};
                        patch[CONFIG.dateField] = val || null;
                        await frappe.db.set_value(CONFIG.doctype, name, patch);
                        toast(val ? t('dated', val) : t('cleared'));
                    } catch (e) {
                        task[CONFIG.dateField] = before;
                        toast(t('errSave') + errText(e), 'err');
                        render();
                    }
                }
            } else if (act === 'assign') await assignUser(name, val);
            else if (act === 'unassign') await unassignUser(name, val);
        });

        menuOpen = true;
        setTimeout(() => document.addEventListener('mousedown', onOutside, true), 0);
    };

    let menuEl = null;

    const closeMenu = () => {
        if (menuEl) { menuEl.remove();
            menuEl = null; }
        menuOpen = false;
        document.removeEventListener('mousedown', onOutside, true);
    };

    const onOutside = (e) => {
        if (menuEl && !menuEl.contains(e.target)) closeMenu();
    };

    const assignUser = async (name, user) => {
        const k = tasks.find(x => x.name === name);
        if (!k || !user) return;
        const who = assignList(k._assign);
        if (who.indexOf(user) > -1) return;
        k._assign = JSON.stringify(who.concat([user]));
        render();
        try {
            await frappe.call({
                method: 'frappe.desk.form.assign_to.add',
                args: { doctype: CONFIG.doctype, name: name, assign_to: [user] }
            });
            toast(t('assigned', shortUser(user)));
            assignees = Array.from(new Set(
                tasks.reduce((a, k) => a.concat(assignList(k._assign)), []))).sort();
            buildControls();
            render();
        } catch (e) {
            k._assign = JSON.stringify(who);
            toast(t('errSave') + errText(e), 'err');
            render();
        }
    };

    const unassignUser = async (name, user) => {
        const k = tasks.find(x => x.name === name);
        if (!k) return;
        const who = assignList(k._assign);
        k._assign = JSON.stringify(who.filter(u => u !== user));
        render();
        try {
            await frappe.call({
                method: 'frappe.desk.form.assign_to.remove',
                args: { doctype: CONFIG.doctype, name: name, assign_to: user }
            });
            toast(t('unassignedOk'));
            assignees = Array.from(new Set(
                tasks.reduce((a, k) => a.concat(assignList(k._assign)), []))).sort();
            buildControls();
            render();
        } catch (e) {
            k._assign = JSON.stringify(who);
            toast(t('errSave') + errText(e), 'err');
            render();
        }
    };

    // Quick add
    const quickAdd = async (colKey, input) => {
        const subject = (input.value || '').trim();
        if (!subject) return;
        const doc = { doctype: CONFIG.doctype, subject: subject };
        const plan = dropPlan(colKey);
        if (plan && plan.kind === 'field' && plan.value !== null) doc[plan.field] = plan.value;
        input.disabled = true;
        try {
            await frappe.db.insert(doc);
            input.value = '';
            toast(t('added'));
            await load();
        } catch (e) {
            toast(t('errSave') + errText(e), 'err');
        } finally {
            input.disabled = false;
        }
    };

    // Export functions
    const exportXlsx = () => {
        const rows = visible().map(k => ({
            id: k.name,
            subject: k.subject || '',
            status: tr(k.status || ''),
            priority: tr(k.priority || ''),
            due: k[CONFIG.dateField] || null,
            bucket: t(bucketOf(k)),
            late: lateDays(k) || 0,
            project: k.project ? projLabel(k.project) : '',
            assignee: assignList(k._assign).map(shortUser).join(' · '),
            progress: Number(k.progress || 0),
            modified: k.modified ? String(k.modified).slice(0, 10) : null
        }));

        // Simple CSV export for now
        const headers = ['ID', 'Status', 'Priority', 'Due', 'Project', 'Assignee', 'Progress', 'Subject'];
        let csv = headers.join(',') + '\n';
        rows.forEach(row => {
            csv += [
                row.id,
                row.status,
                row.priority,
                row.due || '',
                row.project,
                row.assignee,
                row.progress,
                `"${row.subject.replace(/"/g, '""')}"`
            ].join(',') + '\n';
        });

        const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `tasks-${ymd(new Date())}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        setTimeout(() => URL.revokeObjectURL(link.href), 500);
        toast(t('exported'));
    };

    // Initialize
    const init = () => {
        // Create the HTML structure
        const html = `
            <div class="momc-tb" dir="${lang === 'ar' ? 'rtl' : 'ltr'}" data-lang="${lang}">
                <header class="tb-head">
                    <div class="tb-brand">
                        <div>
                            <h2 class="tb-title">${t('title')}</h2>
                            <p class="tb-sub">${t('subtitle')}</p>
                        </div>
                    </div>
                    <div class="tb-head-actions">
                        <button class="tb-btn tb-btn-xl" data-role="export" type="button">
                            <span class="tb-ico" aria-hidden="true">↓</span><span>${t('export')}</span>
                        </button>
                        <button class="tb-btn" data-role="export-csv" type="button">
                            <span>CSV</span>
                        </button>
                        <button class="tb-btn" data-role="refresh" type="button">
                            <span class="tb-ico" aria-hidden="true">↻</span><span>${t('refresh')}</span>
                        </button>
                        <button class="tb-btn tb-btn-solid" data-role="lang" type="button">
                            <span data-role="lang-label">${t('langLabel')}</span>
                        </button>
                    </div>
                </header>

                <div class="tb-kpis" data-role="kpis"></div>

                <div class="tb-bar">
                    <label class="tb-inline">
                        <span class="tb-inline-l">${t('groupBy')}</span>
                        <select class="tb-sel tb-sel-inline" data-role="group"></select>
                    </label>

                    <label class="tb-search">
                        <span class="tb-ico" aria-hidden="true">🔍</span>
                        <input type="text" data-role="q" placeholder="${t('searchPh')}">
                        <button type="button" class="tb-x" data-role="q-clear" hidden>✕</button>
                    </label>

                    <button class="tb-btn" data-role="filters-toggle" type="button" aria-expanded="false">
                        <span class="tb-ico" aria-hidden="true">☰</span>
                        <span>${t('filters')}</span>
                        <span class="tb-badge" data-role="fcount" hidden></span>
                    </button>

                    <button class="tb-btn" data-role="tree-toggle" type="button" aria-expanded="false">
                        <span class="tb-ico" aria-hidden="true">⏺</span>
                        <span>${t('tree')}</span>
                    </button>

                    <span class="tb-count" data-role="count"></span>
                </div>

                <div class="tb-panel" data-role="panel" hidden>
                    <div class="tb-field">
                        <label>${t('fStatus')}</label>
                        <select class="tb-sel" data-role="status"></select>
                    </div>
                    <div class="tb-field">
                        <label>${t('fPriority')}</label>
                        <select class="tb-sel" data-role="priority"></select>
                    </div>
                    <div class="tb-field">
                        <label>${t('fProject')}</label>
                        <select class="tb-sel" data-role="project"></select>
                    </div>
                    <div class="tb-field">
                        <label>${t('fAssignee')}</label>
                        <select class="tb-sel" data-role="assignee"></select>
                    </div>
                    <div class="tb-field tb-field-wide">
                        <label>${t('fDue')}</label>
                        <select class="tb-sel" data-role="preset"></select>
                        <div class="tb-range">
                            <input type="date" class="tb-date" data-role="from">
                            <span class="tb-dash">–</span>
                            <input type="date" class="tb-date" data-role="to">
                        </div>
                    </div>
                    <div class="tb-field">
                        <label>${t('fSort')}</label>
                        <select class="tb-sel" data-role="sort"></select>
                    </div>
                    <div class="tb-field tb-field-checks">
                        <label class="tb-check"><input type="checkbox" data-role="mine"><span>${t('mine')}</span></label>
                        <label class="tb-check"><input type="checkbox" data-role="openonly" checked><span>${t('openOnly')}</span></label>
                        <label class="tb-check"><input type="checkbox" data-role="unassigned"><span>${t('unassigned')}</span></label>
                    </div>
                    <div class="tb-field tb-field-wide tb-views">
                        <label>${t('fViews')}</label>
                        <div class="tb-range tb-views-row">
                            <select class="tb-sel" data-role="view"></select>
                            <button type="button" class="tb-btn tb-btn-sm" data-role="view-save">${t('saveView')}</button>
                            <button type="button" class="tb-btn tb-btn-sm" data-role="view-del">${t('delView')}</button>
                        </div>
                    </div>
                </div>

                <div class="tb-chips" data-role="chips" hidden></div>

                <div class="tb-main">
                    <aside class="tb-tree" data-role="tree" hidden>
                        <div class="tb-tree-head">
                            <span class="tb-tree-t">${t('treeTitle')}</span>
                            <button type="button" class="tb-tree-new" data-role="tree-add-project">
                                <span aria-hidden="true">+</span><span>${t('addProject')}</span>
                            </button>
                            <button type="button" class="tb-tree-x" data-role="tree-close" aria-label="close">✕</button>
                        </div>
                        <label class="tb-tree-search">
                            <span class="tb-ico" aria-hidden="true">🔍</span>
                            <input type="text" data-role="tree-q" placeholder="${t('treeSearchPh')}">
                            <button type="button" class="tb-x" data-role="tree-q-clear" hidden>✕</button>
                        </label>
                        <div class="tb-tree-tools">
                            <button type="button" class="tb-btn tb-btn-sm" data-role="tree-expand">${t('expandAll')}</button>
                            <button type="button" class="tb-btn tb-btn-sm" data-role="tree-collapse">${t('collapseAll')}</button>
                        </div>
                        <div class="tb-tree-body" data-role="tree-body"></div>
                    </aside>

                    <div class="tb-scroll">
                        <div class="tb-board" data-role="board"></div>
                    </div>
                </div>

                <div class="tb-hint">${t('hint')}</div>
            </div>
        `;

        container.innerHTML = html;

        // Add styles
        const style = document.createElement('style');
        style.textContent = `
            .momc-tb {
                --t-900: #0E4442;
                --t-700: #1C615D;
                --t-500: #2F8078;
                --t-300: #77B0A8;
                --t-050: #E6EFEE;
                --b-700: #776650;
                --b-500: #948065;
                --b-300: #C4B69C;
                --b-050: #F4F0E8;
                --alert: #9C4A3C;
                --sand: #F1F1EC;
                --paper: #FFFFFF;
                --ink: #16211F;
                --ink-2: #5C6A68;
                --line: #DFE3DE;
                font-family: "Qamra", "IBM Plex Sans Arabic", "Noto Kufi Arabic", "Segoe UI", Inter, system-ui, sans-serif;
                color: var(--ink);
                background: var(--sand);
                border: 1px solid var(--line);
                border-radius: 14px;
                padding: 16px 0 18px;
                font-variant-numeric: tabular-nums;
                user-select: none;
            }
            .momc-tb * { box-sizing: border-box; }
            .momc-tb [hidden] { display: none !important; }

            /* Header */
            .momc-tb .tb-head {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 14px;
                flex-wrap: wrap;
                padding: 0 16px 13px;
                border-bottom: 1px solid var(--line);
            }
            .momc-tb .tb-brand { display: flex; align-items: center; gap: 11px; }
            .momc-tb .tb-title { margin: 0; font-size: 1.1rem; font-weight: 700; color: var(--t-900); }
            .momc-tb .tb-sub { margin: 2px 0 0; font-size: .76rem; color: var(--ink-2); }
            .momc-tb .tb-head-actions { display: flex; gap: 8px; }
            .momc-tb .tb-btn {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                font-family: inherit;
                border: 1px solid var(--line);
                background: var(--paper);
                color: var(--t-900);
                border-radius: 999px;
                padding: 6px 13px;
                font-size: .78rem;
                font-weight: 600;
                cursor: pointer;
                white-space: nowrap;
                transition: background .15s, border-color .15s;
            }
            .momc-tb .tb-btn:hover { background: var(--t-050); border-color: var(--t-300); }
            .momc-tb .tb-btn-xl { border-color: var(--t-300); background: var(--t-050); }
            .momc-tb .tb-btn-xl:hover { background: var(--t-700); border-color: var(--t-700); color: #fff; }
            .momc-tb .tb-btn-solid { background: var(--t-700); border-color: var(--t-700); color: #fff; }
            .momc-tb .tb-btn-solid:hover { background: var(--t-900); border-color: var(--t-900); }
            .momc-tb .tb-ico { line-height: 1; }

            /* Bar */
            .momc-tb .tb-bar {
                display: flex;
                align-items: center;
                gap: 9px;
                flex-wrap: wrap;
                padding: 12px 16px 0;
            }
            .momc-tb .tb-search {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                background: var(--paper);
                border: 1px solid var(--line);
                border-radius: 999px;
                padding: 5px 12px;
                color: var(--ink-2);
            }
            .momc-tb .tb-search:focus-within { border-color: var(--t-500); }
            .momc-tb .tb-search input {
                border: 0;
                outline: 0;
                background: none;
                font-family: inherit;
                font-size: .78rem;
                color: var(--ink);
                width: 168px;
            }
            .momc-tb .tb-x {
                border: 0;
                background: none;
                cursor: pointer;
                color: var(--ink-2);
                font-size: .66rem;
                padding: 0 2px;
                line-height: 1;
                font-family: inherit;
            }
            .momc-tb .tb-x:hover { color: var(--alert); }
            .momc-tb .tb-badge {
                background: var(--b-500);
                color: #fff;
                border-radius: 999px;
                font-size: .66rem;
                font-weight: 700;
                padding: 0 6px;
                min-width: 17px;
                text-align: center;
            }
            .momc-tb .tb-count {
                margin-left: auto;
                font-size: .76rem;
                color: var(--ink-2);
            }
            .momc-tb .tb-inline {
                display: inline-flex;
                align-items: center;
                gap: 7px;
                background: var(--paper);
                border: 1px solid var(--line);
                border-radius: 999px;
                padding: 3px 5px 3px 12px;
            }
            .momc-tb .tb-inline-l {
                font-size: .72rem;
                font-weight: 700;
                color: var(--ink-2);
                white-space: nowrap;
            }
            .momc-tb .tb-sel-inline {
                width: auto;
                border: 0;
                background: var(--t-050);
                border-radius: 999px;
                padding: 5px 11px;
                font-weight: 600;
                color: var(--t-900);
            }

            /* Panel */
            .momc-tb .tb-panel {
                display: grid;
                gap: 11px 14px;
                margin: 12px 16px 0;
                padding: 13px 15px;
                background: var(--paper);
                border: 1px solid var(--line);
                border-radius: 12px;
                grid-template-columns: repeat(auto-fit, minmax(168px, 1fr));
                border-left: 3px solid var(--b-500);
            }
            .momc-tb .tb-field { display: flex; flex-direction: column; gap: 5px; min-width: 0; }
            .momc-tb .tb-field > label {
                font-size: .68rem;
                font-weight: 700;
                color: var(--ink-2);
                letter-spacing: .02em;
            }
            .momc-tb .tb-field-wide { grid-column: span 2; }
            .momc-tb .tb-field-checks {
                flex-direction: row;
                flex-wrap: wrap;
                gap: 12px;
                align-items: center;
            }
            .momc-tb .tb-sel, .momc-tb .tb-date {
                font-family: inherit;
                font-size: .77rem;
                color: var(--ink);
                background: var(--sand);
                border: 1px solid var(--line);
                border-radius: 8px;
                padding: 6px 9px;
                width: 100%;
                min-width: 0;
                cursor: pointer;
            }
            .momc-tb .tb-sel:focus, .momc-tb .tb-date:focus {
                outline: 0;
                border-color: var(--t-500);
            }
            .momc-tb .tb-range {
                display: grid;
                grid-template-columns: 1fr auto 1fr;
                align-items: center;
                gap: 6px;
            }
            .momc-tb .tb-dash { color: var(--ink-2); font-size: .8rem; }
            .momc-tb .tb-check {
                display: inline-flex;
                align-items: center;
                gap: 5px;
                font-size: .77rem;
                color: var(--ink-2);
                cursor: pointer;
                white-space: nowrap;
            }
            .momc-tb .tb-check input { accent-color: var(--t-700); cursor: pointer; }

            /* KPIs */
            .momc-tb .tb-kpis {
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
                padding: 13px 16px 0;
            }
            .momc-tb .tb-kpi {
                display: inline-flex;
                align-items: baseline;
                gap: 7px;
                font-family: inherit;
                background: var(--paper);
                border: 1px solid var(--line);
                border-radius: 10px;
                padding: 7px 12px;
                cursor: pointer;
                transition: border-color .15s, transform .15s;
                border-left: 3px solid var(--kpi-c, var(--t-700));
            }
            .momc-tb .tb-kpi:hover { border-color: var(--t-300); transform: translateY(-1px); }
            .momc-tb .tb-kpi.is-on { border-color: var(--t-500); background: var(--t-050); }
            .momc-tb .tb-kpi-v {
                font-size: 1.02rem;
                font-weight: 700;
                color: var(--kpi-c, var(--t-900));
                line-height: 1;
            }
            .momc-tb .tb-kpi-l { font-size: .72rem; color: var(--ink-2); }

            /* Chips */
            .momc-tb .tb-chips {
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
                align-items: center;
                padding: 11px 16px 0;
            }
            .momc-tb .tb-fchip {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                font-family: inherit;
                background: var(--t-050);
                color: var(--t-900);
                border: 1px solid var(--t-300);
                border-radius: 999px;
                padding: 3px 6px 3px 11px;
                font-size: .73rem;
                cursor: default;
            }
            .momc-tb .tb-fchip b { font-weight: 700; }
            .momc-tb .tb-fchip button {
                border: 0;
                background: rgba(28,97,93,.14);
                color: inherit;
                cursor: pointer;
                border-radius: 999px;
                width: 15px;
                height: 15px;
                line-height: 1;
                font-size: .6rem;
                font-family: inherit;
                padding: 0;
            }
            .momc-tb .tb-fchip button:hover { background: var(--alert); color: #fff; }
            .momc-tb .tb-clear {
                border: 0;
                background: none;
                color: var(--alert);
                cursor: pointer;
                font-family: inherit;
                font-size: .74rem;
                font-weight: 600;
                text-decoration: underline;
                text-underline-offset: 3px;
            }

            /* Board */
            .momc-tb .tb-main {
                display: flex;
                align-items: flex-start;
                gap: 12px;
                padding: 13px 16px 4px;
                min-width: 0;
            }
            .momc-tb .tb-scroll {
                flex: 1 1 auto;
                min-width: 0;
                overflow-x: auto;
                scrollbar-width: thin;
            }
            .momc-tb .tb-board {
                display: flex;
                gap: 11px;
                align-items: flex-start;
                min-height: 320px;
            }
            .momc-tb .tb-col {
                flex: 0 0 268px;
                width: 268px;
                background: rgba(255,255,255,.62);
                border: 1px solid var(--line);
                border-radius: 12px;
                padding: 0 0 8px;
                transition: background .15s, border-color .15s, box-shadow .15s;
            }
            .momc-tb .tb-col.is-over {
                border-color: var(--t-500);
                background: var(--t-050);
                box-shadow: inset 0 0 0 1px var(--t-500);
            }
            .momc-tb .tb-col-head {
                display: flex;
                align-items: center;
                gap: 8px;
                color: #fff;
                background: var(--col-c, var(--t-700));
                padding: 9px 16px;
                border-radius: 11px 11px 0 0;
                clip-path: polygon(0 0, 100% 0, 100% 100%, 12px 100%, 0 calc(100% - 9px));
            }
            .momc-tb .tb-col-t {
                font-size: .8rem;
                font-weight: 700;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .momc-tb .tb-col-n {
                margin-left: auto;
                font-size: .72rem;
                font-weight: 700;
                background: rgba(255,255,255,.22);
                border-radius: 999px;
                padding: 1px 8px;
                flex: none;
            }
            .momc-tb .tb-lock { font-size: .8rem; opacity: .7; cursor: help; }
            .momc-tb .tb-list {
                display: flex;
                flex-direction: column;
                gap: 7px;
                padding: 9px;
                min-height: 64px;
                max-height: 62vh;
                overflow-y: auto;
            }

            /* Cards */
            .momc-tb .tb-card {
                position: relative;
                background: var(--paper);
                border: 1px solid var(--line);
                border-radius: 9px;
                padding: 10px 12px 10px 12px;
                cursor: grab;
                touch-action: pan-y;
                transition: border-color .15s, box-shadow .15s, transform .15s;
            }
            .momc-tb .tb-card::before {
                content: "";
                position: absolute;
                top: 7px;
                bottom: 7px;
                left: 0;
                width: 3px;
                border-radius: 3px;
                background: var(--due-c, var(--b-300));
            }
            .momc-tb .tb-card:hover { border-color: var(--t-300); box-shadow: 0 5px 16px -12px rgba(14,68,66,.6); }
            .momc-tb .tb-card.is-dragging { opacity: .32; }
            .momc-tb .tb-subj {
                font-size: .81rem;
                font-weight: 600;
                line-height: 1.45;
                margin: 0 0 6px;
                padding-right: 18px;
                display: -webkit-box;
                -webkit-line-clamp: 3;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }
            .momc-tb .tb-meta {
                display: flex;
                align-items: center;
                gap: 6px;
                flex-wrap: wrap;
            }
            .momc-tb .tb-chip {
                font-size: .68rem;
                padding: 1px 7px;
                border-radius: 999px;
                background: var(--b-050);
                color: var(--b-700);
                border: 1px solid transparent;
                max-width: 120px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            .momc-tb .tb-chip-due {
                background: var(--due-bg, var(--t-050));
                color: var(--due-fg, var(--t-900));
            }
            .momc-tb .tb-chip-pri {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                background: transparent;
                padding-left: 0;
            }
            .momc-tb .tb-pri-dot {
                width: 7px;
                height: 7px;
                border-radius: 999px;
                flex: none;
            }
            .momc-tb .tb-open {
                position: absolute;
                top: 6px;
                right: 7px;
                border: 0;
                background: none;
                cursor: pointer;
                opacity: .35;
                color: var(--ink-2);
                font-size: .82rem;
                line-height: 1;
                padding: 2px 3px;
                font-family: inherit;
                transition: opacity .15s, color .15s;
            }
            .momc-tb .tb-card:hover .tb-open { opacity: 1; }
            .momc-tb .tb-open:hover { color: var(--t-700); }
            .momc-tb .tb-more {
                position: absolute;
                top: 6px;
                right: 24px;
                border: 0;
                background: none;
                cursor: pointer;
                opacity: .35;
                color: var(--ink-2);
                font-size: .9rem;
                line-height: 1;
                padding: 2px 3px;
                font-family: inherit;
                transition: opacity .15s, color .15s;
            }
            .momc-tb .tb-card:hover .tb-more { opacity: 1; }
            .momc-tb .tb-more:hover { color: var(--t-700); }
            .momc-tb .tb-subj { padding-right: 40px; }
            .momc-tb .tb-who {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                flex: none;
                width: 19px;
                height: 19px;
                border-radius: 999px;
                background: var(--t-700);
                color: #fff;
                font-size: .6rem;
                font-weight: 700;
                margin-left: 2px;
            }
            .momc-tb .tb-prog {
                height: 3px;
                background: var(--sand);
                border-radius: 999px;
                margin-top: 8px;
                overflow: hidden;
            }
            .momc-tb .tb-prog i {
                display: block;
                height: 100%;
                background: var(--t-500);
                border-radius: 999px;
            }
            .momc-tb .tb-late {
                font-size: .68rem;
                font-weight: 700;
                color: var(--alert);
                background: #F6E9E6;
                border-radius: 999px;
                padding: 1px 7px;
            }

            /* Add */
            .momc-tb .tb-add {
                display: flex;
                gap: 6px;
                padding: 0 9px;
            }
            .momc-tb .tb-add input {
                flex: 1;
                min-width: 0;
                font-family: inherit;
                font-size: .76rem;
                color: var(--ink);
                background: var(--paper);
                border: 1px dashed var(--line);
                border-radius: 8px;
                padding: 7px 10px;
            }
            .momc-tb .tb-add input:focus {
                outline: 0;
                border-color: var(--t-500);
                border-style: solid;
            }
            .momc-tb .tb-add button {
                border: 0;
                background: var(--t-700);
                color: #fff;
                border-radius: 8px;
                padding: 0 11px;
                font-size: .95rem;
                cursor: pointer;
                font-family: inherit;
            }
            .momc-tb .tb-empty {
                font-size: .74rem;
                color: var(--ink-2);
                text-align: center;
                padding: 16px 8px;
                border: 1px dashed var(--line);
                border-radius: 8px;
            }
            .momc-tb .tb-err {
                padding: 22px 16px;
                font-size: .8rem;
                color: var(--alert);
                text-align: center;
            }
            .momc-tb .tb-hint {
                padding: 10px 16px 0;
                font-size: .7rem;
                color: var(--ink-2);
                opacity: .85;
            }

            /* Toast */
            .tb-toast {
                position: fixed;
                z-index: 9999;
                right: 22px;
                bottom: 22px;
                background: var(--t-900);
                color: #fff;
                font-size: .78rem;
                padding: 9px 14px;
                border-radius: 9px;
                box-shadow: 0 14px 30px -14px rgba(0,0,0,.55);
                max-width: 330px;
                display: none;
            }
            .tb-toast.tb-toast-err { background: var(--alert); }

            /* Menu */
            .momc-tb-menu {
                position: fixed;
                z-index: 9998;
                width: 274px;
                max-height: 76vh;
                overflow-y: auto;
                background: #fff;
                border: 1px solid #DFE3DE;
                border-radius: 12px;
                padding: 11px 12px;
                box-shadow: 0 20px 44px -18px rgba(0,0,0,.45);
                font-family: "Qamra","IBM Plex Sans Arabic","Noto Kufi Arabic",Inter,system-ui,sans-serif;
                color: #16211F;
            }
            .momc-tb-menu[dir="rtl"] { text-align: right; }
            .momc-tb-menu h5 {
                margin: 0 0 8px;
                font-size: .78rem;
                font-weight: 700;
                line-height: 1.4;
                color: #0E4442;
            }
            .momc-tb-menu .mn-sec { margin-top: 10px; }
            .momc-tb-menu .mn-sec > span {
                display: block;
                font-size: .66rem;
                font-weight: 700;
                color: #5C6A68;
                margin-bottom: 5px;
                letter-spacing: .02em;
            }
            .momc-tb-menu .mn-row { display: flex; flex-wrap: wrap; gap: 5px; }
            .momc-tb-menu button.mn-b {
                font-family: inherit;
                font-size: .72rem;
                cursor: pointer;
                border: 1px solid #DFE3DE;
                background: #F1F1EC;
                color: #16211F;
                border-radius: 999px;
                padding: 4px 10px;
            }
            .momc-tb-menu button.mn-b:hover { border-color: #2F8078; background: #E6EFEE; }
            .momc-tb-menu button.mn-b.is-on { background: #1C615D; border-color: #1C615D; color: #fff; }
            .momc-tb-menu button.mn-b[disabled] { opacity: .4; cursor: default; }
            .momc-tb-menu .mn-who {
                display: inline-flex;
                align-items: center;
                gap: 5px;
                font-size: .72rem;
                background: #E6EFEE;
                border-radius: 999px;
                padding: 3px 5px 3px 10px;
            }
            .momc-tb-menu .mn-who button {
                border: 0;
                background: rgba(28,97,93,.16);
                border-radius: 999px;
                cursor: pointer;
                width: 15px;
                height: 15px;
                font-size: .6rem;
                line-height: 1;
                padding: 0;
                font-family: inherit;
            }
            .momc-tb-menu .mn-who button:hover { background: #9C4A3C; color: #fff; }
            .momc-tb-menu select.mn-sel {
                width: 100%;
                font-family: inherit;
                font-size: .73rem;
                padding: 5px 8px;
                border: 1px solid #DFE3DE;
                border-radius: 8px;
                background: #F1F1EC;
                color: #16211F;
            }
            .momc-tb-menu .mn-foot {
                display: flex;
                gap: 6px;
                margin-top: 12px;
                padding-top: 10px;
                border-top: 1px solid #DFE3DE;
            }
            .momc-tb-menu .mn-open {
                flex: 1;
                border: 0;
                background: #1C615D;
                color: #fff;
                border-radius: 8px;
                padding: 7px;
                font-family: inherit;
                font-size: .74rem;
                font-weight: 600;
                cursor: pointer;
            }
            .momc-tb-menu .mn-open:hover { background: #0E4442; }

            /* Busy state */
            .is-busy .tb-ico {
                animation: tb-spin .8s linear infinite;
            }
            @keyframes tb-spin {
                to { transform: rotate(360deg); }
            }

            /* Ghost while dragging */
            .momc-tb-ghost {
                position: fixed;
                z-index: 2000;
                pointer-events: none;
                opacity: .95;
                transform: rotate(-1.5deg);
                box-shadow: 0 16px 34px -14px rgba(0,0,0,.45);
                background: #fff;
                border: 1px solid #1C615D;
                border-radius: 9px;
                padding: 10px 12px;
                font-family: "Qamra","IBM Plex Sans Arabic","Noto Kufi Arabic",Inter,system-ui,sans-serif;
                font-size: .81rem;
                font-weight: 600;
                max-width: 250px;
            }

            /* Dark theme */
            [data-theme="dark"] .momc-tb {
                --sand: #1B1F1E;
                --paper: #232928;
                --ink: #E7ECEA;
                --ink-2: #9AA8A5;
                --line: #343C3B;
                --t-900: #8FC7C1;
                --t-050: #223230;
                --b-050: #2B2721;
            }
            [data-theme="dark"] .momc-tb .tb-col { background: rgba(35,41,40,.6); }
            [data-theme="dark"] .momc-tb .tb-fchip { background: #223230; border-color: #2F8078; }
            [data-theme="dark"] .momc-tb .tb-prog { background: #2E3534; }
            [data-theme="dark"] .momc-tb-menu { background: #232928; border-color: #343C3B; color: #E7ECEA; }
            [data-theme="dark"] .momc-tb-menu button.mn-b { background: #1B1F1E; border-color: #343C3B; color: #E7ECEA; }
            [data-theme="dark"] .momc-tb-menu select.mn-sel { background: #1B1F1E; border-color: #343C3B; color: #E7ECEA; }
            [data-theme="dark"] .momc-tb .tb-late { background: #3A2622; }
            [data-theme="dark"] .momc-tb-ghost { background: #232928; color: #E7ECEA; }

            /* Responsive */
            @media (max-width: 980px) {
                .momc-tb .tb-main { flex-direction: column; }
                .momc-tb .tb-tree { flex: none; width: 100%; max-height: 236px; }
                .momc-tb .tb-scroll { width: 100%; }
                .momc-tb .tb-panel { grid-template-columns: repeat(2, minmax(0, 1fr)); }
                .momc-tb .tb-field-wide { grid-column: span 2; }
            }
            @media (max-width: 640px) {
                .momc-tb .tb-head { flex-direction: column; align-items: stretch; }
                .momc-tb .tb-head-actions { flex-wrap: wrap; }
                .momc-tb .tb-head-actions .tb-btn { flex: 1; justify-content: center; }
                .momc-tb .tb-panel { grid-template-columns: 1fr; }
                .momc-tb .tb-field-wide { grid-column: span 1; }
                .momc-tb .tb-col { flex: 0 0 86vw; width: 86vw; }
                .momc-tb .tb-bar { flex-direction: column; align-items: stretch; }
                .momc-tb .tb-inline { justify-content: space-between; }
                .momc-tb .tb-search input { width: 100%; }
                .momc-tb .tb-count { text-align: center; }
                .momc-tb-menu {
                    left: 0 !important;
                    right: 0 !important;
                    top: auto !important;
                    bottom: 0 !important;
                    width: auto !important;
                    max-width: none;
                    max-height: 74vh;
                    border-radius: 16px 16px 0 0;
                    border-bottom: 0;
                    padding: 16px;
                    box-shadow: 0 -18px 46px -18px rgba(0,0,0,.5);
                }
                .tb-toast {
                    right: 12px;
                    bottom: 12px;
                    max-width: none;
                    text-align: center;
                }
            }
            .momc-tb .tb-tree { display: none; }
            .momc-tb .tb-tree:not([hidden]) { display: flex; }
        `;
        container.appendChild(style);

        // Bind events and load data
        document.querySelector('[data-role="group"]')?.addEventListener('change', (e) => {
            group = e.target.value;
            render();
        });

        document.querySelector('[data-role="lang"]')?.addEventListener('click', () => {
            lang = lang === 'ar' ? 'en' : 'ar';
            frappe.boot.user.language = lang;
            document.querySelector('.momc-tb').setAttribute('dir', lang === 'ar' ? 'rtl' : 'ltr');
            document.querySelector('.momc-tb').setAttribute('data-lang', lang);
            document.querySelector('[data-role="lang-label"]').textContent = t('langLabel');
            document.querySelector('.tb-title').textContent = t('title');
            document.querySelector('.tb-sub').textContent = t('subtitle');
            document.querySelector('[data-role="export"] span:last-child').textContent = t('export');
            document.querySelector('[data-role="refresh"] span:last-child').textContent = t('refresh');
            document.querySelector('.tb-inline-l').textContent = t('groupBy');
            document.querySelector('[data-role="filters-toggle"] span:not(.tb-badge):not(.tb-ico)').textContent = t('filters');
            document.querySelector('[data-role="tree-toggle"] span:not(.tb-ico)').textContent = t('tree');
            document.querySelector('[data-role="q"]').placeholder = t('searchPh');
            document.querySelector('.tb-hint').textContent = t('hint');

            const panel = document.querySelector('[data-role="panel"]');
            if (!panel.hidden) {
                panel.querySelectorAll('.tb-field > label').forEach((label, i) => {
                    const labels = [t('fStatus'), t('fPriority'), t('fProject'), t('fAssignee'), t('fDue'), t('fSort'), '', t('fViews')];
                    if (i < labels.length) label.textContent = labels[i];
                });
            }

            buildControls();
            render();
        });

        document.querySelector('[data-role="refresh"]')?.addEventListener('click', load);
        document.querySelector('[data-role="export"]')?.addEventListener('click', exportXlsx);

        // Filter toggles
        const toggle = document.querySelector('[data-role="filters-toggle"]');
        const panel = document.querySelector('[data-role="panel"]');
        if (toggle && panel) {
            toggle.addEventListener('click', () => {
                panel.hidden = !panel.hidden;
                toggle.setAttribute('aria-expanded', String(!panel.hidden));
            });
        }

        // Filter changes
        document.querySelector('[data-role="q"]')?.addEventListener('input', (e) => {
            F.q = e.target.value;
            document.querySelector('[data-role="q-clear"]').hidden = !F.q;
            render();
        });

        document.querySelector('[data-role="q-clear"]')?.addEventListener('click', () => {
            F.q = '';
            document.querySelector('[data-role="q"]').value = '';
            document.querySelector('[data-role="q-clear"]').hidden = true;
            render();
        });

        ['status', 'priority', 'project', 'assignee', 'sort'].forEach(key => {
            document.querySelector(`[data-role="${key}"]`)?.addEventListener('change', (e) => {
                F[key] = e.target.value;
                render();
            });
        });

        document.querySelector('[data-role="preset"]')?.addEventListener('change', (e) => {
            F.preset = e.target.value;
            if (F.preset) { F.from = '';
                F.to = ''; }
            render();
        });

        ['from', 'to'].forEach(key => {
            document.querySelector(`[data-role="${key}"]`)?.addEventListener('change', (e) => {
                F.preset = '';
                F[key] = e.target.value;
                render();
            });
        });

        document.querySelector('[data-role="mine"]')?.addEventListener('change', (e) => {
            F.mine = e.target.checked;
            render();
        });

        document.querySelector('[data-role="openonly"]')?.addEventListener('change', (e) => {
            F.open = e.target.checked;
            render();
        });

        document.querySelector('[data-role="unassigned"]')?.addEventListener('change', (e) => {
            F.unassigned = e.target.checked;
            render();
        });

        // Initial load
        buildControls();
        load();
    };

    init();
}