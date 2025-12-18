frappe.listview_settings['Campaign Recipient'] = {
    add_fields: ["action_type", "email", "campaign"],
    get_indicator: function(doc) {
        const indicator_map = {
            "Opened": ["green", "Opened"],
            "Clicked": ["blue", "Clicked"],
            "Bounced": ["orange", "Bounced"],
            "Unsubscribed": ["red", "Unsubscribed"],
            "Complaint": ["red", "Complaint"]
        };
        
        return indicator_map[doc.action_type] || ["gray", doc.action_type];
    }
};