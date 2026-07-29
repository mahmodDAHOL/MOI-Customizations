frappe.pages['momc_website_statistics'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'MoMC Website Statistics',
        single_column: true
    });
    $(page.body).html(
	'<iframe src="https://analytics.momc.gov.sy/d/momc.gov.sy/" width="100%" height="900" style="border:0" loading="lazy" referrerpolicy="no-referrer" sandbox="allow-scripts allow-same-origin" title="momc.gov.sy analytics"></iframe>'
    );
};
