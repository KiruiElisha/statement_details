# Copyright (c) 2022, Codes Soft and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, date, timedelta
from datetime import datetime, date
from frappe.utils import add_days,  cstr,  today, getdate, formatdate, nowdate,  get_first_day, date_diff, add_years, flt, \
                        cint, getdate, now, get_site_name
from frappe.utils.pdf import get_pdf,cleanup
from frappe.core.doctype.access_log.access_log import make_access_log
from PyPDF2 import PdfFileWriter
import pdfkit
import json
from frappe.utils.background_jobs import enqueue
from frappe.utils.file_manager import save_file
from frappe.utils.print_format import  report_to_pdf
from frappe.utils.pdf import get_pdf
from frappe.utils.file_manager import save_file_on_filesystem, save_file

party_statement_files = []
class CustomerScheduler(Document):

    def validate(self):
        return None


@frappe.whitelist(allow_guest=True)
def scheduler_job():
    enqueue("statement_details.statement_details.customer_scheduler.customer_scheduler.run_customer_scheduler_job", queue='long', timeout=None)
    return 'success'

@frappe.whitelist(allow_guest  = True)
def run_customer_scheduler_job():
    try:
        doc = frappe.get_doc("Customer Scheduler" , "Customer Scheduler")
        child = doc.scheduler_items
        create_party_statements(child)

    except Exception as e:
        error_message = frappe.get_traceback()+"Error\n"+str(e)
        frappe.log_error(error_message, "run_customer_scheduler_job failed!.")



def create_party_statements(child):
    try:
        if child:
            for row in child:
                currentMonth = datetime.now().month
                currentYear = datetime.now().year
                scheduler_day = f"{currentYear}-{currentMonth}-{row.schedule_day}"
                start_date = str(row.start_date)
                end_date = str(row.end_date)

                batch_args = {
                    'start_date' : start_date,
                    'end_date': end_date,
                    'scheduler_day': scheduler_day
                }

                if row.customer_group and start_date and end_date and scheduler_day:
                    frappe.log_error(f"{row.customer_group} --> scheduler_day: {scheduler_day} ; nowdate: {getdate(nowdate())}", f"Run customer scheduler job for party {row.customer_group}")
                    if getdate(scheduler_day) == getdate(nowdate()):
                        try:
                            batch_count = 0
                            batch_start_idx = 0
                            mod = 0        
                            customer_list = frappe.db.get_list("Customer" ,  filters = {"customer_group" : row.customer_group, "disabled": 0 } , fields =  ["name" , "email_id", "company"])
                            csrl_length = len(customer_list)
                            
                            if csrl_length>0:
                                if csrl_length>100:
                                    mod = csrl_length % 100
                                    csrl_length -= mod
                                    for batch in range(int(csrl_length/100)): 
                                        batch_count += 100
                                        batch_start_idx = batch_count-100
                                        batch_list = customer_list[batch_start_idx : batch_count]
                                        batch_args['batch_list'] = batch_list
                                        enqueue("statement_details.statement_details.customer_scheduler.customer_scheduler.run_batch_for_party_statement", queue='long', timeout=None, batch_args=batch_args)
                                
                                    batch_list = customer_list[batch_count : batch_count+mod]
                                    batch_args['batch_list'] = batch_list
                                    enqueue("statement_details.statement_details.customer_scheduler.customer_scheduler.run_batch_for_party_statement", queue='long', timeout=None, batch_args=batch_args)
                                
                                else:
                                    batch_list = customer_list
                                    batch_args['batch_list'] = batch_list
                                    enqueue("statement_details.statement_details.customer_scheduler.customer_scheduler.run_batch_for_party_statement", queue='long', timeout=None, batch_args=batch_args)

                                from time import sleep
                                sleep(30)
                        except Exception as e:
                            error_message = frappe.get_traceback()+"Error\n"+str(e)
                            frappe.log_error(error_message, "get_data_customer_group function failed.")
        return 'success'
    except Exception as e:
        error_message = frappe.get_traceback()+"Error\n"+str(e)
        frappe.log_error(error_message, "create_party_statements function failed!")

def set_batch_email_for_clients(create_party_statements):
    try:
        frappe.log_error(party_statement_files, 'party_statement_files')
        ebatch_count = 0
        ebatch_start_idx = 0
        estatements_length =  len(party_statement_files)
        if estatements_length>0:
            emod = estatements_length % 100
            estatements_length -= emod
            if estatements_length>100:
                for ebatch in range(estatements_length/100):
                    ebatch_count += 100
                    ebatch_start_idx = batch_count - 100
                    
                    ebatch_list = party_statement_files[ebatch_start_idx : ebatch_count]
                    
                    enqueue("statement_details.statement_details.customer_scheduler.customer_scheduler.run_clients_email_job", queue='long', timeout=None, party_statement_files=ebatch_list)

            ebatch_list =  party_statement_files[ebatch_count : ebatch_count + emod]
            enqueue("statement_details.statement_details.customer_scheduler.customer_scheduler.run_clients_email_job", queue='long', timeout=None, party_statement_files=ebatch_list)
            return 'success in setting batches for client emails.'
    except Exception as e:
        error_message = frappe.get_traceback()+"Error\n"+str(e)
        # frappe.log_error(error_message, "run_clients_email_job failed!")


