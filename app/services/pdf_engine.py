from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from datetime import datetime
import hashlib

class PDFEngine:
    def generate_audit_report(self, user_name: str, audit_logs: list):
        """Generates a PDF in memory with the audit trail."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # Header
        elements.append(Paragraph(f"AI Governance & Audit Report", styles['Title']))
        elements.append(Paragraph(f"Subject: {user_name}", styles['Heading2']))
        elements.append(Paragraph(f"Generated: {datetime.utcnow().isoformat()}", styles['Normal']))
        elements.append(Spacer(1, 12))

        # Data Table
        data = [["Timestamp", "Event", "Severity", "Details"]]

        for log in audit_logs:
            # Adapter Pattern Logic
            # Timestamp: log.login_timestamp
            # Event: log.action
            # Severity: Derived

            action = log.action if log.action else "UNKNOWN"
            timestamp = log.login_timestamp.strftime("%Y-%m-%d %H:%M") if log.login_timestamp else "N/A"
            details = log.details if log.details else "N/A"

            # Truncate details if too long
            display_details = (details[:50] + '...') if len(details) > 50 else details

            # Derive Severity
            severity = "INFO"
            action_upper = action.upper()
            if any(keyword in action_upper for keyword in ["DELETE", "REVOKE", "FAIL", "WARNING", "ERROR"]):
                severity = "WARNING"

            data.append([
                timestamp,
                action,
                severity,
                display_details
            ])

        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)

        # Footer / Signature
        elements.append(Spacer(1, 24))
        elements.append(Paragraph("Cryptographic Signature (SHA-256):", styles['Heading4']))

        # Calculate Hash of the content (Simulated for this step, usually hash of the final bytes)
        content_string = str(data).encode('utf-8')
        signature = hashlib.sha256(content_string).hexdigest()
        elements.append(Paragraph(signature, styles['Code']))

        doc.build(elements)
        buffer.seek(0)
        return buffer

pdf_engine = PDFEngine()
