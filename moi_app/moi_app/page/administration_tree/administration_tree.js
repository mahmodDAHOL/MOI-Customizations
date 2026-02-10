frappe.pages['administration-tree'].on_page_load = function (wrapper) {
	injectTreeCSS();

	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'شجرة القرار الإداري',
		single_column: true
	});

	var html = `
	<div class="form-dashboard-section mb-4 sticky-filters">
		<div class="d-flex justify-content-between align-items-center">
			<h6><i class="fa fa-sitemap text-muted"></i> شجرة القرار الإداري</h6>
			<div>
				<button class="btn btn-xs btn-default btn-expand-all">
					<i class="fa fa-plus-square-o"></i> توسيع الكل
				</button>
				<button class="btn btn-xs btn-default ml-2 btn-collapse-all">
					<i class="fa fa-minus-square-o"></i> طي الكل
				</button>
			</div>
		</div>

		<div class="row mt-3">
			<div class="col-md-3">
				<label class="control-label">الجهة</label>
				<select id="filter-company" class="filter-company form-control input-sm">
					<option value="">اختر الجهة...</option>
				</select>
			</div>
			<div class="col-md-3">
				<label class="control-label">القسم</label>
				<select id="filter-department" class="filter-department form-control input-sm">
					<option value="">اختر القسم...</option>
				</select>
			</div>
			<div class="col-md-3">
				<label class="control-label">الدائرة / المكتب</label>
				<select id="filter-office" class="filter-office form-control input-sm">
					<option value="">اختر الدائرة / المكتب...</option>
				</select>
			</div>
			<div class="col-md-3">
				<label class="control-label">الشعبة</label>
				<select id="filter-section" class="filter-section form-control input-sm">
					<option value="">اختر الشعبة...</option>
				</select>
			</div>
		</div>
	</div>

	<div id="tree-container" class="decision-tree-container">
		<!-- tree -->
	</div>
`;

	$(page.body).html(html);

	// Debounce
	const debounce = (func, wait) => {
		let timeout;
		return (...args) => {
			clearTimeout(timeout);
			timeout = setTimeout(() => func.apply(this, args), wait);
		};
	};

	const debouncedRefresh = debounce(refreshTree, 300);
	$('.filter-company, .filter-department, .filter-office, .filter-section').on('input', debouncedRefresh);
	$('.btn-expand-all').on('click', expandAll);
	$('.btn-collapse-all').on('click', collapseAll);

	refreshTree();
};

// ─── CSS for Decision Tree ───────────────────────────────
function injectTreeCSS() {
	const id = 'decision-tree-css';
	if (document.getElementById(id)) return;

	const style = document.createElement('style');
	style.id = id;
	style.textContent = `

		.decision-tree {
			display: flex;
			flex-direction: row-reverse;
			align-items: flex-start;
			padding: 20px 0;
		}
		.tree-node {
			background: #f1f5f9;
			border: 1px solid #cbd5e1;
			border-radius: 8px;
			padding: 12px 16px;
			margin: 8px 0;
			min-width: 220px;
			max-width: 280px;
			box-shadow: 0 1px 3px rgba(0,0,0,0.05);
			position: relative;
		}
		.tree-node.dept {
			background: #dbeafe;
			border-color: #93c5fd;
			font-weight: 600;
			color: #1e40af;
		}
		.tree-node.office {
			background: #fffbeb;
			border-color: #fbbf24;
			color: #92400e;
		}
		.tree-node.section {
			background: #dcfce7;
			border-color: #86efac;
			color: #166534;
			font-size: 0.95em;
		}
		.level-group {
			display: flex;
			flex-direction: column;
			margin-left: 60px;
			position: relative;
		}
		.level-group::before {
			content: '';
			position: absolute;
			top: 0;
			bottom: 0;
			left: -30px;
			width: 2px;
			background: #cbd5e1;
			z-index: 0;
		}
		.tree-node::before {
			content: '';
			position: absolute;
			right: -30px;
			top: 50%;
			width: 30px;
			height: 2px;
			background: #cbd5e1;
			z-index: 1;
		}
		.collapse-toggle {
			position: absolute;
			left: -45px;
			top: 50%;
			transform: translateY(-50%);
			width: 24px;
			height: 24px;
			background: #94a3b8;
			color: white;
			border-radius: 50%;
			display: flex;
			align-items: center;
			justify-content: center;
			font-size: 12px;
			cursor: pointer;
			z-index: 2;
		}
		.collapse-toggle.empty { display: none; }
		.collapsed .level-group {
			display: none !important;
		}
		.badge {
			background: #e2e8f0;
			color: #475569;
			font-size: 0.7em;
			padding: 2px 6px;
			border-radius: 10px;
			margin-top: 4px;
			display: inline-block;
		}
		.controls-row { margin-top: 16px; }
		@media print {
			.decision-tree { flex-direction: column; }
			.level-group { margin-left: 0; }
			.level-group::before { display: none; }
			.tree-node::before { display: none; }
		}
.decision-tree-container {
	overflow-x: auto;
	background: #fff;

	padding-bottom: 12px; /* for scrollbar spacing */
	scrollbar-width: thin; /* Firefox */
	scrollbar-height: thin; /* Firefox */
	scrollbar-color: #cbd5e1 #f8fafc; /* thumb / track */
}

.decision-tree-container::-webkit-scrollbar {
	height: 8px;
}

.decision-tree-container::-webkit-scrollbar-track {
	background: #f8fafc;
	border-radius: 4px;
}

.decision-tree-container::-webkit-scrollbar-thumb {
	background: #cbd5e1;
	border-radius: 4px;
}

.decision-tree-container::-webkit-scrollbar-thumb:hover {
	background: #94a3b8;
}

.decision-tree {
	/* 🌐 2D Growth: expands as needed in X and Y */
	display: inline-flex;
	flex-direction: row-reverse;       /* RTL: root on right */
	min-width: fit-content;            /* ← allows horizontal overflow */
	min-height: fit-content;           /* ← allows vertical overflow */

	/* Spacing & alignment */
	padding: 20px;
	gap: 24px;                          /* space between department columns */

	/* Prevent unwanted wrapping */
	flex-wrap: nowrap;                 /* keep all dept columns in one row */
	align-items: flex-start;           /* top-align tall columns */

	/* Optional: subtle background for debugging */
	/* background: #fbfcfd; */
}
/* ➕ Draggable feedback */
.decision-tree-container {
	cursor: grab;
	overflow: auto;
	max-height: calc(100vh - 250px); /* viewport minus header/filters */
	/* keep other styles */
}

.decision-tree-container.dragging {
	cursor: grabbing;
	transition: none;
}
	
	`;
	document.head.appendChild(style);
}