@frappe.whitelist(allow_guest=True)
def run_batch_for_party_statement(batch_args = {}):
    if batch_args:
        for party in batch_args["batch_list"]:
            get_party_data(party.company, "Customer", [party.name], batch_args["start_date"] , batch_args["end_date"] , party.email_id, batch_args["scheduler_day"])
    
    return 'success'

@frappe.whitelist(allow_guest=True)
def run_clients_email_job(party_statement_files):
    try:
        for party in party_statement_files:
            frappe.sendmail(
                recipients= party['recipients'],
                subject=party['subject'],
                content=party['content'],
                attachments=party['attachments'],
                now=True,
            )
        return 'success in email sending :)'
    except Exception as e:
      error_message = frappe.get_traceback()+"Error \n"+str(e)
      frappe.log_error(error_message, "Customer Scheduler sending Email Error!")


""" This api call is for sending Statement Detail Report on click of Send Specifically button in report page """
@frappe.whitelist(allow_guest  = True)
def generate_pdf_statement_detail(filters):
    filters = frappe._dict(json.loads(filters))
    protocol = get_site_name(frappe.local.request.url)
    domain =  get_site_name(frappe.local.request.host)

    try:
        email_id = frappe.db.get_value('Customer', filters.get("party"), 'email_id')
        only_print=True
        pdf_file_url = get_party_data(filters.company, filters.party_type, filters.party, filters.from_date, filters.to_date, email_id,  today(), only_print)
        return f"{protocol}://{domain}{pdf_file_url}"
    except Exception as e:
        error_message = frappe.get_traceback()+"Error\n"+str(e)
        frappe.log_error(error_message, "Main function named Check Scheduler Date failed.")
        return error_message

""" This api call is for sending Statement Detail Report on click of Send Specifically button in report page """
@frappe.whitelist(allow_guest  = True)
def send_email_statement_detail_on_specific_email(filters, customer_email):
    filters = frappe._dict(json.loads(filters))

    try:
        email_id = customer_email
        result = get_party_data(filters.company, filters.party_type, filters.party, filters.from_date, filters.to_date, email_id,  today())
        return 'Success in sending email ' + str(result)
    except Exception as e:
        error_message = frappe.get_traceback()+"Error\n"+str(e)
        frappe.log_error(error_message, "Main function named Check Scheduler Date failed.")
        return error_message


