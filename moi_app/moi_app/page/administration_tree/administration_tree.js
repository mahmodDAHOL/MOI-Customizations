frappe.pages['administration-tree'].on_page_load = function (wrapper) {
	injectTreeCSS();

	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'الهيكل الإداري',
		single_column: true
	});

	var html = `
	<div class="admin-tree-wrapper" dir="rtl">

		<!-- ════════ Toolbar ════════ -->
		<div class="atv-toolbar">
			<div class="atv-toolbar-filters">
				<button type="button" class="atv-filter-icon-btn" title="تصفية">
					<i class="fa fa-filter"></i>
				</button>
				<select id="filter-company" class="atv-filter-select">
					<option value="">وزارة الإعلام</option>
				</select>
				<select id="filter-department" class="atv-filter-select" disabled>
					<option value="">اختر مديرية</option>
				</select>
				<select id="filter-office" class="atv-filter-select" disabled>
					<option value="">اختر دائرة</option>
				</select>
				<select id="filter-section" class="atv-filter-select" disabled>
					<option value="">اختر شعبة</option>
				</select>
			</div>
			<div class="atv-toolbar-actions">
				<span class="atv-results-count">
					إجمالي النتائج:
					<span class="atv-count-num" id="resultCount">0</span>
					وحدة
				</span>
				<button type="button" class="atv-action-btn btn-collapse-all">
					<span class="atv-sign">−</span>
					<span>طي الكل</span>
				</button>
				<button type="button" class="atv-action-btn btn-expand-all">
					<span class="atv-sign">+</span>
					<span>توسيع الكل</span>
				</button>
			</div>
		</div>

		<!-- ════════ Tree area ════════ -->
		<div class="atv-tree-area">
			<div class="atv-zoom-panel">
				<button type="button" class="atv-zoom-reset" title="إعادة التعيين">
					<i class="fa fa-crosshairs"></i>
				</button>
				<span class="atv-zoom-divider"></span>
				<button type="button" class="atv-zoom-out" title="تصغير">−</button>
				<span class="atv-zoom-level">100%</span>
				<button type="button" class="atv-zoom-in" title="تكبير">+</button>
			</div>

			<div id="tree-container" class="atv-tree-container">
				<div class="atv-tree-stage" id="treeStage">
					<svg class="atv-connectors-layer" id="connectors" xmlns="http://www.w3.org/2000/svg"></svg>
					<div class="atv-tree" id="tree"></div>
				</div>
			</div>
		</div>
	</div>
	`;

	$(page.body).html(html);

	// ── Debounce helper ──
	const debounce = (func, wait) => {
		let timeout;
		return (...args) => {
			clearTimeout(timeout);
			timeout = setTimeout(() => func.apply(this, args), wait);
		};
	};

	// ── Bind toolbar actions ──
	$(page.body).find('.btn-expand-all').on('click', () => setExpandedAll(true));
	$(page.body).find('.btn-collapse-all').on('click', () => setExpandedAll(false, /*keepRoot*/true));

	// ── Bind zoom ──
	$(page.body).find('.atv-zoom-in').on('click', () => applyZoom(0.1));
	$(page.body).find('.atv-zoom-out').on('click', () => applyZoom(-0.1));
	$(page.body).find('.atv-zoom-reset').on('click', resetZoom);

	// ── Bind chevron toggles (delegated) ──
	$(page.body).on('click', '.atv-node-chevron', function (e) {
		e.stopPropagation();
		const id = $(this).attr('data-toggle');
		toggleNode(id);
	});

	// ── Pan (drag-to-scroll) ──
	enablePan();

	// ── Initial load ──
	refreshTree();
};

// ──────────────────────────────────────────────────────────
// Internal tree state (built from the backend response)
// ──────────────────────────────────────────────────────────
let TREE_DATA = null;
let _autoId = 0;
const mkId = () => 'n' + (++_autoId);