// ─── Data Loading ────────────────────────────────────────
function refreshTree() {

	let company = $('#filter-company').val();
	company = company ? company.trim() : '';

	let department = $('#filter-department').val();
	department = department ? department.trim() : '';

	let office = $('#filter-office').val();
	office = office ? office.trim() : '';

	let section = $('#filter-section').val();
	section = section ? section.trim() : '';
	frappe.call({
		method: 'moi_app.moi_app.page.administration_tree.administration_tree.get_administration_tree',
		args: { office: office, department: department, section: section, company: company },
		callback: (r) => {
			renderDecisionTree(r.message || []);
		}
	});
}

// ─── Decision Tree Renderer ──────────────────────────────
function renderDecisionTree(data) {
	if (!data.length) {
		$('#tree-container').html('<div class="text-muted text-center mt-5">لا توجد بيانات مطابقة</div>');
		return;
	}

	let html = `<div class="decision-tree">

			<div class="decision-tree" id="decision-tree-root">
	`;

	// Render departments (first level)
	data.forEach(dept => {
		const hasOffices = dept.offices && dept.offices.length > 0;
		html += `

			<div class="level-group">
				<div class="tree-node dept ${hasOffices ? '' : 'no-children'}" data-level="dept">
					${hasOffices ? `<div class="collapse-toggle" data-action="toggle">+</div>` : ''}
					<div>${esc(dept.name)}</div>
					${hasOffices ? `<div class="badge">${dept.offices.length} دوائر</div>` : ''}
					${dept.emp_num !=0 ? `<div class="badge">${dept.emp_num} موظف</div>` : ''}
				</div>
				${hasOffices ? renderOfficesAsGroup(dept.offices) : ''}
			</div>
		`;
	});

	html += `</div>`;
	$('#tree-container').html(html);
	makeTreeDraggable();
	initZoom();
	// Bind toggle events
	$('[data-action="toggle"]').on('click', function (e) {
		e.stopPropagation();
		const $toggle = $(this);
		const $group = $toggle.closest('.level-group');
		const $node = $toggle.closest('.tree-node');

		$group.toggleClass('collapsed');
		const isCollapsed = $group.hasClass('collapsed');
		$toggle.text(isCollapsed ? '+' : '−');
	});



}

let zoomState = {
	scale: 1,
	minScale: 0.5,
	maxScale: 2.0,
	container: null,
	tree: null,
	zoomLevelEl: null
};