def get_party_data(company, party_type, party, start_date , end_date , email_id , scheduler_day, only_print=False):
    try:
        filters = frappe._dict({
            "from_date" : start_date, 
            "scheduler_day" : scheduler_day, 
            "to_date" : end_date, 
            "company" : company, 
            "report_date": end_date,
            "range1": 30,
            "range2": 60,
            "range3": 90,
            "range4": 120,
            "party_type": party_type,
            "party": party,
            "group_by": "Group by Voucher (Consolidated)",
            "include_dimensions": 0,
            "show_opening_entries": 0,
            "include_default_book_entries": 0,
            "show_cancelled_entries": 0,
            "show_net_values_in_party_account": 0,
        })

        from statement_details.statement_details.report.statement_details_with_chq_no.statement_details_with_chq_no import execute as statement
        
        data = statement(filters)
        

        customer_personal_detail = data[1][-1]["customer_personal_detial"]
        party_vals = frappe.db.get_value(party_type, party[0], [party_type.lower()+"_name", "tax_id"])
        
        customer_summary = data[4]
        if customer_summary:              
            total_sales = customer_summary[0]["value"] or 0.0 
            total_sales_return =  customer_summary[1]["value"] or 0.0
            total_payment = customer_summary[2]["value"]  or 0.0
            amount_due = customer_summary[3]["value"] or 0.0

            ageing_summary = data[1][-1]["ageing_data"] 
            if ageing_summary:
                age_30 = ageing_summary["30"]
                age_60 = ageing_summary["60"]
                age_90 = ageing_summary["90"]
                age_120 = ageing_summary["120"]
                age_120_above = ageing_summary["above"]

        report_details = data[1]
        report_rows = []
        is_hundred_above_oustanding = False
        if report_details:
            if report_details[0]:
                report_rows.append({
                    "date": report_details[0].get("posting_date"), 
                    "voucher_no" : report_details[0].get("voucher_no"),
                    "description" : report_details[0].get("voucher_type"),
                    "allocation" : report_details[0].get("against_voucher"),
                    "ref_no": report_details[0].get("ref_number"),
                    "chq_ref_date": report_details[0].get("chq_ref_date"),
                    "mode_of_payment": report_details[0].get("mode_of_payment"),
                    "cheque_no": report_details[0].get("cheque_no"),
                    "credit" : report_details[0].get("credit") or 0.0 ,
                    "debit" : report_details[0].get("debit") or 0.0,
                    "balance" : report_details[0].get("balance") or 0.0,
                })
                if report_details[0].get("balance") > 100:
                    is_hundred_above_oustanding = True 

            if len(report_details)>1:
                for i in report_details[1:]:
                    if i.get("voucher_type") not in ("'Total'", "'Closing (Opening + Total)'", "'Opening Balance'"):
                        report_rows.append({
                            "date": i.get("posting_date"), 
                            "voucher_no" : i.get("voucher_no"),
                            "description" : i.get("voucher_type"),
                            "allocation" : i.get("against_voucher"),
                            "ref_no": i.get("ref_number"),
                            "chq_ref_date": i.get("chq_ref_date"),
                            "mode_of_payment": i.get("mode_of_payment"),
                            "cheque_no": i.get("cheque_no"),
                            "credit" : i.get("credit") or 0.0 ,
                            "debit" : i.get("debit") or 0.0,
                            "balance" : i.get("balance") or 0.0,
                        })

        pdc_details = data[1][-1]["cheque_list"]
        pdc_total_amount = "{:.2f}".format(float(data[1][-1]["totals_pds"].get("p_paid_amount") or 0.0))
        pdc_rows = []
        if pdc_details:
            for pdc in pdc_details:
                pdc_rows.append({
                    "posting_date": pdc.get("pd_posting_date"),
                    "cheque_no": pdc.get("pd_cheque_name"),
                    "reference_no": pdc.get("pd_reference_no"),
                    "reference_date": pdc.get("pd_reference_date"),
                    "paid_amount": pdc.get("p_paid_amount"),
                })


        chart = data[3]
        chart_vals = {}    
        if chart:
            chart_vals['sales_vals'] = str(chart['data']['datasets'][0]['values'])
            chart_vals['rtn_vals'] = str(chart['data']['datasets'][1]['values'])
            chart_vals['payment_vals'] = str(chart['data']['datasets'][2]['values'])
            chart_vals['month_list'] = str(chart['data']['labels'])
            chart_vals['month_sales_values'] = chart_vals['sales_vals']
            chart_vals['month_sales_return_values'] = chart_vals['rtn_vals']
            chart_vals['month_payment_values'] = chart_vals['payment_vals']

        template = frappe.render_template(
            "statement_details/statement_details/customer_scheduler/customer_scheduler.html",
            {   
                "chart_vals": chart_vals,
                "report_rows" : report_rows,
                "pdc_rows": pdc_rows,
                "pdc_total_amount": pdc_total_amount,
                "company": company,
                "party_type": party_type,
                "party": party[0],
                "party_name": party_vals[0],
                "email_id": email_id,
                "pin_no": party_vals[1],
                "start_date": start_date,
                "end_date": end_date,
                "creation": frappe.utils.now(),
                "customer_personal_detail": customer_personal_detail,
                "total_sales": total_sales,
                "total_sales_return": total_sales_return,
                "total_payment": total_payment,
                "amount_due": amount_due,
                "age_30": age_30,
                "age_60": age_60,
                "age_90": age_90,
                "age_120": age_120,
                "age_120_above": age_120_above,
            })

        filename = generate_statement_pdf(template, party_vals[0])
        
        if only_print!=True and is_hundred_above_oustanding==True:
            attachment = {"fid" : filename}
            doc = frappe.get_doc("Customer Scheduler")
            doc_recipients = []
            if doc.recipients:
                doc_recipients = [r.strip() for r in doc.recipients.split(",")]

            custdoc = frappe.get_doc(party_type, party)
            frappe.msgprint(custdoc)
            if party_type=='Customer':
                custdoc_recipients = custdoc.email_id
            customer_recipients = []
            if custdoc_recipients:
                customer_recipients = [c.strip() for c in custdoc_recipients.split(",")]
            if email_id:
                customer_recipients.append(email_id)

            email_recipients = []
            email_recipients.extend(doc_recipients)
            
            if doc.send_customers_email==1:
                email_recipients.extend(customer_recipients)

            subject = doc.email_subject or ""
            content = doc.email_body or ""

            party_statement_files.append({'party': party[0], 'recipients' : ['test@mail.com'], 'subject' : subject, 'content' : content, 'attachments' : [attachment]})
            try:
                frappe.sendmail(
                    recipients= email_recipients,
                    subject=subject,
                    content=content,
                    attachments=[attachment],
                    now=True,
                )
            except Exception as e:
                error_message = frappe.get_traceback() + "Error\n"+str(e)
                frappe.log_error(error_message, "Email failed for party {party[0]}!")
            return 'client email sending job success.'
        file_url = frappe.get_doc('File', filename).file_url
        return file_url
    except Exception as e:
        error_message = frappe.get_traceback()+"Error\n"+str(e)
        frappe.log_error(error_message, "get_party_data function failed. ")


@frappe.whitelist(allow_guest=True)
def generate_statement_pdf(template, party_name):
    try:
        # Attaching PDF to response
        pdf = get_pdf(template)
        file_data = save_file(party_name+'.pdf', pdf, '', '')
        
        return file_data.name

    except:
        frappe.log_error("generate_statement_pdf failed", generate_statement_pdf)