// ──────────────────────────────────────────────────────────
// CSS injection
// ──────────────────────────────────────────────────────────
function injectTreeCSS() {
	const id = 'admin-tree-css-v2';
	if (document.getElementById(id)) return;

	const style = document.createElement('style');
	style.id = id;
	style.textContent = `

		/* ─────────── Theme tokens ─────────── */
		.admin-tree-wrapper {
			--atv-green-900: #0d3f30;
			--atv-green-800: #134f3d;
			--atv-green-700: #1a5a45;
			--atv-gold-500: #b89058;
			--atv-gold-400: #c9a16a;
			--atv-cream-100: #f5ede0;
			--atv-cream-200: #ede2cd;
			--atv-cream-border: #d9c7a4;
			--atv-blue-50: #eaf2f9;
			--atv-blue-accent: #1f4f8b;
			--atv-blue-text: #173a6a;
			--atv-text-dark: #14342a;
			--atv-text-muted: #5d6b6a;
			--atv-tree-bg: #fbfaf6;
			--atv-line: #bdb29a;

			font-family: "Segoe UI", "Tahoma", "Helvetica Neue", Arial, sans-serif;
			color: var(--atv-text-dark);
			direction: rtl;
		}

		/* ─────────── Toolbar ─────────── */
		.admin-tree-wrapper .atv-toolbar {
			background: #ffffff;
			padding: 14px 18px;
			display: flex;
			align-items: center;
			justify-content: space-between;
			gap: 16px;
			flex-wrap: wrap;
			border: 1px solid #eee;
			border-radius: 10px;
			margin-bottom: 14px;
		}

		.admin-tree-wrapper .atv-toolbar-filters,
		.admin-tree-wrapper .atv-toolbar-actions {
			display: flex;
			align-items: center;
			gap: 10px;
			flex-wrap: wrap;
		}

		.admin-tree-wrapper .atv-toolbar-actions {
			gap: 14px;
		}

		.admin-tree-wrapper .atv-filter-icon-btn {
			width: 40px;
			height: 40px;
			border-radius: 8px;
			border: 1px solid #e5e7eb;
			background: #fff;
			color: var(--atv-text-dark);
			display: flex;
			align-items: center;
			justify-content: center;
			cursor: pointer;
			font-size: 15px;
			padding: 0;
		}

		.admin-tree-wrapper .atv-filter-icon-btn:hover {
			background: #f9fafb;
		}

		.admin-tree-wrapper .atv-filter-select {
			min-width: 170px;
			height: 40px;
			padding: 0 36px 0 14px;
			border: 1px solid #e5e7eb;
			border-radius: 8px;
			background: #fff;
			color: var(--atv-text-dark);
			font-size: 14px;
			font-family: inherit;
			cursor: pointer;
			appearance: none;
			-webkit-appearance: none;
			background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3e%3cpath fill='%23667' d='M6 8.5L2 4.5h8z'/%3e%3c/svg%3e");
			background-repeat: no-repeat;
			background-position: left 12px center;
			background-size: 10px;
			text-align: right;
			box-shadow: none;
		}

		.admin-tree-wrapper .atv-filter-select:hover {
			border-color: #cbd5e1;
		}

		.admin-tree-wrapper .atv-filter-select:focus {
			outline: none;
			border-color: var(--atv-green-700);
			box-shadow: 0 0 0 3px rgba(19, 79, 61, 0.08);
		}

		.admin-tree-wrapper .atv-filter-select:disabled {
			background-color: #f8fafc;
			color: #94a3b8;
			cursor: not-allowed;
		}

		.admin-tree-wrapper .atv-results-count {
			color: var(--atv-text-dark);
			font-size: 14px;
			font-weight: 500;
		}

		.admin-tree-wrapper .atv-count-num {
			color: var(--atv-green-800);
			font-weight: 700;
			margin: 0 4px;
		}

		.admin-tree-wrapper .atv-action-btn {
			display: inline-flex;
			align-items: center;
			gap: 8px;
			padding: 0 16px;
			height: 40px;
			border: 1px solid #e5e7eb;
			border-radius: 8px;
			background: #fff;
			color: var(--atv-text-dark);
			font-size: 14px;
			font-family: inherit;
			font-weight: 500;
			cursor: pointer;
			transition: all 0.15s ease;
		}

		.admin-tree-wrapper .atv-action-btn:hover {
			background: #f9fafb;
			border-color: #cbd5e1;
		}

		.admin-tree-wrapper .atv-action-btn .atv-sign {
			font-size: 18px;
			line-height: 1;
			color: var(--atv-gold-500);
			font-weight: 700;
		}

		/* ─────────── Tree area ─────────── */
		.admin-tree-wrapper .atv-tree-area {
			position: relative;
			height: calc(100vh - 240px);
			min-height: 520px;
			background-color: var(--atv-tree-bg);
			background-image: radial-gradient(circle, #d8d1bf 1px, transparent 1px);
			background-size: 18px 18px;
			border-radius: 10px;
			border: 1px solid #eee;
			overflow: hidden;
		}

		.admin-tree-wrapper .atv-zoom-panel {
			position: absolute;
			top: 18px;
			left: 18px;
			display: flex;
			align-items: center;
			gap: 4px;
			background: #fff;
			border-radius: 999px;
			padding: 6px 10px;
			box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08), 0 4px 12px rgba(0, 0, 0, 0.04);
			z-index: 10;
		}

		.admin-tree-wrapper .atv-zoom-panel button {
			width: 32px;
			height: 32px;
			border: none;
			background: transparent;
			border-radius: 50%;
			color: var(--atv-text-dark);
			cursor: pointer;
			font-size: 15px;
			display: flex;
			align-items: center;
			justify-content: center;
			padding: 0;
		}

		.admin-tree-wrapper .atv-zoom-panel button:hover {
			background: #f3f4f6;
		}

		.admin-tree-wrapper .atv-zoom-level {
			font-size: 13px;
			color: var(--atv-text-dark);
			font-weight: 600;
			min-width: 42px;
			text-align: center;
		}

		.admin-tree-wrapper .atv-zoom-divider {
			width: 1px;
			height: 22px;
			background: #e5e7eb;
			margin: 0 4px;
		}

		.admin-tree-wrapper .atv-tree-container {
			position: absolute;
			inset: 0;
			overflow: auto;
			cursor: grab;
			padding: 80px 40px 40px 40px;
		}

		.admin-tree-wrapper .atv-tree-container.dragging {
			cursor: grabbing;
		}

		.admin-tree-wrapper .atv-tree-container::-webkit-scrollbar {
			width: 10px;
			height: 10px;
		}

		.admin-tree-wrapper .atv-tree-container::-webkit-scrollbar-thumb {
			background: #cbc4b1;
			border-radius: 6px;
		}

		.admin-tree-wrapper .atv-tree-container::-webkit-scrollbar-thumb:hover {
			background: #a89e85;
		}

		.admin-tree-wrapper .atv-tree-stage {
			position: relative;
			display: inline-block;
			min-width: 100%;
			transform-origin: top right;
			transition: transform 0.2s ease;
		}

		.admin-tree-wrapper .atv-connectors-layer {
			position: absolute;
			top: 0;
			right: 0;
			pointer-events: none;
			z-index: 1;
		}

		.admin-tree-wrapper .atv-tree {
			position: relative;
			z-index: 2;
			display: inline-flex;
			flex-direction: row;
			align-items: flex-start;
		}

		.admin-tree-wrapper .atv-tree-row {
			display: flex;
			flex-direction: row;
			align-items: center;
			gap: 80px;
		}

		.admin-tree-wrapper .atv-tree-children {
			display: flex;
			flex-direction: column;
			gap: 14px;
		}

		/* ─────────── Nodes ─────────── */
		.admin-tree-wrapper .atv-node {
			position: relative;
			width: 270px;
			min-height: 78px;
			padding: 16px 20px 14px 20px;
			border-radius: 14px;
			box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04), 0 4px 12px rgba(0, 0, 0, 0.04);
			transition: box-shadow 0.2s ease, transform 0.2s ease;
			display: flex;
			flex-direction: column;
			justify-content: center;
			gap: 8px;
		}

		.admin-tree-wrapper .atv-node:hover {
			box-shadow: 0 2px 4px rgba(0, 0, 0, 0.06), 0 8px 20px rgba(0, 0, 0, 0.07);
			transform: translateY(-1px);
		}

		.admin-tree-wrapper .atv-node-title {
			font-size: 15.5px;
			font-weight: 700;
			line-height: 1.3;
			text-align: right;
		}

		.admin-tree-wrapper .atv-node-stats {
			display: flex;
			align-items: center;
			justify-content: flex-end;
			gap: 18px;
			font-size: 13px;
			color: var(--atv-text-muted);
		}

		.admin-tree-wrapper .atv-node-stat {
			display: inline-flex;
			align-items: center;
			gap: 6px;
			white-space: nowrap;
		}

		.admin-tree-wrapper .atv-node-stat i {
			font-size: 13px;
			opacity: 0.75;
		}

		.admin-tree-wrapper .atv-node-chevron {
			position: absolute;
			bottom: 6px;
			left: 50%;
			transform: translateX(-50%);
			width: 28px;
			height: 18px;
			display: flex;
			align-items: center;
			justify-content: center;
			background: transparent;
			border: none;
			cursor: pointer;
			color: inherit;
			font-size: 11px;
			opacity: 0.75;
			padding: 0;
			transition: opacity 0.15s ease;
		}

		.admin-tree-wrapper .atv-node-chevron:hover {
			opacity: 1;
		}

		/* Ministry (root) — dark green */
		.admin-tree-wrapper .atv-node.ministry {
			background: var(--atv-green-800);
			color: #ffffff;
			padding-right: 76px;
		}

		.admin-tree-wrapper .atv-node.ministry .atv-node-title {
			color: #ffffff;
			font-size: 17px;
		}

		.admin-tree-wrapper .atv-node.ministry .atv-node-stats {
			color: rgba(255, 255, 255, 0.85);
		}

		.admin-tree-wrapper .atv-node.ministry .atv-node-stat i {
			color: var(--atv-gold-400);
			opacity: 1;
		}

		.admin-tree-wrapper .atv-node.ministry .atv-ministry-icon {
			position: absolute;
			top: 50%;
			right: 16px;
			transform: translateY(-50%);
			width: 42px;
			height: 42px;
			border-radius: 10px;
			background: rgba(201, 161, 106, 0.18);
			display: flex;
			align-items: center;
			justify-content: center;
			color: var(--atv-gold-400);
			font-size: 18px;
		}

		.admin-tree-wrapper .atv-node.ministry .atv-node-chevron {
			color: rgba(255, 255, 255, 0.9);
		}

		/* Directorate & Unit (middle) — cream */
		.admin-tree-wrapper .atv-node.directorate,
		.admin-tree-wrapper .atv-node.unit {
			background: var(--atv-cream-100);
			border: 1px solid var(--atv-cream-border);
			color: var(--atv-green-900);
		}

		.admin-tree-wrapper .atv-node.directorate .atv-node-title,
		.admin-tree-wrapper .atv-node.unit .atv-node-title {
			color: var(--atv-green-900);
		}

		.admin-tree-wrapper .atv-node.directorate .atv-node-stats,
		.admin-tree-wrapper .atv-node.unit .atv-node-stats {
			color: #6b5e44;
		}

		.admin-tree-wrapper .atv-node.directorate .atv-node-stat i,
		.admin-tree-wrapper .atv-node.unit .atv-node-stat i {
			color: #8a7a5a;
		}

		/* Office (leaf) — light blue with left accent */
		.admin-tree-wrapper .atv-node.office {
			background: var(--atv-blue-50);
			border: 1px solid #d3e0ee;
			border-left: 4px solid var(--atv-blue-accent);
			color: var(--atv-blue-text);
			min-height: 64px;
		}

		.admin-tree-wrapper .atv-node.office .atv-node-title {
			color: var(--atv-blue-text);
		}

		.admin-tree-wrapper .atv-node.office .atv-node-stats {
			color: #4f6485;
		}

		.admin-tree-wrapper .atv-node.office .atv-node-stat i {
			color: var(--atv-blue-accent);
			opacity: 0.9;
		}

		/* ─────────── Empty / loading state ─────────── */
		.admin-tree-wrapper .atv-empty-state {
			position: absolute;
			inset: 0;
			display: flex;
			flex-direction: column;
			align-items: center;
			justify-content: center;
			padding: 60px 20px;
			color: #94a3b8;
			text-align: center;
			pointer-events: none;
		}

		.admin-tree-wrapper .atv-empty-state i {
			font-size: 48px;
			margin-bottom: 16px;
			opacity: 0.5;
		}

		.admin-tree-wrapper .atv-empty-state h5 {
			color: #64748b;
			margin-bottom: 4px;
			font-size: 16px;
			font-weight: 600;
		}

		.admin-tree-wrapper .atv-empty-state p {
			color: #94a3b8;
			font-size: 13px;
		}

		/* ─────────── Responsive ─────────── */
		@media (max-width: 900px) {
			.admin-tree-wrapper .atv-toolbar {
				padding: 12px 14px;
			}
			.admin-tree-wrapper .atv-filter-select {
				min-width: 140px;
			}
			.admin-tree-wrapper .atv-node {
				width: 240px;
			}
		}

		/* ─────────── Print ─────────── */
		@media print {
			.admin-tree-wrapper .atv-toolbar,
			.admin-tree-wrapper .atv-zoom-panel {
				display: none;
			}
			.admin-tree-wrapper .atv-tree-area {
				height: auto;
				overflow: visible;
				border: none;
				background-image: none;
			}
			.admin-tree-wrapper .atv-tree-container {
				position: relative;
				inset: auto;
				overflow: visible;
			}
		}
	`;
	document.head.appendChild(style);
}