function initZoom() {
	zoomState.container = document.querySelector('.decision-tree-container');
	zoomState.tree = document.getElementById('decision-tree-root');
	zoomState.zoomLevelEl = document.querySelector('.zoom-level');
	
	if (!zoomState.container || !zoomState.tree) return;

	// 🖱️ Mouse wheel zoom (Ctrl + Scroll)
	zoomState.container.addEventListener('wheel', (e) => {
		if (!e.ctrlKey) return;
		
		e.preventDefault();
		const delta = e.deltaY > 0 ? -0.1 : 0.1; // reverse for natural feel
		applyZoom(delta, e);
	});

	// 🔘 Buttons
	document.querySelector('.zoom-in')?.addEventListener('click', () => applyZoom(0.1));
	document.querySelector('.zoom-out')?.addEventListener('click', () => applyZoom(-0.1));
	document.querySelector('.zoom-reset')?.addEventListener('click', resetZoom);
}

function applyZoom(delta, e) {
	const newScale = Math.min(
		zoomState.maxScale,
		Math.max(zoomState.minScale, zoomState.scale + delta)
	);
	
	if (newScale === zoomState.scale) return;
	
	// 🔍 Scroll-centered zoom (cursor as pivot)
	if (e) {
		const rect = zoomState.container.getBoundingClientRect();
		const mouseX = e.clientX - rect.left;
		const mouseY = e.clientY - rect.top;
		
		// Adjust scroll to keep mouse position fixed
		const scrollX = zoomState.container.scrollLeft;
		const scrollY = zoomState.container.scrollTop;
		
		const newScrollX = mouseX / zoomState.scale - mouseX / newScale + scrollX;
		const newScrollY = mouseY / zoomState.scale - mouseY / newScale + scrollY;
		
		zoomState.container.scrollLeft = newScrollX;
		zoomState.container.scrollTop = newScrollY;
	}
	
	// Apply scale
	zoomState.scale = newScale;
	zoomState.tree.style.transform = `scale(${zoomState.scale})`;
	
	// Update UI
	const percent = Math.round(zoomState.scale * 100);
	zoomState.zoomLevelEl.textContent = `${percent}%`;
}

function resetZoom() {
	zoomState.scale = 1;
	zoomState.tree.style.transform = 'scale(1)';
	zoomState.container.scrollTo(0, 0);
	zoomState.zoomLevelEl.textContent = '100%';
}

function renderOfficesAsGroup(offices) {
	let html = `<div class="level-group">`;

	offices.forEach(office => {
		const hasSections = office.sections && office.sections.length > 0;
		html += `
			<div class="tree-node office ${hasSections ? '' : 'no-children'}" data-level="office">
				${hasSections ? `<div class="collapse-toggle" data-action="toggle">+</div>` : ''}
				<div>${esc(office.name)}</div>
				${hasSections ? `<div class="badge">${office.sections.length} شعب</div>` : ''}
				${office.emp_num != 0 ? `<div class="badge">${office.emp_num} موظف</div>` : ''}
			</div>
			${hasSections ? renderSectionsAsGroup(office.sections) : ''}
		`;
	});

	html += `</div>`;
	return html;
}

function renderSectionsAsGroup(sections) {
	let html = `<div class="level-group">`;

	sections.forEach(sec => {
		html += `
			<div class="tree-node section">
				<div>${esc(sec.name)}</div>
				${sec.emp_num !=0 ? `<div class="badge">${sec.emp_num} موظف</div>` : ''}
			</div>
		`;
	});

	html += `</div>`;
	return html;
}

// ─── Controls ────────────────────────────────────────────
function expandAll() {
	$('.level-group').removeClass('collapsed');
	$('.collapse-toggle').text('−');
}

function collapseAll() {
	$('.level-group').addClass('collapsed');
	$('.collapse-toggle').text('+');
}

