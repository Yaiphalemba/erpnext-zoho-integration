// Copyright (c) 2025, Yanky and contributors
// For license information, please see license.txt

frappe.ui.form.on('Zoho Settings', {
    refresh: function(frm) {
        // Authorization button
        if (!frm.doc.is_active) {
            frm.add_custom_button(__('Authorize with Zoho'), () => {
                window.location.href =
                    "/api/method/erpnext_zoho_integration.erpnext_zoho_integration.api.oauth.authorize";
            }).addClass('btn-primary');
        }

        if (!frm.doc.is_active && frm.doc.code) {
            frm.add_custom_button(__('Fetch Tokens'), function() {
                frappe.call({
                    method: 'erpnext_zoho_integration.erpnext_zoho_integration.api.oauth.fetch_tokens',
                    args: { code: frm.doc.code },
                    callback: function(r) {
                        if (r.message) {
                            frappe.msgprint(__('Tokens fetched successfully'), 'Success');
                            frm.reload_doc();
                        }
                    }
                });
            });
        }

        // Test Connection button
        if (frm.doc.is_active) {
            frm.add_custom_button(__('Test Connection'), function() {
                frappe.call({
                    method: 'erpnext_zoho_integration.erpnext_zoho_integration.api.campaigns.get_recent_campaigns',
                    args: { limit: 5 },
                    callback: function(r) {
                        if (r.message) {
                            frappe.msgprint({
                                title: __('Connection Successful'),
                                message: __('Found {0} campaigns. Total campaigns: {1}', 
                                    [r.message.fetched_count, r.message.total_count]),
                                indicator: 'green'
                            });
                        }
                    }
                });
            });
            
            // View Campaigns button
            frm.add_custom_button(__('View Campaigns'), function() {
                frappe.call({
                    method: 'erpnext_zoho_integration.erpnext_zoho_integration.api.campaigns.get_recent_campaigns',
                    args: { limit: 20 },
                    callback: function(r) {
                        if (r.message && r.message.campaigns) {
                            show_campaigns_dialog(r.message.campaigns);
                        }
                    }
                });
            });
            
            // Refresh Token button
            frm.add_custom_button(__('Refresh Token'), function() {
                frappe.call({
                    method: 'erpnext_zoho_integration.erpnext_zoho_integration.api.oauth.refresh_access_token',
                    callback: function(r) {
                        if (r.message) {
                            frappe.msgprint(__('Token refreshed successfully'), 'Success');
                            frm.reload_doc();
                        }
                    }
                });
            });
            
            // Sync All Campaigns button
            if (frm.doc.is_active) {
                frm.add_custom_button(__('Sync All Campaigns'), function() {
                    frappe.call({
                        method: 'erpnext_zoho_integration.erpnext_zoho_integration.api.sync.sync_all_campaigns',
                        freeze: true,
                        freeze_message: __('Syncing campaigns from Zoho...'),
                        callback: function(r) {
                            if (r.message) {
                                let msg = __('Synced {0} out of {1} campaigns successfully', 
                                    [r.message.synced_count, r.message.total_campaigns]);
                                
                                if (r.message.errors && r.message.errors.length > 0) {
                                    msg += '<br><br><b>Errors:</b><br>';
                                    r.message.errors.forEach(err => {
                                        msg += `${err.campaign}: ${err.error}<br>`;
                                    });
                                }
                                
                                frappe.msgprint({
                                    title: __('Sync Complete'),
                                    message: msg,
                                    indicator: r.message.errors.length > 0 ? 'orange' : 'green'
                                });
                            }
                        }
                    });
                });
            }
        }
    }
});

