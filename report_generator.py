"""
report_generator.py
--------------------
Builds a downloadable PDF "compliance report" summarizing what
was done to the dataset - required by the project proposal.
"""

from datetime import datetime
from fpdf import FPDF


def generate_compliance_report(dataset_name, num_records, column_actions,
                                risk_before, risk_after, output_path):
    """
    column_actions: list of dicts like
        {"column": "email", "label": "Email", "method": "mask"}
    """
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Data Anonymization Compliance Report", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.ln(4)

    pdf.cell(0, 8, f"Dataset Name: {dataset_name}", ln=True)
    pdf.cell(0, 8, f"Number of Records: {num_records}", ln=True)
    pdf.cell(0, 8, f"Generated On: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Privacy Risk Score", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Before Anonymization: {risk_before}/100", ln=True)
    pdf.cell(0, 8, f"After Anonymization:  {risk_after}/100", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Columns Protected", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for action in column_actions:
        pdf.cell(0, 7,
                  f"- {action['column']} ({action['label']})  ->  {action['method']}",
                  ln=True)

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Compliance Status", ln=True)
    pdf.set_font("Helvetica", "", 11)
    status = "COMPLIANT" if risk_after < 30 else "PARTIALLY COMPLIANT - review remaining risk"
    pdf.cell(0, 8, f"GDPR / DPDP Act indicative status: {status}", ln=True)

    pdf.output(output_path)
    return output_path
