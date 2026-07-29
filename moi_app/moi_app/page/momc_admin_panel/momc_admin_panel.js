frappe.pages['momc_admin_panel'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'MoMC Admin Panel',
        single_column: true
    });

    // var token = frappe.boot.cms_admin_token;
    var token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoid2ViLWFkbWluIiwic3ViIjoiIiwiYXVkIjoibW9pIiwicm9sZXMiOlsiYWRtaW4iXSwiaWF0IjoxNzgwODEzMzc4LCJleHAiOjE3ODA5MDMzNzh9.wXrdoM2tk2DvWN8jcrKeV0VS-o2kYvnlaBk2TDdkOxs";
    var baseUrl = "https://momc.gov.sy/momc-dashboard-emedia-marketing-gov-admin-panel/";

    var $frame = $('<iframe>', {
        style: [
            "width:100%",
            "height:calc(100vh - 130px)",
            "border:none"
        ].join(";"),
        referrerpolicy: "no-referrer"
    });

    if (!token) {
        $(wrapper).html(
            '<p style="color:red;padding:2rem;">CMS token not configured.<br>' +
            'Run: <code>bench set-config cms_admin_token "YOUR_TOKEN"</code></p>'
        );
        return;
    }

    $frame.attr("src", baseUrl + "?_token=" + encodeURIComponent(token));
    $(page.body).html($frame);
};
