import frappe
from frappe import _
from erpnext_zoho_integration.erpnext_zoho_integration.api.campaigns import (
    get_recent_campaigns,
    get_campaign_report,
    get_campaign_recipients
)
import json
from frappe.utils import get_datetime, now_datetime

@frappe.whitelist()
def sync_all_campaigns():
    """Sync all recent campaigns from Zoho"""
    try:
        # Get recent campaigns
        result = get_recent_campaigns(limit=50)
        campaigns = result.get("campaigns", [])
        
        synced_count = 0
        errors = []
        
        for campaign_data in campaigns:
            try:
                # Only sync sent campaigns
                if campaign_data.get("campaign_status") == "Sent":
                    sync_single_campaign(campaign_data)
                    synced_count += 1
            except Exception as e:
                errors.append({
                    "campaign": campaign_data.get("campaign_name"),
                    "error": str(e)
                })
                frappe.log_error(
                    frappe.get_traceback(),
                    f"Campaign Sync Error: {campaign_data.get('campaign_name')}"
                )
        
        frappe.db.commit()
        
        return {
            "success": True,
            "synced_count": synced_count,
            "total_campaigns": len(campaigns),
            "errors": errors
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Sync All Campaigns Error")
        frappe.throw(_("Failed to sync campaigns: {0}").format(str(e)))


def sync_single_campaign(campaign_data):
    """Sync a single campaign with all its data"""
    campaign_id = campaign_data.get("campaignId")
    campaign_key = campaign_data.get("campaign_key")
    campaign_name = campaign_data.get("campaign_name", "Unknown Campaign")
    
    if not campaign_key:
        return None
    
    # Check if campaign exists
    existing = frappe.db.get_value(
        "Campaign",
        {"zoho_campaign_id": campaign_id},
        "name"
    )
    
    if existing:
        campaign = frappe.get_doc("Campaign", existing)
    else:
        campaign = frappe.new_doc("Campaign")
        campaign.campaign_name = campaign_name
        campaign.naming_series = "SAL-CAM-.YYYY.-"
    
    # Map basic fields
    campaign.zoho_campaign_id = campaign_id
    campaign.zoho_campaign_key = campaign_key
    campaign.zoho_subject = campaign_data.get("subject")
    campaign.zoho_from_email = campaign_data.get("from_email")
    
    # Handle sent_time (milliseconds timestamp)
    sent_time = campaign_data.get("sent_time")
    if sent_time:
        try:
            campaign.zoho_sent_time = get_datetime(int(sent_time) / 1000)
        except (ValueError, TypeError):
            pass  # Skip if invalid timestamp
    
    campaign.zoho_campaign_status = campaign_data.get("campaign_status")
    campaign.zoho_campaign_type = campaign_data.get("campaigntype")
    campaign.zoho_reply_to = campaign_data.get("reply_to")
    
    # Fix the preview URL - add https:// if not present
    preview_url = campaign_data.get("campaign_preview")
    if preview_url and not preview_url.startswith(('http://', 'https://')):
        preview_url = f"https://{preview_url}"
    campaign.zoho_preview_url = preview_url
    
    campaign.last_synced = now_datetime()
    campaign.save(ignore_permissions=True)
    
    # Sync analytics and recipients
    sync_campaign_analytics(campaign, campaign_key)
    
    return campaign


def sync_campaign_analytics(campaign, campaign_key):
    """Sync campaign analytics and recipient data"""
    try:
        # Get campaign report
        report = get_campaign_report(campaign_key)
        campaign_reports = report.get("campaign_reports", {})
        
        if not campaign_reports:
            return
        
        # Clear existing analytics
        campaign.campaign_analytics = []
        
        # Metric mapping with Zoho API field names
        metric_mapping = {
            "emails_sent_count": "Emails Sent",
            "delivered_count": "Delivered",
            "delivered_percent": "Delivered %",
            "opens_count": "Opens",
            "open_percent": "Open Rate %",
            "unique_clicks_count": "Unique Clicks",
            "unique_clicked_percent": "Click Rate %",
            "bounces_count": "Bounces",
            "bounce_percent": "Bounce Rate %",
            "hardbounce_count": "Hard Bounces",
            "softbounce_count": "Soft Bounces",
            "unsub_count": "Unsubscribes",
            "unsubscribe_percent": "Unsubscribe Rate %",
            "complaints_count": "Spam Complaints",
            "complaints_percent": "Spam Rate %",
            "unopened": "Unopened",
            "unopened_percent": "Unopened %",
            "clicksperopenrate": "Click-to-Open Rate",
            "forwards_count": "Forwards"
        }
        
        for key, label in metric_mapping.items():
            value = campaign_reports.get(key)
            if value is not None:
                campaign.append("campaign_analytics", {
                    "metric": label,
                    "value": str(value),
                    "percentage": float(value) if "percent" in key or "rate" in key.lower() else None
                })
        
        campaign.save(ignore_permissions=True)
        
        # Sync recipient data for different actions
        sync_campaign_recipients_data(campaign, campaign_key)
        
    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            f"Campaign Analytics Sync Error: {campaign.name}"
        )
        raise


