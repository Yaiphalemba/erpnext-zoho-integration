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
        });

        setTimeout(() => {
            render_campaign_dashboard(frm);
        }, 500);
    },
    
    onload: function(frm) {
        if (frm.doc.zoho_campaign_key) {
            setTimeout(() => {
                render_campaign_dashboard(frm);
            }, 1000);
        }
    }
});

function render_campaign_dashboard(frm) {
    if (!frm.doc.campaign_analytics || !Array.isArray(frm.doc.campaign_analytics) || frm.doc.campaign_analytics.length === 0) {
        return;
    }

    const analytics_field = frm.fields_dict.campaign_analytics;
    if (!analytics_field || !analytics_field.$wrapper) return;

    // Remove old dashboard if exists
    $(frm.wrapper).find('.zoho-campaign-dashboard').remove();

    // CSS for perfect centering and alignment
    const gridCSS = `
        .zoho-campaign-dashboard {
            margin: 25px 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .zoho-dashboard-section {
            margin-bottom: 30px;
            width: 100%;
        }
        .zoho-dashboard-section h4 {
            margin: 0 0 20px 0;
            color: #36414C;
            font-weight: 600;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            text-align: left;
        }
        .zoho-metrics-container {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 15px;
            width: 100%;
        }
        .zoho-metric-card {
            background: #fff;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-height: 120px;
            transition: all 0.2s ease;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            position: relative;
            overflow: hidden;
            width: 200px;
            flex: 0 0 auto;
        }
        .zoho-metric-card.clickable {
            cursor: pointer;
        }
        .zoho-metric-card.clickable:hover {
            transform: translateY(-2px);
            border-color: #b4c6fe;
            box-shadow: 0 4px 12px rgba(94, 100, 255, 0.15);
        }
        .zoho-metric-card .metric-label {
            font-size: 12px;
            color: #6B7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 10px;
            font-weight: 500;
            line-height: 1.2;
            max-width: 100%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .zoho-metric-card .metric-value {
            font-size: 28px;
            font-weight: 700;
            line-height: 1;
            margin-bottom: 4px;
        }
        .zoho-metric-card .metric-percentage {
            font-size: 12px;
            color: #9CA3AF;
            margin-top: 2px;
        }
        .zoho-metric-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: currentColor;
            opacity: 0.2;
        }
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
            .zoho-metric-card {
                width: calc(50% - 8px);
                min-width: 160px;
            }
        }
        @media (max-width: 480px) {
            .zoho-metric-card {
                width: 100%;
                max-width: 280px;
            }
        }
    `;

    // Add CSS to head
    if (!$('#zoho-dashboard-styles').length) {
        $('<style id="zoho-dashboard-styles">').text(gridCSS).appendTo('head');
    }

    // Group metrics
    const metricMapping = {
        'Opened': ['total opens', 'unique opens', 'opens', 'opened', 'total opened'],
        'Clicked': ['total clicks', 'unique clicks', 'clicks', 'clicked', 'total clicked'],
        'Bounced': ['bounces', 'total bounces', 'bounced', 'hard bounces', 'soft bounces'],
        'Unsubscribed': ['unsubscribes', 'total unsubscribes', 'unsubscribed'],
        'Complaint': ['spam complaints', 'complaints', 'spam', 'complaint'],
        'info': ['emails sent', 'sent', 'total sent', 'delivered', 'total delivered', 
                 'click through rate', 'ctr', 'open rate', 'unique open rate']
    };

    const engagementMetrics = [];
    const infoMetrics = [];
    
    frm.doc.campaign_analytics.forEach(metric => {
        if (!metric.metric || !metric.value) return;
        
        let action = null;
        const metricLower = metric.metric.toLowerCase();
        
        for (const [actionType, keywords] of Object.entries(metricMapping)) {
            if (actionType === 'info') continue;
            if (keywords.some(keyword => metricLower.includes(keyword))) {
                action = actionType;
                break;
            }
        }
        
        if (action) {
            engagementMetrics.push({...metric, action});
        } else if (metricMapping.info.some(keyword => metricLower.includes(keyword))) {
            infoMetrics.push({...metric, action: 'info'});
        }
    });

    // Build HTML
    let html = `<div class="zoho-campaign-dashboard">`;
    
    // Engagement metrics section
    if (engagementMetrics.length > 0) {
        html += `<div class="zoho-dashboard-section">
                    <h4>Engagement Metrics</h4>
                    <div class="zoho-metrics-container">`;
        
        const colors = ['#5e64ff', '#5856d6', '#ff9500', '#ff3b30', '#ff2d55', '#34c759'];
        
        engagementMetrics.slice(0, 6).forEach((metric, index) => {
            const color = colors[index % colors.length];
            html += `
                <div class="zoho-metric-card clickable" 
                     data-action="${metric.action}"
                     style="color: ${color}">
                    <div class="metric-label" title="${metric.metric}">
                        ${metric.metric}
                    </div>
                    <div class="metric-value">${metric.value}</div>
                    ${metric.percentage > 0 ? `<div class="metric-percentage">${metric.percentage}%</div>` : ''}
                </div>`;
        });
        
        html += `</div></div>`;
    }
    
    // Info metrics section
    if (infoMetrics.length > 0) {
        html += `<div class="zoho-dashboard-section">
                    <h4>Campaign Stats</h4>
                    <div class="zoho-metrics-container">`;
        
        const colors = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#ec4899'];
        
        infoMetrics.slice(0, 6).forEach((metric, index) => {
            const color = colors[index % colors.length];
            html += `
                <div class="zoho-metric-card" style="color: ${color}">
                    <div class="metric-label" title="${metric.metric}">
                        ${metric.metric}
                    </div>
                    <div class="metric-value">${metric.value}</div>
                    ${metric.percentage > 0 ? `<div class="metric-percentage">${metric.percentage}%</div>` : ''}
                </div>`;
        });
        
        html += `</div></div>`;
    }
    
    // Fallback
    if (engagementMetrics.length === 0 && infoMetrics.length === 0) {
        html += `<div class="zoho-dashboard-section">
                    <h4>Campaign Analytics</h4>
                    <div class="zoho-metrics-container">`;
        
        const colors = ['#5e64ff', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];
        
        frm.doc.campaign_analytics.slice(0, 6).forEach((metric, index) => {
            const color = colors[index % colors.length];
            html += `
                <div class="zoho-metric-card" style="color: ${color}">
                    <div class="metric-label" title="${metric.metric}">
                        ${metric.metric}
                    </div>
                    <div class="metric-value">${metric.value}</div>
                    ${metric.percentage > 0 ? `<div class="metric-percentage">${metric.percentage}%</div>` : ''}
                </div>`;
        });
        
        html += `</div></div>`;
    }
    
    html += `</div>`;

    // Insert before analytics table
    const analyticsSection = analytics_field.$wrapper.closest('.form-section');
    if (!analyticsSection.length) return;
    
    $(html).insertBefore(analytics_field.$wrapper);

    // Add click handlers
    analyticsSection.find('.zoho-metric-card.clickable').off('click').on('click', function () {
        show_recipients_list(frm.doc.name, $(this).data('action'));
    });
}

function show_recipients_list(campaign, action_type) {
    frappe.route_options = {
        "campaign": campaign,
        "action_type": action_type
    };
    frappe.set_route("List", "Campaign Recipient");
}