// ──────────────────────────────────────────────────────────
// Refresh tree from backend
// ──────────────────────────────────────────────────────────
function refreshTree() {
	let company = ($('#filter-company').val() || '').trim();
	let department = ($('#filter-department').val() || '').trim();
	let office = ($('#filter-office').val() || '').trim();
	let section = ($('#filter-section').val() || '').trim();

	// Loading state
	$('#tree').empty();
	const $area = $('.atv-tree-area');
	$area.find('.atv-empty-state').remove();
	$area.append(`
		<div class="atv-empty-state">
			<i class="fa fa-spinner fa-spin"></i>
			<h5>جاري التحميل...</h5>
		</div>
	`);

	frappe.call({
		method: 'moi_app.moi_app.page.administration_tree.administration_tree.get_administration_tree',
		args: { office: office, department: department, section: section, company: company },
		callback: (r) => {
			const data = r.message || [];
			$area.find('.atv-empty-state').remove();

			if (!data.length) {
				$area.append(`
					<div class="atv-empty-state">
						<i class="fa fa-sitemap"></i>
						<h5>${company ? 'لا توجد بيانات مطابقة' : 'اختر جهة لعرض الهيكل الإداري'}</h5>
						${company ? '<p>حاول تغيير معايير البحث</p>' : ''}
					</div>
				`);
				$('#resultCount').text('0');
				TREE_DATA = null;
				return;
			}

			TREE_DATA = normalizeTree(data, company || 'الجهة');
			renderTree();
		}
	});
}

