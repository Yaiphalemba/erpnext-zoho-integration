# Copyright (c) 2025, Yanky and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data

def get_columns():
    return [
        {
            "fieldname": "campaign_name",
            "label": _("Campaign"),
            "fieldtype": "Link",
            "options": "Campaign",
            "width": 200
        },
        {
            "fieldname": "sent_time",
            "label": _("Sent Time"),
            "fieldtype": "Datetime",
            "width": 150
        },
        {
            "fieldname": "emails_sent",
            "label": _("Sent"),
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "opens",
            "label": _("Opens"),
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "open_rate",
            "label": _("Open %"),
            "fieldtype": "Percent",
            "width": 100
        },
        {
            "fieldname": "clicks",
            "label": _("Clicks"),
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "click_rate",
            "label": _("Click %"),
            "fieldtype": "Percent",
            "width": 100
        },
        {
            "fieldname": "bounces",
            "label": _("Bounces"),
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "unsubscribes",
            "label": _("Unsubs"),
            "fieldtype": "Int",
            "width": 100
        }
    ]

def get_data(filters):
    campaigns = frappe.get_all(
        "Campaign",
        filters={"zoho_campaign_id": ["is", "set"]},
        fields=["name", "campaign_name", "zoho_sent_time"]
    )
    
    data = []
    
    for campaign in campaigns:
        analytics = frappe.get_all(
            "Campaign Analytics",
            filters={"parent": campaign.name},
            fields=["metric", "value", "percentage"]
        )
        
        row = {
            "campaign_name": campaign.name,
            "sent_time": campaign.zoho_sent_time
        }
        
        for metric in analytics:
            if "Emails Sent" in metric.metric:
                row["emails_sent"] = int(metric.value or 0)
            elif metric.metric == "Opens":
                row["opens"] = int(metric.value or 0)
            elif metric.metric == "Open Rate %":
                row["open_rate"] = float(metric.percentage or 0)
            elif metric.metric == "Unique Clicks":
                row["clicks"] = int(metric.value or 0)
            elif metric.metric == "Click Rate %":
                row["click_rate"] = float(metric.percentage or 0)
            elif metric.metric == "Bounces":
                row["bounces"] = int(metric.value or 0)
            elif metric.metric == "Unsubscribes":
                row["unsubscribes"] = int(metric.value or 0)
        
        data.append(row)
    
    return data