// Copyright (c) 2025, ronoh and contributors
// For license information, please see license.txt

frappe.query_reports["Statement details"] = {
		"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname":"finance_book",
			"label": __("Finance Book"),
			"fieldtype": "Link",
			"options": "Finance Book",
			"hidden": 1,

		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1,
			"width": "60px"
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1,
			"width": "60px"
		},
		{
			"fieldname":"account",
			"label": __("Account"),
			"fieldtype": "MultiSelectList",
			"options": "Account",
			"hidden": 1,
 
			get_data: function(txt) {
				return frappe.db.get_link_options('Account', txt, {
					company: frappe.query_report.get_filter_value("company")
				});
			}
		},
		{
			"fieldname":"voucher_no",
			"label": __("Voucher No"),
			"fieldtype": "Data",
			"hidden": 1,

			on_change: function() {
				frappe.query_report.set_filter_value('group_by', "Group by Voucher (Consolidated)");
			}
		},
		{
			"fieldtype": "Break",
		},
		{
			"fieldname":"party_type",
			"label": __("Party Type"),

			"fieldtype": "Link",
			"options": "Party Type",
			"default": "Customer",
			"reqd" : 1 , 
			on_change: function() {
				frappe.query_report.set_filter_value('party', "");
			}
		},
		{
			"fieldname":"party",
			"label": __("Party"),
			"reqd" : 1 , 
			"fieldtype": "MultiSelectList",
			get_data: function(txt) {
				if (!frappe.query_report.filters) return;

				let party_type = frappe.query_report.get_filter_value('party_type');
				if (!party_type) return;

				return frappe.db.get_link_options(party_type, txt, {
					'disabled' : frappe.query_report.get_filter_value("disabled_party")
				});
			},
			on_change: function() {
				var party_type = frappe.query_report.get_filter_value('party_type');
				var parties = frappe.query_report.get_filter_value('party');

				if(!party_type || parties.length === 0 || parties.length > 1) {
					frappe.query_report.set_filter_value('party_name', "");
					frappe.query_report.set_filter_value('tax_id', "");
					return;
				} else {
					var party = parties[0];
					var fieldname = erpnext.utils.get_party_name(party_type) || "name";
					frappe.db.get_value(party_type, party, fieldname, function(value) {
						frappe.query_report.set_filter_value('party_name', value[fieldname]);
					});

					if (party_type === "Customer" || party_type === "Supplier") {
						frappe.db.get_value(party_type, party, "tax_id", function(value) {
							frappe.query_report.set_filter_value('tax_id', value["tax_id"]);
						});
					}
				}
			}
		},
		{
			"fieldname":"party_name",
			"label": __("Party Name"),
			"fieldtype": "Data",
			"hidden": 0
		},
		{
			"fieldname":"group_by",
			"label": __("Group by"),
			"fieldtype": "Select",
			"hidden": 1,

			"options": [
				"",
				{
					label: __("Group by Voucher"),
					value: "Group by Voucher",
				},
				{
					label: __("Group by Voucher (Consolidated)"),
					value: "Group by Voucher (Consolidated)",
				},
				{
					label: __("Group by Account"),
					value: "Group by Account",
				},
				{
					label: __("Group by Party"),
					value: "Group by Party",
				},
			],
			"default": "Group by Voucher (Consolidated)"
		},
		{
			"fieldname":"tax_id",
			"label": __("Tax Id"),
			"fieldtype": "Data",
			"hidden": 1,

		},
		{
			"fieldname": "presentation_currency",
			"label": __("Currency"),
			"fieldtype": "Select",
			"hidden": 1,

			"options": erpnext.get_presentation_currency_list()
		},
		{
			"fieldname":"cost_center",
			"label": __("Cost Center"),
			"fieldtype": "MultiSelectList",
			"hidden": 1,

			get_data: function(txt) {
				return frappe.db.get_link_options('Cost Center', txt, {
					company: frappe.query_report.get_filter_value("company")
				});
			}
		},
		{
			"fieldname":"project",
			"label": __("Project"),
			"fieldtype": "MultiSelectList",
			"hidden": 1,

			get_data: function(txt) {
				return frappe.db.get_link_options('Project', txt, {
					company: frappe.query_report.get_filter_value("company")
				});
			}
		},
		{
			"fieldname": "include_dimensions",
			"label": __("Consider Accounting Dimensions"),
			"fieldtype": "Check",
			"hidden": 1,

			"default": 1
		},
		{
			"fieldname": "show_opening_entries",
			"label": __("Show Opening Entries"),
			"fieldtype": "Check",
			"hidden": 1,

		},
		{
			"fieldname": "include_default_book_entries",
			"label": __("Include Default Book Entries"),
			"fieldtype": "Check",
			"hidden": 1,

		},
		{
			"fieldname": "show_cancelled_entries",
			"label": __("Show Cancelled Entries"),
			"fieldtype": "Check",
			"hidden": 1,

		},
		{
			"fieldname": "show_net_values_in_party_account",
			"label": __("Show Net Values in Party Account"),
			"fieldtype": "Check",
			"hidden": 1,

		},
		{
			"fieldname": "disabled_party",
			"label": __("Show Disabled Party"),
			"fieldtype": "Check",
			"hidden": 0,

		},
	],
  onload: function(report) {
		report.page.add_inner_button(__("Send via Email"), function() {
			var filters = report.get_values();
			frappe.db.get_value('Customer', filters.party[0], 'email_id')
			.then(r => {
							var customer_email = r.message.email_id;
							frappe.prompt({
							    label: 'Email Receipt',
							    fieldname: 'customer_email',
							    fieldtype: 'Data',
							  	default: customer_email,
							}, (values) => {
							    console.log(values.email_id);
							    customer_email = values.customer_email;
					    		frappe.call({
										method: 'statement_details.statement_details.customer_scheduler.customer_scheduler.send_email_statement_detail_on_specific_email',
										args: {
											'filters' : filters,
											'customer_email' : customer_email,
										},
										async: true,
										freeze: true,
										freeze_message: 'Sending the report via Email',
										callback: (r) => {
											if (r.message){
												frappe.msgprint("Email Sent Successfully.")
											}
										},
										error: (r) => {
											console.log(r.message)
										}

									})
							}, null, 'Send')			
			});			
		});

		report.page.add_inner_button(__("Generate Pdf"), function() {
			var filters = report.get_values();
			frappe.call({
				method: 'statement_details.statement_details.customer_scheduler.customer_scheduler.generate_pdf_statement_detail',
				args: {
					'filters' : filters,
				},
				freeze: true,
				freeze_message: "<b style='color: darkgray;'>Wait! generating the report pdf.</b>",
				callback: (r) => {
					if (r.message){
						console.log(r.message)
						// working url

						// window.open(r.message[1]+"/api/method/frappe.utils.print_format.download_pdf?doctype=Customer%20Scheduler%20Report&name="+r.message[0]+"&format=Customer%20Scheduler%20Report%20V-1&no_letterhead=0")
						window.open(r.message)
					}
				},
				error: (r) => {
					console.log(r.message)
				}

			})
			
		});
	},
}

function get_columns(filters) {
    if (filters.get("presentation_currency")) {
        currency = filters["presentation_currency"];
    } else {
        if (filters.get("company")) {
            currency = get_company_currency(filters["company"]);
        } else {
            company = get_default_company();
            currency = get_company_currency(company);
        }
    }

    columns = [
        {
            "label": __("Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 90,
        },
        {"label": __("Description"), "fieldname": "voucher_type", "width": 140},
        {
            "label": __("Voucher No"),
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 180,
        },
        {
            "label": __("Item"),
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": __("Chq Ref Date"),
            "fieldname": "chq_ref_date",
            "fieldtype": "Date",
            "width": 180,
        },
    ];

    return columns;
}

erpnext.utils.add_dimensions('General Ledger', 15);
