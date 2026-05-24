frappe.pages["momc-web-panel"].on_page_load = function (wrapper) {
    var token = frappe.boot.cms_admin_token;
    var baseUrl = "https://momc.gov.sy/momc-dashboard-emedia-marketing-gov-admin-panel/";

    var $frame = $('<iframe>', {
        style: [
            "position:fixed",
            "top:60px",
            "left:0",
            "right:0",
            "bottom:0",
            "width:100%",
            "height:calc(100vh - 60px)",
            "border:none",
            "z-index:1"
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
    $(wrapper).append($frame);
};

