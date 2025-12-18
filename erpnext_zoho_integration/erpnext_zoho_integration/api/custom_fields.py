import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    """Add custom fields to Campaign and Contact doctypes"""
    
    custom_fields = {
        "Campaign": [
            {
                "fieldname": "zoho_section",
                "label": "Zoho Campaign Data",
                "fieldtype": "Section Break",
                "insert_after": "description",
                "collapsible": 1,
                "module": "ERPNext Zoho Integration"
            },
            {
                "fieldname": "zoho_campaign_id",
                "label": "Zoho Campaign ID",
                "fieldtype": "Data",
                "insert_after": "zoho_section",
                "read_only": 1,
                "unique": 1,
                "module": "ERPNext Zoho Integration"
            },
            {
                "fieldname": "zoho_campaign_key",
                "label": "Zoho Campaign Key",
                "fieldtype": "Data",
                "insert_after": "zoho_campaign_id",
                "read_only": 1,
                "module": "ERPNext Zoho Integration"
            },
            {
                "fieldname": "zoho_subject",
                "label": "Email Subject",
                "fieldtype": "Data",
                "insert_after": "zoho_campaign_key",
                "read_only": 1,
                "module": "ERPNext Zoho Integration"
            },
            {
                "fieldname": "zoho_from_email",
                "label": "From Email",
                "fieldtype": "Data",
                "insert_after": "zoho_subject",
                "read_only": 1,
                "options": "Email",
                "module": "ERPNext Zoho Integration"
            },
            {
                "fieldname": "zoho_column_break",
                "fieldtype": "Column Break",
                "insert_after": "zoho_from_email",
                "module": "ERPNext Zoho Integration"
            },
            {
                "fieldname": "zoho_sent_time",
                "label": "Sent Time",
                "fieldtype": "Datetime",
                "insert_after": "zoho_column_break",
                "read_only": 1,
                "module": "ERPNext Zoho Integration"
            },
            {
                "fieldname": "zoho_campaign_status",
                "label": "Zoho Status",
                "fieldtype": "Data",
                "insert_after": "zoho_sent_time",
                "read_only": 1,
                "module": "ERPNext Zoho Integration"
            },
            {
                "fieldname": "zoho_campaign_type",
                "label": "Campaign Type",
                "fieldtype": "Data",
                "insert_after": "zoho_campaign_status",
                "read_only": 1,
                "module": "ERPNext Zoho Integration"
            },
            {
                "fieldname": "zoho_reply_to",
                "label": "Reply To",
                "fieldtype": "Data",
                "insert_after": "zoho_campaign_type",
                "read_only": 1,
                "options": "Email",
                "module": "ERPNext Zoho Integration"
            },
            {
                "fieldname": "zoho_preview_url",
                "label": "Preview URL",
                "fieldtype": "Data",
                "insert_after": "zoho_reply_to",
                "read_only": 1,
                "options": "URL",
                "module": "ERPNext Zoho Integration"
            },
            {
                "fieldname": "analytics_section",
                "label": "Campaign Analytics",
                "fieldtype": "Section Break",
                "insert_after": "zoho_preview_url",
                "collapsible": 1,
                "module": "ERPNext Zoho Integration"
            },
            {
                "fieldname": "campaign_analytics",
                "label": "Analytics",
                "fieldtype": "Table",
                "insert_after": "analytics_section",
                "options": "Campaign Analytics",
                "module": "ERPNext Zoho Integration"
            },
            {
                "fieldname": "last_synced",
                "label": "Last Synced",
                "fieldtype": "Datetime",
                "insert_after": "campaign_analytics",
                "read_only": 1,
                "module": "ERPNext Zoho Integration"
            }
        ],
        "Contact": [
            {
                "fieldname": "zoho_contact_section",
                "label": "Zoho Data",
                "fieldtype": "Section Break",
                "insert_after": "unsubscribed",
                "collapsible": 1,
                "module": "ERPNext Zoho Integration"
            },
            {
                "fieldname": "zoho_contact_id",
                "label": "Zoho Contact ID",
                "fieldtype": "Data",
                "insert_after": "zoho_contact_section",
                "read_only": 1,
                "unique": 1,
                "module": "ERPNext Zoho Integration"
            },
            {
                "fieldname": "zoho_status",
                "label": "Zoho Status",
                "fieldtype": "Data",
                "insert_after": "zoho_contact_id",
                "read_only": 1,
                "module": "ERPNext Zoho Integration"
            },
            {
                "fieldname": "zoho_column_break",
                "fieldtype": "Column Break",
                "insert_after": "zoho_status",
                "module": "ERPNext Zoho Integration"
            },
            {
                "fieldname": "zoho_last_synced",
                "label": "Last Synced from Zoho",
                "fieldtype": "Datetime",
                "insert_after": "zoho_column_break",
                "read_only": 1,
                "module": "ERPNext Zoho Integration"
            }
        ]
    }
    
    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()