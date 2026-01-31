"""
Module tao phieu luong PDF
"""

import os
from datetime import datetime
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.models import Payroll, User, Violation, Reward, AttendanceRecord
from flask import current_app


def format_currency(amount):
    """Format so tien thanh chuoi VND"""
    if amount is None:
        return "0"
    return "{:,.0f}".format(amount)


def generate_payslip_pdf(payroll_id, output_path=None):
    """
    Tao phieu luong PDF cho 1 nhan vien

    Args:
        payroll_id: ID cua Payroll record
        output_path: Duong dan luu file (None = tra ve BytesIO)

    Returns:
        BytesIO or filepath
    """
    payroll = Payroll.query.get(payroll_id)
    if not payroll:
        return None

    user = User.query.get(payroll.user_id)
    if not user:
        return None

    # Tao buffer hoac file
    if output_path:
        buffer = output_path
    else:
        buffer = BytesIO()

    # Tao document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Center
    )
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=10
    )
    normal_style = styles['Normal']

    # Content
    elements = []

    # Title
    elements.append(Paragraph("PHIEU LUONG THANG", title_style))
    elements.append(Paragraph(f"Thang {payroll.month}/{payroll.year}", title_style))
    elements.append(Spacer(1, 20))

    # Thong tin nhan vien
    elements.append(Paragraph("THONG TIN NHAN VIEN", header_style))

    info_data = [
        ["Ho va ten:", user.full_name],
        ["Ma nhan vien:", user.username],
        ["Loai nhan vien:", "Full-time" if user.employment_type.value == "full_time" else "Part-time"],
        ["Luong theo gio:", f"{format_currency(user.hourly_rate)} VND"],
        ["Ty le huong luong:", f"{user.salary_percentage}%"]
    ]

    info_table = Table(info_data, colWidths=[5*cm, 10*cm])
    info_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))

    # Chi tiet luong
    elements.append(Paragraph("CHI TIET LUONG", header_style))

    salary_data = [
        ["Khoan muc", "So luong/Gio", "Don gia", "Thanh tien"],
        ["Tong gio lam viec", f"{payroll.total_work_hours} gio", f"{format_currency(user.hourly_rate)}", f"{format_currency(payroll.gross_salary)}"],
        ["So ca lam viec", f"{payroll.total_shifts} ca", "", ""],
    ]

    # Tien an ca
    if payroll.meal_support_amount > 0:
        meal_days = int(payroll.meal_support_amount / 25000)
        salary_data.append(["Tien an ca", f"{meal_days} ngay", "25,000", f"{format_currency(payroll.meal_support_amount)}"])

    # Thuong
    if payroll.total_reward > 0:
        salary_data.append(["Tien thuong", "", "", f"+{format_currency(payroll.total_reward)}"])

    # Phat
    if payroll.total_penalty > 0:
        salary_data.append(["Tien phat", f"{payroll.late_count} lan", "", f"-{format_currency(payroll.total_penalty)}"])

    # Tam ung
    if payroll.advance_payment > 0:
        salary_data.append(["Tien tam ung", "", "", f"-{format_currency(payroll.advance_payment)}"])

    salary_data.append(["", "", "", ""])
    salary_data.append(["THUC LINH", "", "", f"{format_currency(payroll.net_salary)} VND"])

    salary_table = Table(salary_data, colWidths=[5*cm, 3*cm, 3*cm, 4*cm])
    salary_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
    ]))
    elements.append(salary_table)
    elements.append(Spacer(1, 30))

    # Chi tiet di muon (neu co)
    if payroll.late_count > 0:
        elements.append(Paragraph("CHI TIET DI MUON", header_style))

        from datetime import date as date_type
        month_start = date_type(payroll.year, payroll.month, 1)
        if payroll.month == 12:
            month_end = date_type(payroll.year + 1, 1, 1)
        else:
            month_end = date_type(payroll.year, payroll.month + 1, 1)

        violations = Violation.query.filter(
            Violation.user_id == payroll.user_id,
            Violation.type == 'late',
            Violation.date >= month_start,
            Violation.date < month_end
        ).order_by(Violation.date).all()

        late_data = [["Ngay", "Mo ta", "Tien phat"]]
        for v in violations:
            late_data.append([
                v.date.strftime('%d/%m/%Y'),
                v.description or "",
                f"{format_currency(v.penalty_amount)}"
            ])

        late_table = Table(late_data, colWidths=[4*cm, 7*cm, 4*cm])
        late_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(late_table)
        elements.append(Spacer(1, 20))

    # Footer
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(f"Ngay in: {datetime.now().strftime('%d/%m/%Y %H:%M')}", normal_style))
    elements.append(Paragraph("HR Management System - Powered by Vibecode Kit v4.0", normal_style))

    # Build PDF
    doc.build(elements)

    if output_path:
        return output_path
    else:
        buffer.seek(0)
        return buffer


def generate_monthly_report_pdf(month, year, output_path=None):
    """
    Tao bao cao luong thang cho tat ca NV
    """
    payrolls = Payroll.query.filter_by(month=month, year=year).all()

    if output_path:
        buffer = output_path
    else:
        buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        spaceAfter=20,
        alignment=1
    )

    elements = []

    # Title
    elements.append(Paragraph(f"BAO CAO LUONG THANG {month}/{year}", title_style))
    elements.append(Spacer(1, 20))

    # Bang du lieu
    data = [["STT", "Ho ten", "Gio lam", "Ca lam", "Phat", "Thuong", "An ca", "Thuc linh"]]

    for i, p in enumerate(payrolls, 1):
        user = User.query.get(p.user_id)
        data.append([
            str(i),
            user.full_name if user else "N/A",
            f"{p.total_work_hours}",
            f"{p.total_shifts}",
            format_currency(p.total_penalty),
            format_currency(p.total_reward),
            format_currency(p.meal_support_amount),
            format_currency(p.net_salary)
        ])

    # Tong cong
    total_net = sum(p.net_salary for p in payrolls)
    data.append(["", "TONG CONG", "", "", "", "", "", format_currency(total_net)])

    table = Table(data, colWidths=[1*cm, 4*cm, 2*cm, 1.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm])
    table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(table)

    doc.build(elements)

    if output_path:
        return output_path
    else:
        buffer.seek(0)
        return buffer