// ──────────────────────────────────────────────────────────
// Convert backend payload → internal expandable tree
// Backend shape:
//   [{ name, emp_num, offices: [{ name, emp_num, sections: [{name, emp_num}] }] }]
// Maps to:  ministry (root) → directorate → unit → office (leaf)
// ──────────────────────────────────────────────────────────
function normalizeTree(rawData, companyName) {
	_autoId = 0;

	const root = {
		_id: mkId(),
		name: companyName,
		type: 'ministry',
		employees: 0,
		directorates: rawData.length,
		expanded: true,
		children: []
	};

	rawData.forEach(dept => {
		const offices = dept.offices || [];
		const directorate = {
			_id: mkId(),
			name: dept.name,
			type: 'directorate',
			employees: dept.emp_num || 0,
			directorates: offices.length,
			expanded: false,
			children: []
		};

		offices.forEach(office => {
			const sections = office.sections || [];
			const unit = {
				_id: mkId(),
				name: office.name,
				type: 'unit',
				employees: office.emp_num || 0,
				expanded: false,
				children: []
			};

			sections.forEach(sec => {
				unit.children.push({
					_id: mkId(),
					name: sec.name,
					type: 'office',
					employees: sec.emp_num || 0
				});
			});

			directorate.children.push(unit);
		});

		root.employees += directorate.employees;
		root.children.push(directorate);
	});

	// Auto-expand the first branch (mirrors the design reference)
	if (root.children[0]) {
		root.children[0].expanded = true;
		if (root.children[0].children[0]) {
			root.children[0].children[0].expanded = true;
		}
	}

	return root;
}

