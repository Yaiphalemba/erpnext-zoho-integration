import frappe
import requests
from frappe import _
from erpnext_zoho_integration.erpnext_zoho_integration.api.oauth import refresh_access_token
from datetime import datetime, timedelta

from frappe.utils import get_datetime, now_datetime

def get_valid_token():
    """Get valid access token, refresh if expired"""
    settings = frappe.get_single("Zoho Settings")

    if not settings.is_active:
        frappe.throw(_("Zoho integration is not active"))

    token_expiry = get_datetime(settings.token_expiry)

    # Refresh if expired or about to expire (5 min buffer)
    if token_expiry and now_datetime() >= (token_expiry - timedelta(minutes=5)):
        return refresh_access_token()

    return settings.get_password("access_token")


def make_api_call(endpoint, method="GET", params=None, data=None):
    """Generic API call handler with automatic token refresh"""
    token = get_valid_token()
    
    headers = {
        "Authorization": f"Zoho-oauthtoken {token}"
    }
    
    url = f"https://campaigns.zoho.in/api/v1.1/{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            response = requests.post(url, headers=headers, params=params, json=data)
        
        response.raise_for_status()
        result = response.json()
        
        # Check Zoho's response status
        if result.get("status") != "success":
            msg = result.get("message", "").lower()
            if "no contacts" in msg:
                return result
            frappe.throw(_(f"Zoho API Error: {result.get('message')}"))
        
        return result
        
    except requests.exceptions.HTTPError as e:
        # If unauthorized, try refreshing token once
        if e.response.status_code == 401:
            token = refresh_access_token()
            headers["Authorization"] = f"Zoho-oauthtoken {token}"
            
            if method == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method == "POST":
                response = requests.post(url, headers=headers, params=params, json=data)
            
            response.raise_for_status()
            return response.json()
        else:
            raise


@frappe.whitelist()
def get_recent_campaigns(limit=20):
    """Fetch recent campaigns with proper response parsing"""
    try:
        params = {
            "resfmt": "JSON",
            "range": limit
        }
        data = make_api_call("recentcampaigns", params=params)
        
        # Parse the response
        campaigns = data.get("recent_campaigns", [])
        total_count = int(data.get("total_record_count", 0))
        
        return {
            "campaigns": campaigns,
            "total_count": total_count,
            "fetched_count": len(campaigns)
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Zoho Get Recent Campaigns Error"))
        frappe.throw(_("Failed to fetch campaigns: {0}").format(str(e)))


@frappe.whitelist()
def get_campaign_report(campaign_key):
    """Get comprehensive campaign report with all metrics"""
    try:
        params = {
            "resfmt": "JSON",
            "campaignkey": campaign_key
        }
        data = make_api_call("campaignreports", params=params)
        
        # Parse response sections
        report = {
            "campaign_details": data.get("campaign-details", [{}])[0],
            "campaign_reports": data.get("campaign-reports", [{}])[0],
            "campaign_reach": data.get("campaign-reach", [{}])[0],
            "campaign_by_location": data.get("campaign-by-loaction", {}),  # Note: Zoho typo "loaction"
        }
        
        return report
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Zoho Get Campaign Report Error"))
        frappe.throw(_("Failed to fetch campaign report: {0}").format(str(e)))


@frappe.whitelist()
def get_campaign_recipients(campaign_key, action="openedcontacts", fromindex=1, range_val=20):
    """
    Get campaign recipients data
    
    Actions: openedcontacts, clickedcontacts, bouncedcontacts, 
             unsubscribedcontacts, spamcontacts, unopenedcontacts
    """
    try:
        params = {
            "resfmt": "JSON",
            "campaignkey": campaign_key,
            "action": action,
            "fromindex": int(fromindex),
            "range": int(range_val)
        }
        
        data = make_api_call("getcampaignrecipientsdata", method="POST", params=params)
        
        # Parse recipients
        recipients = data.get("list_of_details", [])
        
        return {
            "recipients": recipients,
            "action": action,
            "total_fetched": len(recipients)
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Zoho Get Campaign Recipients Error"))
        frappe.throw(_("Failed to fetch campaign recipients: {0}").format(str(e)))


@frappe.whitelist()
def sync_campaign_data(campaign_key):
    """
    Complete sync of campaign data including reports and recipient actions
    Returns a comprehensive campaign data structure
    """
    try:
        # Get campaign report
        report = get_campaign_report(campaign_key)
        
        # Get all recipient actions
        opened = get_campaign_recipients(campaign_key, "openedcontacts")
        clicked = get_campaign_recipients(campaign_key, "clickedcontacts")
        hard_bounce = get_campaign_recipients(campaign_key, "senthardbounce")
        soft_bounce = get_campaign_recipients(campaign_key, "sentsoftbounce")
        unsubscribed = get_campaign_recipients(campaign_key, "optoutcontacts")
        
        for r in hard_bounce.get("recipients", []):
            r["bounce_type"] = "Hard"

        for r in soft_bounce.get("recipients", []):
            r["bounce_type"] = "Soft"

        bounced_recipients = (
            hard_bounce.get("recipients", []) +
            soft_bounce.get("recipients", [])
        )
        
        return {
            "report": report,
            "opened_contacts": opened["recipients"],
            "clicked_contacts": clicked["recipients"],
            "bounced_contacts": bounced_recipients,
            "unsubscribed_contacts": unsubscribed["recipients"]
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Zoho Sync Campaign Data Error"))
        frappe.throw(_("Failed to sync campaign data: {0}").format(str(e)))