def sync_campaign_recipients_data(campaign, campaign_key):
    """Sync recipient actions (opens, clicks, bounces, etc.) with debug logging"""
    # Updated action mapping based on Zoho API documentation
    action_mapping = {
        "openedcontacts": "Opened",
        "clickedcontacts": "Clicked",
        "senthardbounce": "Hard Bounced",
        "sentsoftbounce": "Soft Bounced",
        "optoutcontacts": "Unsubscribed",
        "spamcontacts": "Complaint"
    }
    
    for action_key, action_type in action_mapping.items():
        try:
            frappe.logger().info(f"Fetching {action_type} recipients with key: {action_key}")
            result = get_campaign_recipients(campaign_key, action_key, range_val=100)
            
            if not result:
                frappe.logger().info(f"No result returned for {action_type} with key {action_key}")
                continue
            
            # Check different possible response structures
            if "list_of_details" in result:
                recipients = result.get("list_of_details", [])
                frappe.logger().info(f"Found {len(recipients)} {action_type} recipients in 'list_of_details'")
            elif "recipients" in result:
                recipients = result.get("recipients", [])
                frappe.logger().info(f"Found {len(recipients)} {action_type} recipients in 'recipients'")
            else:
                # Try to find any array in the result
                for key, value in result.items():
                    if isinstance(value, list) and key != "urlclicks":  # Skip urlclicks array
                        recipients = value
                        frappe.logger().info(f"Found {len(recipients)} {action_type} recipients in '{key}'")
                        break
                else:
                    recipients = []
                    frappe.logger().info(f"No recipient list found in response for {action_type}")
            
            if recipients:
                # Log first recipient to see structure
                frappe.logger().info(f"First {action_type} recipient: {json.dumps(recipients[0] if recipients else {})}")
            
            for recipient_data in recipients:
                sync_recipient(campaign, recipient_data, action_type)
                
            frappe.db.commit()
            
        except Exception as e:
            frappe.log_error(
                f"Error syncing {action_type} recipients with key {action_key}: {str(e)}",
                f"Recipient Sync Error: {campaign.name}"
            )
            frappe.logger().error(f"Full traceback for {action_type}: {frappe.get_traceback()}")