// ──────────────────────────────────────────────────────────
// Render
// ──────────────────────────────────────────────────────────
function chevronFor(node) {
	const hasChildren = node.children && node.children.length > 0;
	if (!hasChildren) return null;
	if (node.expanded) {
		return node.type === 'ministry' ? 'fa-chevron-up' : 'fa-chevron-left';
	}
	return 'fa-chevron-down';
}

function renderNode(node) {
	const hasChildren = node.children && node.children.length > 0;
	const cls = node.type;
	const chev = chevronFor(node);

	const statsParts = [];
	if (node.employees != null && node.employees !== 0) {
		statsParts.push(`<span class="atv-node-stat"><i class="fa fa-users"></i><span>${node.employees} موظف</span></span>`);
	}
	if (node.directorates != null && node.directorates !== 0) {
		statsParts.push(`<span class="atv-node-stat"><i class="fa fa-th-large"></i><span>${node.directorates} مديريات</span></span>`);
	}

	const ministryIcon = node.type === 'ministry'
		? `<div class="atv-ministry-icon"><i class="fa fa-building"></i></div>`
		: '';

	const chevHtml = chev
		? `<button type="button" class="atv-node-chevron" data-toggle="${node._id}" aria-label="تبديل"><i class="fa ${chev}"></i></button>`
		: '';

	const nodeHtml = `
		<div class="atv-node ${cls}" data-id="${node._id}">
			${ministryIcon}
			<div class="atv-node-title">${esc(node.name)}</div>
			<div class="atv-node-stats">${statsParts.join('')}</div>
			${chevHtml}
		</div>
	`;

	let childrenHtml = '';
	if (hasChildren && node.expanded) {
		childrenHtml = `<div class="atv-tree-children">
			${node.children.map(c => `<div class="atv-tree-row" data-row="${c._id}">${renderNode(c)}</div>`).join('')}
		</div>`;
	}

	return nodeHtml + childrenHtml;
}

