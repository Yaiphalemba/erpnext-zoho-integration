# ERPNext Zoho Integration

**Version:** 0.0.1 | **Author:** Yanky | **License:** MIT

A comprehensive Frappe/ERPNext integration module that syncs Zoho Campaigns email campaign data directly into your ERPNext instance. Pull campaign metrics, recipient engagement data, and build analytics on top of your email marketing performance.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Setup & Installation](#setup--installation)
4. [Core Concepts](#core-concepts)
5. [API Reference](#api-reference)
6. [Data Models](#data-models)
7. [Sync Flow](#sync-flow)
8. [Authentication](#authentication)
9. [Troubleshooting](#troubleshooting)

---

## Overview

This module bridges Zoho Campaigns with ERPNext, enabling teams to:

- **Sync campaign metadata** from Zoho (subject, sender, sent time, status, etc.)
- **Pull comprehensive analytics** (opens, clicks, bounces, unsubscribes, engagement metrics)
- **Track recipient actions** with granular data on who opened, clicked, or bounced
- **Auto-link contacts** between systems based on email addresses
- **Run reports** on campaign performance within ERPNext

### Key Features

- OAuth 2.0 authentication with automatic token refresh
- Hourly automatic sync via Frappe scheduler
- Bi-directional data mapping (campaign metadata ↔ analytics)
- Support for multiple recipient action types (opens, clicks, bounces, complaints)
- Clean UI dashboard showing live campaign metrics
- Extensible architecture for adding custom fields and workflows

---

## Architecture

### Module Structure

```
erpnext_zoho_integration/
├── api/
│   ├── oauth.py              # OAuth 2.0 flow, token management
│   ├── campaigns.py          # Zoho Campaigns API wrapper
│   ├── sync.py               # Sync logic & data mapping
│   └── custom_fields.py      # Custom field definitions
├── doctype/
│   ├── zoho_settings/        # Settings doctype (OAuth credentials)
│   ├── campaign_analytics/   # Analytics table doctype
│   ├── campaign_recipient/   # Individual recipient records
│   └── ...
├── custom/
│   ├── campaign.json         # Custom fields added to Campaign doctype
│   └── contact.json          # Custom fields added to Contact doctype
├── public/js/
│   └── campaign.js           # Frontend dashboard & interactions
└── report/
    └── campaign_performance/ # Query report for analytics
```

### Data Flow

```
Zoho Campaigns API
       ↓
oauth.py (token mgmt)
       ↓
campaigns.py (API calls)
       ↓
sync.py (data transformation)
       ↓
Campaign (doctype)
├── Campaign Analytics (child table)
├── Campaign Recipient (linked doctype)
└── Contact (linked doctype)
```

### Key Design Patterns

**Token Management**: The `get_valid_token()` function automatically refreshes tokens before expiry (5-minute buffer). If a 401 response occurs, it triggers a refresh and retries once.

**Generic API Wrapper**: `make_api_call()` abstracts all HTTP calls to Zoho, handling headers, error responses, and status checking in one place.

**Data Deduplication**: Recipients are checked by `(campaign, email, action_type)` to prevent duplicates. Contacts are matched first by Zoho ID, then by email.

**Error Resilience**: All API calls are wrapped with try-catch, errors are logged to Frappe's error log, and users see friendly messages.

---

## Setup & Installation

### Prerequisites

- ERPNext/Frappe v14+
- Python 3.7+
- `requests` library (included with Frappe)

### Step 1: Install the App

```bash
cd ~/frappe-bench
bench get-app erpnext_zoho_integration https://github.com/yourusername/erpnext_zoho_integration.git
bench install-app erpnext_zoho_integration
bench migrate
```

### Step 2: Register with Zoho

1. Log in to [Zoho Campaigns](https://campaigns.zoho.in)
2. Go to **Settings > Integrations > API**
3. Create a new OAuth app:
   - **App Name:** ERPNext Integration
   - **Redirect URI:** `https://yourdomain.com/api/method/erpnext_zoho_integration.erpnext_zoho_integration.api.oauth.callback`
   - **Scopes:** `ZohoCampaigns.campaign.READ ZohoCampaigns.contact.CREATE ZohoCampaigns.contact.READ ZohoCampaigns.contact.UPDATE`
4. Copy your **Client ID** and **Client Secret**

### Step 3: Configure in ERPNext

1. Go to **Zoho Settings** in your ERPNext instance
2. Fill in:
   - **Client ID:** From step 2
   - **Client Secret:** From step 2
   - **Redirect URI:** `https://yourdomain.com/api/method/erpnext_zoho_integration.erpnext_zoho_integration.api.oauth.callback`
3. Click **Authorize with Zoho** → You'll be redirected to Zoho's OAuth screen
4. After granting permissions, you'll return with an authorization **Code**
5. Back in Zoho Settings, click **Fetch Tokens**
6. Click **Test Connection** to verify

### Step 4: Initial Sync

Once authenticated, click **Sync All Campaigns** in Zoho Settings. This will:
- Fetch all sent campaigns from Zoho
- Create/update Campaign records in ERPNext
- Sync analytics and recipient data
- Create/link Contact records

---

## Core Concepts

### Campaigns

A **Campaign** in this integration is an email campaign sent via Zoho Campaigns. The custom fields store:
- `zoho_campaign_id` / `zoho_campaign_key`: Zoho identifiers
- `zoho_subject`, `zoho_from_email`, `zoho_reply_to`: Email metadata
- `zoho_sent_time`, `zoho_campaign_status`: Temporal data
- `campaign_analytics`: Child table with metrics (opens, clicks, bounces, etc.)

### Campaign Analytics

A child table storing individual metrics as key-value pairs:
- `metric`: The metric name (e.g., "Opens", "Click Rate %")
- `value`: The numeric value
- `percentage`: For percentage-based metrics

### Campaign Recipients

Represents individual recipient actions within a campaign. Each record tracks:
- Which **Campaign** and **Contact**
- **Action Type**: Sent, Opened, Clicked, Hard Bounced, Soft Bounced, Unsubscribed, Complaint
- **Action Date**: When the action occurred
- **Location**: Country, city, state
- **Additional Data**: Open/click reports (JSON), URL clicks, full name, job title, etc.

### Zoho Settings

A singleton doctype storing OAuth credentials:
- `client_id`, `client_secret`: OAuth credentials
- `access_token`, `refresh_token`: Current tokens
- `token_expiry`: When access token expires
- `is_active`: Boolean flag indicating if integration is active
- `api_domain`: Zoho's API endpoint

---

## API Reference

### OAuth Module (`api/oauth.py`)

#### `authorize()`
Redirects user to Zoho's OAuth consent screen.
- **Whitelist:** Yes (guest allowed)
- **Returns:** Redirect to Zoho auth URL

#### `fetch_tokens(code)`
Exchanges OAuth authorization code for access & refresh tokens.
- **Args:** `code` (authorization code from callback)
- **Whitelist:** Yes (guest allowed)
- **Returns:** Token response with `access_token`, `refresh_token`, `expires_in`, `api_domain`
- **Side Effects:** Saves tokens to Zoho Settings

#### `refresh_access_token()`
Refreshes an expired access token using the refresh token.
- **Whitelist:** Yes (guest allowed)
- **Returns:** New `access_token`
- **Throws:** If no refresh token exists

---

### Campaigns Module (`api/campaigns.py`)

#### `get_valid_token()`
Returns a valid access token, refreshing if expired.
- **Args:** None
- **Returns:** Access token string
- **Throws:** If integration not active

#### `make_api_call(endpoint, method="GET", params=None, data=None)`
Generic wrapper for all Zoho API calls.
- **Args:**
  - `endpoint`: Zoho API endpoint (e.g., "recentcampaigns")
  - `method`: HTTP method ("GET" or "POST")
  - `params`: Query parameters dict
  - `data`: JSON payload dict
- **Returns:** Parsed JSON response
- **Behavior:** Auto-retries once on 401 with token refresh

#### `get_recent_campaigns(limit=20)`
Fetches recent campaigns from Zoho.
- **Whitelist:** Yes
- **Args:** `limit` (max records to fetch)
- **Returns:** `{"campaigns": [...], "total_count": int, "fetched_count": int}`

#### `get_campaign_report(campaign_key)`
Fetches comprehensive report for a single campaign.
- **Whitelist:** Yes
- **Args:** `campaign_key` (Zoho campaign key)
- **Returns:** Nested dict with campaign details, reports, reach, location data

#### `get_campaign_recipients(campaign_key, action="openedcontacts", fromindex=1, range_val=20)`
Fetches recipients grouped by action type.
- **Whitelist:** Yes
- **Args:**
  - `campaign_key`: Zoho campaign key
  - `action`: One of `openedcontacts`, `clickedcontacts`, `bouncedcontacts`, `senthardbounce`, `sentsoftbounce`, `optoutcontacts`, `spamcontacts`
  - `fromindex`: Pagination start (1-indexed)
  - `range_val`: Records per page (max 100 recommended)
- **Returns:** `{"recipients": [...], "action": str, "total_fetched": int}`

#### `sync_campaign_data(campaign_key)`
Convenience function fetching and structuring all campaign data.
- **Whitelist:** Yes
- **Args:** `campaign_key`
- **Returns:** Nested dict with `report`, `opened_contacts`, `clicked_contacts`, `bounced_contacts`, `unsubscribed_contacts`

---

### Sync Module (`api/sync.py`)

#### `sync_all_campaigns()`
Hourly scheduled sync of all recent sent campaigns.
- **Whitelist:** Yes
- **Returns:** `{"success": bool, "synced_count": int, "total_campaigns": int, "errors": [...]}`
- **Behavior:** Only syncs campaigns with status "Sent"

#### `sync_single_campaign(campaign_data)`
Internal function syncing a single campaign.
- **Args:** Campaign dict from Zoho API
- **Returns:** Created/updated Campaign doc
- **Side Effects:** Creates Campaign record, syncs analytics, syncs recipients

#### `sync_campaign_analytics(campaign, campaign_key)`
Syncs metrics from Zoho report into Campaign Analytics child table.
- **Args:** Campaign doc, Zoho campaign key
- **Side Effects:** Clears existing analytics, inserts new ones

#### `sync_campaign_recipients_data(campaign, campaign_key)`
Syncs all recipient actions (opens, clicks, bounces, etc.).
- **Args:** Campaign doc, Zoho campaign key
- **Behavior:** Handles multiple action types, includes debug logging

#### `sync_recipient(campaign, recipient_data, action_type)`
Syncs individual recipient record with detailed action data.
- **Args:** Campaign doc, recipient dict from Zoho, action type string
- **Side Effects:** Creates/updates Campaign Recipient, links to Contact

#### `find_or_create_contact(contact_data)`
Finds or creates an ERPNext Contact based on email/Zoho ID.
- **Args:** Recipient contact data dict
- **Returns:** Contact doc or None
- **Matching Logic:** Zoho ID first, then email

#### `update_contact_from_zoho(contact, contact_data)`
Updates Contact doc with Zoho metadata.
- **Args:** Contact doc, Zoho contact data
- **Side Effects:** Sets company, designation, Zoho ID, status

#### `sync_campaign_by_name(campaign_name)`
Manual sync of a specific campaign.
- **Whitelist:** Yes
- **Args:** `campaign_name` (ERPNext Campaign name)
- **Returns:** `{"success": bool, "message": str}`

---

## Data Models

### Campaign (Extended)

Standard ERPNext Campaign doctype with additional custom fields:

**Zoho Campaign Data Section:**
- `zoho_campaign_id` (Data, unique, read-only)
- `zoho_campaign_key` (Data, read-only)
- `zoho_subject` (Data, read-only)
- `zoho_from_email` (Data, read-only)
- `zoho_sent_time` (Datetime, read-only)
- `zoho_campaign_status` (Data, read-only) — e.g., "Sent", "Draft"
- `zoho_campaign_type` (Data, read-only)
- `zoho_reply_to` (Data, read-only)
- `zoho_preview_url` (Small Text, read-only) — Direct link to preview

**Campaign Analytics Section:**
- `campaign_analytics` (Table, Campaign Analytics doctype)
- `last_synced` (Datetime, read-only)

### Campaign Analytics (Child Table)

**Fields:**
- `metric` (Data, required) — Metric name (e.g., "Opens")
- `value` (Data) — Numeric value
- `percentage` (Percent) — For percentage metrics

**Example rows:**
```
| Metric           | Value | Percentage |
|------------------|-------|------------|
| Emails Sent      | 5000  |            |
| Delivered        | 4950  | 99.0       |
| Opens            | 1200  | 24.2       |
| Open Rate %      |       | 24.2       |
| Unique Clicks    | 450   | 9.1        |
| Click Rate %     |       | 9.1        |
| Bounces          | 50    | 1.0        |
| Bounce Rate %    |       | 1.0        |
```

### Campaign Recipient

**Key Fields:**
- `campaign` (Link, Campaign, required)
- `contact` (Link, Contact) — Auto-linked if email matches
- `email` (Data, required)
- `zoho_contact_id` (Data, read-only)
- `action_type` (Select, required) — Sent, Opened, Clicked, Hard Bounced, Soft Bounced, Unsubscribed, Complaint
- `action_date` (Datetime) — When action occurred
- `sent_time` (Datetime) — When email was sent
- `open_count` (Int) — Number of times opened
- `country`, `city`, `state` (Data) — Geolocation
- `is_spam`, `is_optout` (Check) — Status flags
- `contact_status` (Data) — Zoho contact status
- `full_name`, `company_name`, `job_title` (Data) — Contact details
- `open_reports` (Long Text) — JSON data for opened emails
- `click_count`, `clicked_links`, `url_clicks` (Data/Long Text) — For clicked recipients

**Naming:** `{contact}-{email}-{##}` (auto-generated)

**Auto-linking:** `before_save()` hook links to Contact if email matches existing Contact Email record

### Contact (Extended)

Standard ERPNext Contact doctype with Zoho fields:

**Zoho Data Section:**
- `zoho_contact_id` (Data, unique, read-only)
- `zoho_status` (Data, read-only)
- `zoho_last_synced` (Datetime, read-only)

### Zoho Settings (Singleton)

**Fields:**
- `client_id` (Data)
- `client_secret` (Password)
- `redirect_uri` (Data)
- `access_token` (Password, read-only)
- `refresh_token` (Password, read-only)
- `token_expiry` (Datetime, read-only)
- `api_domain` (Data, read-only) — Defaults to `https://www.zohoapis.in`
- `code` (Data) — Temporary OAuth authorization code
- `is_active` (Check, read-only) — True when fully authenticated

---

## Sync Flow

### Automatic Hourly Sync

Triggered by Frappe scheduler:

```python
scheduler_events = {
    "hourly": [
        "erpnext_zoho_integration.erpnext_zoho_integration.api.sync.sync_all_campaigns"
    ]
}
```

**Flow:**
1. Fetch up to 50 recent campaigns from Zoho
2. Filter for "Sent" status only
3. For each campaign:
   - Create or update Campaign doc
   - Sync analytics (metrics) into Campaign Analytics child table
   - Sync recipient actions (opens, clicks, bounces, etc.) into Campaign Recipient docs
   - Auto-create/link Contacts based on email
4. Commit all changes
5. Return summary with success count and errors

### Manual Sync

Users can trigger sync via:
- **Zoho Settings > Sync All Campaigns** button (UI)
- **Campaign form > Sync from Zoho** button (single campaign)
- **API:** `frappe.call({method: "erpnext_zoho_integration.erpnext_zoho_integration.api.sync.sync_campaign_by_name", args: {campaign_name: "SAL-CAM-2025-00001"}})`

### Conflict Resolution

**Duplicate Prevention:**
- Campaign Recipient records checked by `(campaign, email, action_type)` tuple
- Existing records are updated, not re-created
- Contact records checked by Zoho ID first, then by email

**Data Consistency:**
- Analytics cleared and rebuilt on each sync (no incremental updates)
- Recipient data upserted (update if exists, insert if new)
- Contacts auto-linked by email if not already linked by Zoho ID

---

## Authentication

### OAuth 2.0 Flow

**Step 1: Authorization Request**
```
User clicks "Authorize with Zoho" in Zoho Settings
↓
Redirects to: https://accounts.zoho.in/oauth/v2/auth?
  response_type=code&
  client_id={CLIENT_ID}&
  scope=ZohoCampaigns.campaign.READ+...&
  redirect_uri={REDIRECT_URI}&
  access_type=offline&
  prompt=consent
```

**Step 2: User Grants Permission**
```
User logs in to Zoho and grants scopes
↓
Redirected back to: {REDIRECT_URI}?code={AUTH_CODE}&state=...
```

**Step 3: Token Exchange**
```
POST https://accounts.zoho.in/oauth/v2/token
  client_id={CLIENT_ID}
  client_secret={CLIENT_SECRET}
  grant_type=authorization_code
  code={AUTH_CODE}
  redirect_uri={REDIRECT_URI}
↓
Response:
{
  "access_token": "...",
  "refresh_token": "...",
  "api_domain": "https://www.zohoapis.in",
  "expires_in": 3600
}
```

**Step 4: Token Storage**
- `access_token` and `refresh_token` saved to Zoho Settings (encrypted by Frappe)
- `token_expiry` = now + expires_in
- `is_active` set to 1

### Token Refresh

When token expires (or is about to):
```python
def get_valid_token():
    token_expiry = get_datetime(settings.token_expiry)
    
    # Refresh if expired or expires in < 5 minutes
    if token_expiry and now_datetime() >= (token_expiry - timedelta(minutes=5)):
        return refresh_access_token()
    
    return settings.get_password("access_token")
```

**Refresh Flow:**
```
POST https://accounts.zoho.in/oauth/v2/token
  client_id={CLIENT_ID}
  client_secret={CLIENT_SECRET}
  grant_type=refresh_token
  refresh_token={REFRESH_TOKEN}
↓
Response: New access_token (refresh_token stays the same)
```

### Scopes Required

- `ZohoCampaigns.campaign.READ` — Read campaign data
- `ZohoCampaigns.contact.CREATE` — Create contacts
- `ZohoCampaigns.contact.READ` — Read contact data
- `ZohoCampaigns.contact.UPDATE` — Update contacts

---

## Troubleshooting

### Common Issues

**"Zoho integration is not active"**
- **Cause:** `is_active` flag is 0 in Zoho Settings
- **Fix:** Complete OAuth flow. Click "Authorize with Zoho" → "Fetch Tokens"

**"No refresh token available"**
- **Cause:** Initial OAuth flow incomplete, or tokens manually cleared
- **Fix:** Re-authenticate via Zoho Settings > "Authorize with Zoho"

**"401 Unauthorized"**
- **Cause:** Token expired and refresh failed
- **Fix:** Check Client ID/Secret are correct. Re-authenticate if needed.

**"Failed to fetch campaigns: No contacts"**
- **Cause:** Campaign had no recipients (Zoho returns this as a message, not an error)
- **Behavior:** Treated as success; sync continues
- **Result:** Campaign record created with no recipients

**Campaign syncs but no analytics appear**
- **Cause:** Zoho API returned empty analytics dict
- **Fix:** Verify campaign has at least one sent email. Wait a few minutes for Zoho to calculate stats.

**Contacts not auto-linking**
- **Cause:** Email doesn't exactly match existing Contact Email record
- **Fix:** Create contact manually or fix email in both systems

**"Sync timeout" after 30+ minutes**
- **Cause:** Too many recipients to sync at once
- **Fix:** Reduce `range_val` in `get_campaign_recipients()` or split manual syncs by campaign

### Debug Tips

**Check error log:**
```python
frappe.log_error(frappe.get_traceback(), "Zoho Sync Error")
```
Errors appear in **Tools > Error Log**

**Enable detailed logging:**
In `sync_campaign_recipients_data()`, look for `frappe.logger().info()` and `frappe.logger().debug()` calls. These appear in **server logs**.

**Verify token manually:**
```python
frappe.get_single("Zoho Settings").get_password("access_token")
```

**Test API call:**
```python
from erpnext_zoho_integration.erpnext_zoho_integration.api.campaigns import get_recent_campaigns
result = get_recent_campaigns(limit=5)
```

---

## Performance Notes

- **Hourly sync:** Typical runtime ~2-5 minutes for 50 campaigns with 1000+ recipients per campaign
- **Database:** Campaign Recipient table grows ~10K-50K rows per 100 campaigns synced
- **API Rate Limits:** Zoho has no published limits; use exponential backoff if hitting 429 responses
- **Memory:** Each sync loads all recipients into memory; watch out with 100K+ recipient records

---

## License

MIT. See LICENSE file.

## Support

For issues, questions, or contributions, contact the development team or open an issue in the repository.