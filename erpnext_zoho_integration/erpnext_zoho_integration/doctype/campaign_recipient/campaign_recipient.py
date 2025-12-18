# Copyright (c) 2025, Yanky and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class CampaignRecipient(Document):
    def before_save(self):
        # Auto-link to Contact if not already linked
        if not self.contact and self.email:
            contact = frappe.db.get_value(
                "Contact Email",
                {"email_id": self.email},
                "parent"
            )
            if contact:
                self.contact = contact