function renderTree() {
	if (!TREE_DATA) return;
	const $tree = $('#tree');
	$tree.html(`<div class="atv-tree-row" data-row="${TREE_DATA._id}">${renderNode(TREE_DATA)}</div>`);

	// Update count of visible nodes
	const visible = $tree.find('.atv-node').length;
	$('#resultCount').text(visible);

	// Draw connectors after the next paint (so layout has settled)
	requestAnimationFrame(() => {
		drawConnectors();
		// Once more — Arabic font shaping can shift widths slightly
		requestAnimationFrame(drawConnectors);
	});
}

// ──────────────────────────────────────────────────────────
// SVG connectors (curved brackets)
// ──────────────────────────────────────────────────────────
function drawConnectors() {
	const svg = document.getElementById('connectors');
	const tree = document.getElementById('tree');
	if (!svg || !tree) return;

	const w = tree.offsetWidth;
	const h = tree.offsetHeight;
	svg.setAttribute('width', w);
	svg.setAttribute('height', h);
	svg.style.width = w + 'px';
	svg.style.height = h + 'px';

	while (svg.firstChild) svg.removeChild(svg.firstChild);

	const treeRect = tree.getBoundingClientRect();
	const z = (zoomState && zoomState.scale) || 1;

	const rows = tree.querySelectorAll('.atv-tree-row');
	rows.forEach(row => {
		const parentNode = row.querySelector(':scope > .atv-node');
		const childrenBox = row.querySelector(':scope > .atv-tree-children');
		if (!parentNode || !childrenBox) return;

		const childRows = childrenBox.querySelectorAll(':scope > .atv-tree-row');
		if (!childRows.length) return;

		const pRect = parentNode.getBoundingClientRect();
		// Parent's LEFT-middle edge (children sit to the left in the row layout)
		const px = (pRect.left - treeRect.left) / z;
		const py = (pRect.top + pRect.height / 2 - treeRect.top) / z;

		childRows.forEach(cr => {
			const cn = cr.querySelector(':scope > .atv-node');
			if (!cn) return;
			const cRect = cn.getBoundingClientRect();
			const cx = (cRect.right - treeRect.left) / z; // child's right edge
			const cy = (cRect.top + cRect.height / 2 - treeRect.top) / z;

			const midX = (px + cx) / 2;
			const dy = cy - py;
			const absDy = Math.abs(dy);

			let d;
			if (absDy < 1) {
				d = `M ${px} ${py} L ${cx} ${cy}`;
			} else {
				const r = Math.min(14, absDy / 2);
				const sign = dy > 0 ? 1 : -1;
				d = `M ${px} ${py}
					 L ${midX + r} ${py}
					 Q ${midX} ${py} ${midX} ${py + sign * r}
					 L ${midX} ${cy - sign * r}
					 Q ${midX} ${cy} ${midX - r} ${cy}
					 L ${cx} ${cy}`;
			}

			const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
			path.setAttribute('d', d);
			path.setAttribute('fill', 'none');
			path.setAttribute('stroke', '#bdb29a');
			path.setAttribute('stroke-width', '1.5');
			path.setAttribute('stroke-linecap', 'round');
			path.setAttribute('stroke-linejoin', 'round');
			svg.appendChild(path);
		});
	});
}

