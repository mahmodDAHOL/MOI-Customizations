frappe.pages['weekly_report'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'التقرير الأسبوعي',
        single_column: true
    });

    const webFormOptions = [
        { label: 'الإعلام الحكومي', route: 'government-media' },
        { label: 'الأرشيف العام', route: 'general-archive' },
        { label: 'الخدمات المشتركة', route: 'shared-service' },
        { label: 'الدراما', route: 'drama' },
        { label: 'الرصد', route: 'c-monitoring' },
        { label: 'الشؤون الصحفية', route: 'press-relation' },
        { label: 'العلاقات العامة', route: 'public_relation' },
        { label: 'القانونية', route: 'legal' },
        { label: 'المعلوماتية', route: 'it' },
        { label: 'مؤسسة الوحدة', route: 'wahda' },
        { label: 'سانا', route: 'sana' },
        { label: 'إعلام المحافظات', route: 'provices' },
        { label: 'الإعلان', route: 'advertisment' },
    ];

    // Build options: first option is empty (acts as placeholder)
    const optionsString = [
        '',
        ...webFormOptions.map(item => item.label)
    ].join('\n');

    // Create centered container BEFORE the field
    const selectContainer = $(`
        <div class="weekly-report-select-wrapper" style="display: flex; justify-content: center; margin: 32px 0;">
            <div style="width: 20%; min-width: 220px; max-width: 320px;">
                <!-- Select field will be inserted here -->
            </div>
        </div>
    `);
    $(page.main).append(selectContainer);

    // Create the select field
    let selectField = frappe.ui.form.make_control({
        df: {
            fieldtype: 'Select',
            label: 'اختر المؤسسة / القسم',
            options: optionsString,
            change: function() {
                const selectedLabel = this.value?.trim();
                const $iframeContainer = $('#web_form_iframe_container');
                const iframe = document.getElementById('web_form_iframe');

                if (selectedLabel) {
                    const selectedOption = webFormOptions.find(item => item.label === selectedLabel);
                    if (selectedOption) {
                        // Show loading
                        $iframeContainer.addClass('loading').show();
                        iframe.onload = () => {
                            $iframeContainer.removeClass('loading');
                            const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                            const button = iframeDoc.getElementById('nextcloud-talk-button');
                            if (button) button.style.display = 'none';
                        };
                        iframe.src = `/${encodeURIComponent(selectedOption.route)}`;
                    }
                } else {
                    $iframeContainer.hide();
                    iframe.src = 'about:blank';
                }
            }
        },
        parent: selectContainer.find('div'),
        render_input: true
    });

    // Style enhancements
    setTimeout(() => {
        const $input = selectField.$input;
        const $label = selectField.$wrapper.find('.control-label');

        // Label styling
        $label.css({
            'font-weight': '600',
            'margin-bottom': '8px',
            'font-size': '15px',
            'color': '#333',
            'text-align': 'right' // RTL alignment
        });

        // Input styling (override Frappe defaults)
        $input.addClass('form-control')
            .css({
                'width': '100% !important',
                'font-size': '15px',
                'border': '1px solid #d1d8dd',
                'border-radius': '6px',
                'background-color': '#fff',
                'box-shadow': '0 1px 2px rgba(0,0,0,0.05)',
                'direction': 'rtl',
                'text-align': 'center'
            })
            .on('focus', function() {
                $(this).css({
                    'border-color': '#007bff',
                    'box-shadow': '0 0 0 2px rgba(0,123,255,0.2)'
                });
            })
            .on('blur', function() {
                $(this).css({
                    'border-color': '#d1d8dd',
                    'box-shadow': '0 1px 2px rgba(0,0,0,0.05)'
                });
            });
    }, 100);

    // Add iframe container (centered, full-width below)
    $(page.main).append(`
        <div id="web_form_iframe_container" class="mt-5" style="display: none; margin: 0 auto; width: 90%; max-width: 1200px;">
            <div class="loading-indicator" style="display: none; text-align: center; padding: 24px; color: #666;">
                <i class="fa fa-spinner fa-spin fa-2x"></i>
                <p class="mt-2" style="font-size: 16px;">جارٍ تحميل النموذج...</p>
            </div>
            <iframe
                id="web_form_iframe"
                src="about:blank"
                style="width: 100%; height: 80vh; border: 1px solid #e0e6eb; border-radius: 8px; display: block;"
                frameborder="0">
            </iframe>
        </div>
    `);

    // Optional: Add global styles if needed
    frappe.dom.set_style(`
        #web_form_iframe_container.loading .loading-indicator {
            display: block !important;
        }
        #web_form_iframe_container.loading iframe {
            opacity: 0.6;
        }
        .mt-5 {
            margin-top: 2rem !important;
        }
        `);
};