// ─── Utils ───────────────────────────────────────────────
function esc(s) {
	if (s == null) return '';
	s = String(s);
	return s.replace(/[&<>"']/g, c =>
		({ '&': '&amp;', '<': '<', '>': '>', '"': '&quot;', "'": '&#39;' }[c])
	);
}

function makeTreeDraggable() {
	const container = document.querySelector('.decision-tree-container');
	if (!container) return;

	let isDragging = false;
	let startX, startY;
	let scrollLeft, scrollTop;

	const startDrag = (e) => {
		isDragging = true;
		container.classList.add('dragging');

		// Get initial scroll & pointer position
		scrollLeft = container.scrollLeft;
		scrollTop = container.scrollTop;

		const clientX = e.clientX || (e.touches && e.touches[0] ? e.touches[0].clientX : 0);
		const clientY = e.clientY || (e.touches && e.touches[0] ? e.touches[0].clientY : 0);

		startX = clientX;
		startY = clientY;

		e.preventDefault(); // Critical: prevents text selection & touch scroll
	};

	const drag = (e) => {
		if (!isDragging) return;

		const clientX = e.clientX || (e.touches && e.touches[0] ? e.touches[0].clientX : 0);
		const clientY = e.clientY || (e.touches && e.touches[0] ? e.touches[0].clientY : 0);

		// Calculate delta (direction-agnostic)
		const deltaX = clientX - startX;
		const deltaY = clientY - startY;

		// Update scroll position (works in RTL too — scrollLeft handles it)
		container.scrollLeft = scrollLeft - deltaX;
		container.scrollTop = scrollTop - deltaY;

		e.preventDefault();
	};

	const stopDrag = () => {
		isDragging = false;
		container.classList.remove('dragging');
	};

	// 🖱️ Mouse events
	container.addEventListener('mousedown', startDrag);
	window.addEventListener('mousemove', drag);
	window.addEventListener('mouseup', stopDrag);

	// 📱 Touch events
	container.addEventListener('touchstart', startDrag, { passive: false });
	window.addEventListener('touchmove', drag, { passive: false });
	window.addEventListener('touchend', stopDrag);
}




// ── 1. Populate Companies on load ───────────────────────────────────────
frappe.db.get_list('Company', {
    fields: ['name'],
    limit: 999,
    order_by: 'name asc'
}).then(companies => {
    const $company = $('#filter-company');
    $company.empty().append('<option value="">اختر الجهة...</option>');
    companies.forEach(company => {
        $company.append(`<option value="${frappe.utils.escape_html(company.name)}">${frappe.utils.escape_html(company.name)}</option>`);
    });
});

// ── Helper: Reset & Disable Select ───────────────────────────────────────
function resetSelect($select, placeholder = '...') {
    $select.empty().append(`<option value="">${placeholder}</option>`).prop('disabled', true);
}

// ── 2. Handle Company Change ─────────────────────────────────────────────
function handleCompanyChange(selectedCompany) {
    const $department = $('#filter-department');
    const $office = $('#filter-office');
    const $section = $('#filter-section');

    // 🔁 Reset all downstream fields
    resetSelect($department, 'جارٍ التحميل...');
    resetSelect($office, 'اختر الدائرة / المكتب...');
    resetSelect($section, 'اختر الشعبة...');

    if (!selectedCompany) return;

    frappe.db.get_list('Department', {
        fields: ['name'],
        filters: { 'company': selectedCompany },  // ✅ exact match for Link field
        limit: 999,
        order_by: 'name asc'
    }).then(departments => {
        resetSelect($department, 'اختر القسم...'); // re-enable with options
        departments.forEach(dept => {
            $department.append(`<option value="${frappe.utils.escape_html(dept.name)}">${frappe.utils.escape_html(dept.name)}</option>`);
        });
        $department.prop('disabled', false);
    });
}

// ── 3. Handle Department Change ──────────────────────────────────────────
function handleDepartmentChange(selectedDepartment) {
    const $office = $('#filter-office');
    const $section = $('#filter-section');

    // 🔁 Reset downstream
    resetSelect($office, 'جارٍ التحميل...');
    resetSelect($section, 'اختر الشعبة...');

    if (!selectedDepartment) return;

    frappe.db.get_list('Office', {
        fields: ['name'],
        filters: { 'department': selectedDepartment },  // ✅ exact match
        limit: 999,
        order_by: 'name asc'
    }).then(offices => {
        resetSelect($office, 'اختر الدائرة / المكتب...');
        offices.forEach(office => {
            $office.append(`<option value="${frappe.utils.escape_html(office.name)}">${frappe.utils.escape_html(office.name)}</option>`);
        });
        $office.prop('disabled', false);
    });
}

// ── 4. Handle Office Change ──────────────────────────────────────────────
function handleOfficeChange(selectedOffice) {
    const $section = $('#filter-section');

    resetSelect($section, 'جارٍ التحميل...');

    if (!selectedOffice) return;

    frappe.db.get_list('section', {  // ✅ Capital 'S' — doctype name is case-sensitive!
        fields: ['name'],
        filters: { 'office': selectedOffice },  // ✅ exact match
        limit: 999,
        order_by: 'name asc'
    }).then(sections => {
        resetSelect($section, 'اختر الشعبة...');
        sections.forEach(section => {
            $section.append(`<option value="${frappe.utils.escape_html(section.name)}">${frappe.utils.escape_html(section.name)}</option>`);
        });
        $section.prop('disabled', false);
    });
}

// ── 5. Bind All Events (Using Delegation) ───────────────────────────────
$(document).on('change', '#filter-company', function() {
    handleCompanyChange($(this).val());
});

$(document).on('change', '#filter-department', function() {
    handleDepartmentChange($(this).val());
});

$(document).on('change', '#filter-office', function() {
    handleOfficeChange($(this).val());
});