// ──────────────────────────────────────────────────────────
// Expand / collapse
// ──────────────────────────────────────────────────────────
function findNodeById(node, id) {
	if (!node) return null;
	if (node._id === id) return node;
	for (const c of (node.children || [])) {
		const r = findNodeById(c, id);
		if (r) return r;
	}
	return null;
}

function toggleNode(id) {
	if (!TREE_DATA) return;
	const n = findNodeById(TREE_DATA, id);
	if (!n || !n.children || !n.children.length) return;
	n.expanded = !n.expanded;
	renderTree();
}

function setExpandedAll(value, keepRoot) {
	if (!TREE_DATA) return;
	function walk(n, depth) {
		if (n.children && n.children.length) {
			n.expanded = (keepRoot && depth === 0) ? true : value;
			n.children.forEach(c => walk(c, depth + 1));
		}
	}
	walk(TREE_DATA, 0);
	renderTree();
}

// ──────────────────────────────────────────────────────────
// Zoom
// ──────────────────────────────────────────────────────────
let zoomState = {
	scale: 1,
	min: 0.4,
	max: 2.0
};

function applyZoom(delta, e) {
	const stage = document.getElementById('treeStage');
	const container = document.querySelector('.atv-tree-container');
	if (!stage || !container) return;

	const newScale = Math.min(
		zoomState.max,
		Math.max(zoomState.min, +(zoomState.scale + delta).toFixed(2))
	);
	if (newScale === zoomState.scale) return;

	// Keep the mouse position stable when wheel-zooming
	if (e) {
		const rect = container.getBoundingClientRect();
		const mouseX = e.clientX - rect.left;
		const mouseY = e.clientY - rect.top;
		const newScrollX = mouseX / zoomState.scale - mouseX / newScale + container.scrollLeft;
		const newScrollY = mouseY / zoomState.scale - mouseY / newScale + container.scrollTop;
		container.scrollLeft = newScrollX;
		container.scrollTop = newScrollY;
	}

	zoomState.scale = newScale;
	stage.style.transform = `scale(${zoomState.scale})`;
	$('.atv-zoom-level').text(Math.round(zoomState.scale * 100) + '%');
}

function resetZoom() {
	const stage = document.getElementById('treeStage');
	const container = document.querySelector('.atv-tree-container');
	zoomState.scale = 1;
	if (stage) stage.style.transform = 'scale(1)';
	$('.atv-zoom-level').text('100%');
	if (container) container.scrollTo({ left: container.scrollWidth, top: 0, behavior: 'smooth' });
}

// ──────────────────────────────────────────────────────────
// Pan (drag-to-scroll) + Ctrl+wheel zoom
// ──────────────────────────────────────────────────────────
function enablePan() {
	const container = document.querySelector('.atv-tree-container');
	if (!container) return;

	let isDown = false, startX, startY, sl, st;

	container.addEventListener('mousedown', (e) => {
		// don't pan when clicking interactive elements
		if (e.target.closest('button, select, input, a')) return;
		isDown = true;
		container.classList.add('dragging');
		startX = e.clientX;
		startY = e.clientY;
		sl = container.scrollLeft;
		st = container.scrollTop;
		e.preventDefault();
	});
	window.addEventListener('mousemove', (e) => {
		if (!isDown) return;
		container.scrollLeft = sl - (e.clientX - startX);
		container.scrollTop = st - (e.clientY - startY);
	});
	window.addEventListener('mouseup', () => {
		isDown = false;
		container.classList.remove('dragging');
	});

	container.addEventListener('wheel', (e) => {
		if (!e.ctrlKey) return;
		e.preventDefault();
		const delta = e.deltaY > 0 ? -0.1 : 0.1;
		applyZoom(delta, e);
	}, { passive: false });

	// Redraw connectors if the layout itself changes
	window.addEventListener('resize', () => {
		requestAnimationFrame(drawConnectors);
	});
}

