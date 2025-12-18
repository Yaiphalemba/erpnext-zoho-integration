// Copyright (c) 2025, Yanky and contributors
// For license information, please see license.txt

frappe.query_reports["Campaign Performance"] = {
	"filters": [
		{
					"fieldname": "employee",
					"label": __("Employee"),
					"fieldtype": "Link",
					"options": "Employee",
					"default": ""
        },        
		{
			"fieldname": "printed_on",
			"label": __("Printed On"),
			"fieldtype": "Data",
			"default": moment(frappe.datetime.now_datetime()).format("MM-DD-YYYY HH:mm:ss"),
			"read_only": 1
		}
	]
};