def sync_recipient(campaign, recipient_data, action_type):
    """Sync individual recipient data with better debugging"""
    email = recipient_data.get("contactemailaddress")
    zoho_contact_id = recipient_data.get("contactid")
    
    frappe.logger().debug(f"Syncing recipient: email={email}, action={action_type}")
    
    if not email:
        frappe.logger().warning(f"No email found for recipient: {recipient_data}")
        return
    
    # Find or create Contact
    contact = find_or_create_contact(recipient_data)
    
    # Check if recipient action already exists
    existing = frappe.db.exists(
        "Campaign Recipient",
        {
            "campaign": campaign.name,
            "email": email,
            "action_type": action_type
        }
    )
    
    if existing:
        recipient = frappe.get_doc("Campaign Recipient", existing)
        frappe.logger().debug(f"Updating existing recipient: {existing}")
    else:
        recipient = frappe.new_doc("Campaign Recipient")
        recipient.campaign = campaign.name
        recipient.email = email
        recipient.action_type = action_type
        frappe.logger().debug(f"Creating new recipient for {email}")
    
    # Map fields
    recipient.contact = contact.name if contact else None
    recipient.zoho_contact_id = zoho_contact_id
    
    # Handle sent_date - parse from "sentdate" field
    sent_date = recipient_data.get("sentdate")
    if sent_date:
        try:
            # Parse date like "05 Dec 2025, 04:21 PM"
            from datetime import datetime
            dt = datetime.strptime(sent_date, "%d %b %Y, %I:%M %p")
            recipient.sent_time = dt
            recipient.action_date = dt
        except (ValueError, TypeError) as e:
            frappe.logger().warning(f"Invalid sent_date {sent_date}: {str(e)}")
    
    # For clicked recipients, handle click-specific data
    if action_type == "Clicked":
        # Get click count
        click_count = recipient_data.get("clickcount")
        if click_count:
            try:
                recipient.click_count = int(click_count)
            except (ValueError, TypeError):
                recipient.click_count = 1
        
        # Store clicked URLs
        clicked_urls = recipient_data.get("clickedurls")
        if clicked_urls:
            # Clean up the URLs string - remove brackets if present
            if isinstance(clicked_urls, str):
                clicked_urls = clicked_urls.strip("[]")
                recipient.clicked_links = clicked_urls
        
        # Store click reports as JSON
        click_reports = recipient_data.get("clickreports")
        if click_reports:
            try:
                if isinstance(click_reports, str):
                    # Parse the string representation of dict
                    import ast
                    try:
                        click_reports_dict = ast.literal_eval(click_reports)
                        recipient.click_reports = json.dumps(click_reports_dict)
                    except:
                        recipient.click_reports = click_reports
                else:
                    recipient.click_reports = json.dumps(click_reports)
            except Exception as e:
                frappe.logger().warning(f"Error parsing click_reports: {str(e)}")
        
        # Store URL clicks data
        url_clicks = recipient_data.get("urlclicks")
        if url_clicks:
            recipient.url_clicks = json.dumps(url_clicks)
    
    # For opened recipients
    elif action_type == "Opened":
        # Store open reports if available
        open_reports = recipient_data.get("openreports")
        if open_reports:
            try:
                if isinstance(open_reports, str):
                    import ast
                    try:
                        open_reports_dict = ast.literal_eval(open_reports)
                        recipient.open_reports = json.dumps(open_reports_dict)
                    except:
                        recipient.open_reports = open_reports
                else:
                    recipient.open_reports = json.dumps(open_reports)
            except Exception as e:
                frappe.logger().warning(f"Error parsing open_reports: {str(e)}")
    
    # Common fields
    recipient.country = recipient_data.get("country")
    recipient.city = recipient_data.get("city")
    recipient.state = recipient_data.get("state")
    
    # Handle boolean fields
    rtbf = recipient_data.get("rtbf")
    recipient.is_rtbf = rtbf == "1" if rtbf else False
    
    recipient.contact_status = recipient_data.get("contactstatus")
    
    # Store additional data
    full_name = f"{recipient_data.get('contactfn', '')} {recipient_data.get('contactln', '')}".strip()
    recipient.full_name = full_name if full_name else None
    
    recipient.company_name = recipient_data.get("companyname")
    recipient.job_title = recipient_data.get("jobtitle")
    
    recipient.save(ignore_permissions=True)
    frappe.logger().debug(f"Saved recipient: {recipient.name}")


def find_or_create_contact(contact_data):
    """Find existing or create new ERPNext Contact"""
    email = contact_data.get("contactemailaddress")
    zoho_contact_id = contact_data.get("contactid")
    
    if not email:
        return None
    
    # Check by Zoho Contact ID first
    if zoho_contact_id:
        existing = frappe.db.get_value(
            "Contact",
            {"zoho_contact_id": zoho_contact_id},
            "name"
        )
        if existing:
            contact = frappe.get_doc("Contact", existing)
            update_contact_from_zoho(contact, contact_data)
            return contact
    
    # Check by email
    existing_email = frappe.db.get_value(
        "Contact Email",
        {"email_id": email},
        "parent"
    )
    
    if existing_email:
        contact = frappe.get_doc("Contact", existing_email)
        update_contact_from_zoho(contact, contact_data)
        return contact
    
    # Create new contact
    contact = frappe.new_doc("Contact")
    contact.first_name = contact_data.get("contactfn") or "Unknown"
    contact.last_name = contact_data.get("contactln") or ""
    
    # Add email
    contact.append("email_ids", {
        "email_id": email,
        "is_primary": 1
    })
    
    # Add phone if available
    phone = contact_data.get("phone") or contact_data.get("mobile")
    if phone:
        contact.append("phone_nos", {
            "phone": phone,
            "is_primary_phone": 1
        })
    
    update_contact_from_zoho(contact, contact_data)
    contact.save(ignore_permissions=True)
    
    return contact


def update_contact_from_zoho(contact, contact_data):
    """Update contact with Zoho data"""
    contact.zoho_contact_id = contact_data.get("contactid")
    contact.zoho_status = contact_data.get("contactstatus")
    contact.zoho_last_synced = now_datetime()
    
    # Update company and designation if not already set
    if not contact.company_name and contact_data.get("companyname"):
        contact.company_name = contact_data.get("companyname")
    
    if not contact.designation and contact_data.get("jobtitle"):
        contact.designation = contact_data.get("jobtitle")
    
    contact.save(ignore_permissions=True)


@frappe.whitelist()
def sync_campaign_by_name(campaign_name):
    """Sync a specific campaign by its ERPNext name"""
    campaign = frappe.get_doc("Campaign", campaign_name)
    
    if not campaign.zoho_campaign_key:
        frappe.throw(_("This campaign is not linked to Zoho"))
    
    sync_campaign_analytics(campaign, campaign.zoho_campaign_key)
    
    return {
        "success": True,
        "message": "Campaign synced successfully"
    }