// ──────────────────────────────────────────────────────────
// Utils
// ──────────────────────────────────────────────────────────
function esc(s) {
	if (s == null) return '';
	s = String(s);
	return s.replace(/[&<>"']/g, c =>
		({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
	);
}

// ──────────────────────────────────────────────────────────
// Helper: reset a cascading select to its placeholder
// ──────────────────────────────────────────────────────────
function resetSelect($select, placeholder) {
	$select.empty().append(`<option value="">${placeholder}</option>`).prop('disabled', true);
}

// ──────────────────────────────────────────────────────────
// Populate Companies on load
// ──────────────────────────────────────────────────────────
frappe.db.get_list('Company', {
	fields: ['name'],
	limit: 999,
	order_by: 'name asc'
}).then(companies => {
	const $company = $('#filter-company');
	if (!$company.length) return;
	$company.empty().append('<option value="">اختر جهة</option>');
	companies.forEach(company => {
		$company.append(`<option value="${frappe.utils.escape_html(company.name)}">${frappe.utils.escape_html(company.name)}</option>`);
	});
});

// ──────────────────────────────────────────────────────────
// Cascading filters
// ──────────────────────────────────────────────────────────
function handleCompanyChange(selectedCompany) {
	const $department = $('#filter-department');
	const $office = $('#filter-office');
	const $section = $('#filter-section');

	resetSelect($department, 'جارٍ التحميل...');
	resetSelect($office, 'اختر دائرة');
	resetSelect($section, 'اختر شعبة');

	if (!selectedCompany) {
		resetSelect($department, 'اختر مديرية');
		refreshTree();
		return;
	}

	frappe.db.get_list('Department', {
		fields: ['name'],
		filters: { 'company': selectedCompany },
		limit: 999,
		order_by: 'name asc'
	}).then(departments => {
		resetSelect($department, 'اختر مديرية');
		departments.forEach(dept => {
			$department.append(`<option value="${frappe.utils.escape_html(dept.name)}">${frappe.utils.escape_html(dept.name)}</option>`);
		});
		$department.prop('disabled', false);
		refreshTree();
	});
}

function handleDepartmentChange(selectedDepartment) {
	const $office = $('#filter-office');
	const $section = $('#filter-section');

	resetSelect($office, 'جارٍ التحميل...');
	resetSelect($section, 'اختر شعبة');

	if (!selectedDepartment) {
		resetSelect($office, 'اختر دائرة');
		refreshTree();
		return;
	}

	frappe.db.get_list('Office', {
		fields: ['name'],
		filters: { 'department': selectedDepartment },
		limit: 999,
		order_by: 'name asc'
	}).then(offices => {
		resetSelect($office, 'اختر دائرة');
		offices.forEach(office => {
			$office.append(`<option value="${frappe.utils.escape_html(office.name)}">${frappe.utils.escape_html(office.name)}</option>`);
		});
		$office.prop('disabled', false);
		refreshTree();
	});
}

function handleOfficeChange(selectedOffice) {
	const $section = $('#filter-section');

	resetSelect($section, 'جارٍ التحميل...');

	if (!selectedOffice) {
		resetSelect($section, 'اختر شعبة');
		refreshTree();
		return;
	}

	frappe.db.get_list('section', {
		fields: ['name'],
		filters: { 'office': selectedOffice },
		limit: 999,
		order_by: 'name asc'
	}).then(sections => {
		resetSelect($section, 'اختر شعبة');
		sections.forEach(section => {
			$section.append(`<option value="${frappe.utils.escape_html(section.name)}">${frappe.utils.escape_html(section.name)}</option>`);
		});
		$section.prop('disabled', false);
		refreshTree();
	});
}

// ──────────────────────────────────────────────────────────
// Filter event bindings (delegated so they survive re-renders)
// ──────────────────────────────────────────────────────────
$(document).on('change', '#filter-company', function () {
	handleCompanyChange($(this).val());
});

$(document).on('change', '#filter-department', function () {
	handleDepartmentChange($(this).val());
});

$(document).on('change', '#filter-office', function () {
	handleOfficeChange($(this).val());
});

$(document).on('change', '#filter-section', function () {
	refreshTree();
});
