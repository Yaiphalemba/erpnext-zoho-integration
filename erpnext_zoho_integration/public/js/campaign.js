frappe.ui.form.on('Campaign', {
    refresh(frm) {
        if (!frm.doc.zoho_campaign_key) return;

        frm.add_custom_button(__('Sync from Zoho'), function () {
            frappe.call({
                method: 'erpnext_zoho_integration.erpnext_zoho_integration.api.sync.sync_campaign_by_name',
                args: { campaign_name: frm.doc.name },
                freeze: true,
                freeze_message: __('Syncing campaign data...'),
                callback(r) {
                    if (r.message?.success) {
                        frappe.show_alert({
                            message: __('Campaign synced successfully'),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    }
                }
            });
        }, __('Actions'));

        // Delay dashboard render
        setTimeout(() => {
            render_campaign_dashboard(frm);
        }, 300);
    }
});

function render_campaign_dashboard(frm) {
    if (!frm.doc.campaign_analytics?.length) return;

    const analytics_field = frm.fields_dict.campaign_analytics;
    if (!analytics_field || !analytics_field.$wrapper) return;

    // Remove old dashboard
    analytics_field.$wrapper
        .closest('.form-section')
        .find('.zoho-campaign-dashboard')
        .remove();

    const key_metrics = [
        { label: 'Opens', action: 'Opened', color: '#5e64ff' },
        { label: 'Unique Clicks', action: 'Clicked', color: '#5856d6' },
        { label: 'Bounces', action: 'Bounced', color: '#ff9500' },
        { label: 'Unsubscribes', action: 'Unsubscribed', color: '#ff3b30' },
        { label: 'Spam Complaints', action: 'Complaint', color: '#ff2d55' }
    ];

    let html = `<div class="zoho-campaign-dashboard" style="margin:20px 0">
                    <div class="row">`;

    key_metrics.forEach(cfg => {
        const metric = frm.doc.campaign_analytics.find(m =>
            m.metric?.includes(cfg.label)
        );

        if (!metric) return;

        html += `
            <div class="col-sm-4 col-md-2">
                <div class="metric-card"
                     data-action="${cfg.action}"
                     style="
                        cursor:pointer;
                        padding:20px;
                        background:#fff;
                        border:1px solid #d1d8dd;
                        border-radius:8px;
                        text-align:center;
                        transition:.3s;
                        box-shadow:0 1px 3px rgba(0,0,0,.05)">
                    <div style="font-size:12px;color:#8d99a6;text-transform:uppercase">
                        ${cfg.label}
                    </div>
                    <div style="font-size:28px;font-weight:600;color:${cfg.color}">
                        ${metric.value}
                    </div>
                    ${metric.percentage ? `<div style="color:#8d99a6">${metric.percentage}%</div>` : ``}
                </div>
            </div>`;
    });

    html += `</div></div>`;

    // Insert BEFORE analytics table
    $(html).insertBefore(analytics_field.$wrapper);

    // Click handler
    $('.metric-card').on('click', function () {
        show_recipients_list(frm.doc.name, $(this).data('action'));
    });

    // Add hover effects
    $('.metric-card').hover(
        function() {
            $(this).css({
                'transform': 'translateY(-2px)',
                'box-shadow': '0 4px 12px rgba(0,0,0,0.15)',
                'border-color': '#a8b1bd'
            });
        },
        function() {
            $(this).css({
                'transform': 'translateY(0)',
                'box-shadow': '0 1px 3px rgba(0,0,0,0.05)',
                'border-color': '#d1d8dd'
            });
        }
    );
}

function show_recipients_list(campaign, action_type) {
    frappe.route_options = {
        "campaign": campaign,
        "action_type": action_type
        };
    frappe.set_route("List", "Campaign Recipient");
}