function show_campaigns_dialog(campaigns) {
    let d = new frappe.ui.Dialog({
        title: __('Recent Campaigns'),
        fields: [
            {
                fieldname: 'campaigns_html',
                fieldtype: 'HTML'
            }
        ],
        size: 'extra-large'
    });
    
    let html = '<table class="table table-bordered">';
    html += '<thead><tr><th>Campaign Name</th><th>Subject</th><th>Sent Date</th><th>Status</th><th>Actions</th></tr></thead><tbody>';
    
    campaigns.forEach(campaign => {
        const is_draft = campaign.campaign_status === 'Draft';

        html += `<tr>
            <td>${campaign.campaign_name}</td>
            <td>${campaign.subject}</td>
            <td>${campaign.sent_date_string || 'Not Sent'}</td>
            <td>
                <span class="indicator ${
                    campaign.campaign_status === 'Sent' ? 'green' : 'orange'
                }">
                    ${campaign.campaign_status}
                </span>
            </td>
            <td>
                ${
                    !is_draft
                        ? `<button class="btn btn-xs btn-default"
                            onclick="view_campaign_report('${campaign.campaign_key}')">
                            View Report
                        </button>`
                        : ''
                }
            </td>
        </tr>`;
    });
    
    html += '</tbody></table>';
    d.fields_dict.campaigns_html.$wrapper.html(html);
    d.show();
}

window.view_campaign_report = function(campaign_key) {
    frappe.call({
        method: 'erpnext_zoho_integration.erpnext_zoho_integration.api.campaigns.get_campaign_report',
        args: { campaign_key: campaign_key },
        callback: function(r) {
            if (r.message) {
                show_campaign_report_dialog(r.message);
            }
        }
    });
}

function show_campaign_report_dialog(report) {
    let stats = report.campaign_reports;
    
    let d = new frappe.ui.Dialog({
        title: __('Campaign Report: {0}', [report.campaign_details.campaign_name]),
        fields: [
            {
                fieldname: 'report_html',
                fieldtype: 'HTML'
            }
        ],
        size: 'large'
    });
    
    let html = `
        <div class="row">
            <div class="col-sm-3">
                <div class="stat-box">
                    <h4>${stats.emails_sent_count}</h4>
                    <p>Emails Sent</p>
                </div>
            </div>
            <div class="col-sm-3">
                <div class="stat-box">
                    <h4>${stats.delivered_count} (${stats.delivered_percent}%)</h4>
                    <p>Delivered</p>
                </div>
            </div>
            <div class="col-sm-3">
                <div class="stat-box">
                    <h4>${stats.opens_count} (${stats.open_percent}%)</h4>
                    <p>Opens</p>
                </div>
            </div>
            <div class="col-sm-3">
                <div class="stat-box">
                    <h4>${stats.unique_clicks_count} (${stats.unique_clicked_percent}%)</h4>
                    <p>Clicks</p>
                </div>
            </div>
        </div>
        <div class="row" style="margin-top: 20px;">
            <div class="col-sm-3">
                <div class="stat-box">
                    <h4>${stats.bounces_count} (${stats.bounce_percent}%)</h4>
                    <p>Bounces</p>
                </div>
            </div>
            <div class="col-sm-3">
                <div class="stat-box">
                    <h4>${stats.unsub_count} (${stats.unsubscribe_percent}%)</h4>
                    <p>Unsubscribes</p>
                </div>
            </div>
            <div class="col-sm-3">
                <div class="stat-box">
                    <h4>${stats.complaints_count} (${stats.complaints_percent}%)</h4>
                    <p>Complaints</p>
                </div>
            </div>
            <div class="col-sm-3">
                <div class="stat-box">
                    <h4>${stats.clicksperopenrate}%</h4>
                    <p>Click-to-Open Rate</p>
                </div>
            </div>
        </div>
        <style>
            .stat-box { text-align: center; padding: 15px; background: #f5f5f5; border-radius: 5px; }
            .stat-box h4 { margin: 0; color: #2490ef; font-size: 24px; }
            .stat-box p { margin: 5px 0 0; color: #6c757d; }
        </style>
    `;
    
    d.fields_dict.report_html.$wrapper.html(html);
    d.show();
}