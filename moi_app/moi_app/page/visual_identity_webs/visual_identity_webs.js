frappe.pages['visual-identity-webs'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Visual Identity Website Statistics',
		single_column: true
	});

        $(`
        <iframe
            src="https://moi.gov.sy/data-access/vi"
            style="width: 100%; height: 85vh; border: none;"
        ></iframe>
        `).appendTo(page.body);
}
