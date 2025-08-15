# -*- coding: utf-8 -*-
import io
import os
import streamlit as st
import plotly.express as px
import jdatetime
from typing import Any

# Optional libs for RTL in PDF
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_RTL_LIBS = True
except Exception:
    HAS_RTL_LIBS = False

# ---- Persian digits + thousand separator ----
PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
EN_DIGITS = "0123456789"
FA_TO_EN = str.maketrans(PERSIAN_DIGITS, EN_DIGITS)

def to_persian_number(num, decimals=0):
    """
    num: number
    decimals: decimal digits for display (default 0 for Tomans)
    """
    if decimals == 0:
        s = f"{round(num):,}"
    else:
        s = f"{num:,.{decimals}f}"
    out = []
    for ch in s:
        if ch.isdigit():
            out.append(PERSIAN_DIGITS[ord(ch) - ord('0')])
        else:
            out.append(ch)
    return "".join(out)

def fa_to_en_num_str(s: str) -> str:
    # convert Persian digits to English, keep digits only
    s = (s or "").translate(FA_TO_EN)
    # keep digits only
    digits = "".join(ch for ch in s if ch.isdigit())
    return digits or "0"

def format_with_commas(s: str) -> str:
    n = int(fa_to_en_num_str(s))
    return f"{n:,}"

# ---- Streamlit page ----
st.set_page_config(page_title="الزامات مالی - ماشین‌حساب", page_icon="💰", layout="centered")

# ---- RTL styles (kept) ----
rtl_style = """
<style>
* { direction: rtl; text-align: right; font-family: Vazirmatn, Tahoma, "IRANSans", sans-serif; }
table { direction: rtl; }
.block-container { padding-top: 1rem; }
h1, h2, h3 { font-weight: 700; }
.kimiya-note {
    background: #fffbe6; border: 1px dashed #f0c36d; padding: 8px 12px; display: inline-block;
    border-radius: 12px; font-weight: 700; font-size: 16px;
}
.footer-note { color: #666; font-size: 12px; }
.pay-note {
    background: #eefaf0; border: 1px solid #b9e4c9; padding: 10px 12px; border-radius: 10px; margin-top: 8px;
}
</style>
"""
st.markdown(rtl_style, unsafe_allow_html=True)

# ---- Header & "logo" (kept) ----
st.markdown("<div class='kimiya-note'>کارگاه کیمیاگری ۹</div>", unsafe_allow_html=True)
st.markdown("<h1 style='text-align:center;'>سلام کیمیاگر</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;'>این نرم‌افزار برای تسهیل فعالیت اقتصادی تو تهیه شده است.</p>", unsafe_allow_html=True)

# ---- Inputs (live thousand separators) ----
st.header("📥 ورود اطلاعات")
business_name = st.text_input("🏢 نام کسب‌وکار", value="")  # New input field

def formatted_number_input(label: str, key: str) -> int:
    value_str = st.session_state.get(key, "0")

    def _format_callback():
        st.session_state[key] = format_with_commas(st.session_state[key])

    val_str = st.text_input(label, value=value_str, key=key, on_change=_format_callback)
    return int(fa_to_en_num_str(val_str))

col1, col2, col3 = st.columns([1,1,1])
with col1:
    num_customers = formatted_number_input("👥 تعداد مشتریان", key="num_customers_input")
with col2:
    total_income = formatted_number_input("💵 کل درآمد (تومان)", key="total_income_input")
with col3:
    total_costs = formatted_number_input("💰 کل هزینه‌ها (تومان)", key="total_costs_input")


calc_col, pdf_col = st.columns([1, 1])

do_calc = calc_col.button("📊 محاسبه کن")
pdf_placeholder = pdf_col.empty()  # show PDF button after calculation

results_box = st.container()
charts_box = st.container()
footer_box = st.container()

if do_calc:
    # ---- Tax rules (Tomans) ----
    income_tax = 0.05 * total_income                     # ۵٪ از درآمد
    fee = 5000 * num_customers                           # ۵۰۰۰ تومان به ازای هر مشتری
    corporate_tax_base = total_income - (total_costs + income_tax + fee)
    corporate_tax = 0.25 * corporate_tax_base if corporate_tax_base > 0 else 0
    vat = 0.10 * total_income                            # ۱۰٪ از درآمد
    total_remaining = total_income - income_tax - fee - corporate_tax
    net_profit = total_income - (total_costs + income_tax + fee + corporate_tax)

    # ---- KPIs ----
    gross_profit = total_income - total_costs
    gross_margin = (gross_profit / total_income * 100) if total_income > 0 else 0
    net_margin = (net_profit / total_income * 100) if total_income > 0 else 0
    total_obligations = income_tax + fee + corporate_tax + vat
    tax_to_income = ((total_obligations - vat) / total_income * 100) if total_income > 0 else 0
    cost_to_income = (total_costs / total_income * 100) if total_income > 0 else 0
    profit_per_customer = (net_profit / num_customers) if num_customers > 0 else 0


    with results_box:
        st.header("📤 نتایج محاسبه")
        if business_name.strip():
            st.markdown(f"**🏷️ نام کسب‌وکار:** {business_name}")
        st.success("✅ محاسبه انجام شد! نتایج زیر را بررسی کنید.")

        # Metrics with smaller numbers
        col1, col2, col3, col4, col5 = st.columns(5)
        metrics = [
            ("سود خالص", net_profit),
            ("حاشیه سود خالص", net_margin),
            ("کل دریافت با ارزش افزوده", total_income + vat),
            ("کل پرداخت به صندوق شهر", total_obligations),
            ("مانده برای کسب‌و‌کار", total_remaining)
        ]

        for col, (label, value) in zip([col1, col2, col3, col4, col5], metrics):
            # Handle percentage display separately
            if label == "حاشیه سود خالص":
                persian_value = to_persian_number(value, decimals=0) + "٪"
            else:
                persian_value = to_persian_number(value, decimals=0)
            
            col.markdown(
                f"<div style='text-align:center;'>"
                f"<div style='font-size:18px; font-weight:700;'>{label}</div>"
                f"<div style='font-size:14px; color:#333;'>{persian_value}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

        st.subheader("جزئیات محاسبات")
        st.write(f"مجموع درآمد فروش کالا یا خدمات: {to_persian_number(total_income)} تومان")
        st.write(f"مالیات بر ارزش افزوده دریافتی از مشتری: {to_persian_number(vat)} تومان")
        st.write(f"**کل دریافت با ارزش افزوده:** {to_persian_number(total_income+vat)} تومان")
        st.write("")
        st.write(f"عوارض فعالیت اقتصادی (۵٪ از درآمد): {to_persian_number(income_tax)} تومان")
        st.write(f"کارمزد تراکنش (۵۰۰۰ تومان × تعداد مشتریان): {to_persian_number(fee)} تومان")
        st.write(f"مالیات بر سود (۲۵٪ از سود پس از هزینه و مالیات/کارمزد تراکنش): {to_persian_number(corporate_tax)} تومان")
        st.write(f"مالیات بر ارزش افزوده (۱۰٪ از درآمد): {to_persian_number(vat)} تومان")
        st.write(f"**مانده برای کسب‌و‌کار:** {to_persian_number(total_remaining)} تومان")
        st.write("")
        st.write(f"**مجموع هزینه تولید کالا یا خدمات:** {to_persian_number(total_costs)} تومان")
        st.write("")
        st.write(f"**سود خالص:** {to_persian_number(net_profit)} تومان")
        st.write(f"**حاشیه سود:** {to_persian_number(round(net_margin, 0), decimals=0)}٪")
        st.write("")
        st.write(f"**نسبت هزینه به درآمد:** {to_persian_number(round(cost_to_income, 0), decimals=0)}٪")
        st.write(f"**نسبت پرداخت به صندوق شهر به درآمد:** {to_persian_number(round(tax_to_income, 0), decimals=0)}٪")
        st.write(f"**سود به ازای هر مشتری:** {to_persian_number(profit_per_customer)} تومان")

        st.markdown(
            "<div class='pay-note'>"
            "🧾 <b>نحوه پرداخت الزامات مالی:</b><br>"
            f"لطفا مبلغ {to_persian_number(total_obligations)} تومان را به حساب مسئول بودجه <b>فرنام شهبا</b> به شماره کارت "
            "<b>۶۲۷۴۸۸۱۱۱۳۱۹۱۶۶۱</b> واریز بفرمایید و رسید واریز به همراه اظهارنامه مالی را به آی‌دی تلگرام "
            "<b>farnamshahba@</b> ارسال کنید."
            "</div>", unsafe_allow_html=True
        )

    # ---- Chart (kept colors) ----
    with charts_box:
        st.subheader("📊 نمودار توزیع درآمد")
        pie_data = {
            "نوع": ["عوارض فعالیت اقتصادی", "کارمزد تراکنش", "مالیات بر سود", "هزینه کسب و کار", "سود خالص"],
            "مقدار": [income_tax, fee, corporate_tax, total_costs, net_profit]
        }
        colors_palette = ["#D89128","#F89602", "#FFB74D", "#E57373", "#4DB6AC"]  # kept palette
        fig_pie = px.pie(
            pie_data, names="نوع", values="مقدار",
            title=False, hole=0.4, color="نوع", color_discrete_sequence=colors_palette
        )
        fig_pie.update_traces(textinfo="label+percent", textfont_size=14)
        st.plotly_chart(fig_pie, use_container_width=True)

    # ---- PDF generation ----
    def shape_rtl(text):
        if not text:
            return text
        if HAS_RTL_LIBS:
            return get_display(arabic_reshaper.reshape(text))
        return text

    def get_persian_datetime_str():
        now = jdatetime.datetime.now()
        # HH:MM zero-padded
        hh = f"{now.hour:02d}"
        mm = f"{now.minute:02d}"
        return (
            f"{to_persian_number(now.year)}/"
            f"{to_persian_number(now.month)}/"
            f"{to_persian_number(now.day)} - "
            f"{to_persian_number(int(hh))}:{to_persian_number(int(mm))}"
        )

    def build_pdf_bytes():
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

        # Register Persian font
        font_name = "Vazirmatn"
        font_path = "Vazirmatn-Regular.ttf"
        bold_font_name = "Vazirmatn-Bold"
        bold_font_path = "Vazirmatn-Bold.ttf"
        try:
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                pdfmetrics.registerFont(TTFont(bold_font_name, bold_font_path))
            else:
                font_name = "Helvetica"
        except Exception:
            font_name = "Helvetica"

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=2*cm, leftMargin=2*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('title', parent=styles['Title'], fontName=font_name, fontSize=18, alignment=2)
        subtitle_style = ParagraphStyle('subtitle', parent=styles['Normal'], fontName=font_name, fontSize=12, alignment=2)
        normal_style = ParagraphStyle('normal', parent=styles['Normal'], fontName=font_name, fontSize=11, alignment=2)
        bold_normal_style = ParagraphStyle('normal', parent=styles['Normal'], fontName=bold_font_name, fontSize=12, alignment=2)

        elements = []

        # Logo
        elements.append(Paragraph(f"<b>{shape_rtl('کارگاه کیمیاگری ۹')}</b>", subtitle_style))
        elements.append(Spacer(1, 6))

        # Title
        elements.append(Paragraph(shape_rtl("گزارش مالی"), title_style))
        elements.append(Spacer(1, 10))

        # Business name (kept) + Persian date/time just below it
        if business_name.strip():
            elements.append(Paragraph(shape_rtl(f"نام کسب‌وکار: {business_name}"), normal_style))
        elements.append(Paragraph(shape_rtl(f"تاریخ و زمان تولید گزارش: {get_persian_datetime_str()}"), normal_style))
        elements.append(Spacer(1, 10))

        # Summary line
        summary = (
            f"تعداد مشتریان: {to_persian_number(num_customers)} | "
            f"کل درآمد: {to_persian_number(total_income)} تومان | "
            f"کل هزینه‌ها: {to_persian_number(total_costs)} تومان"
        )
        elements.append(Paragraph(shape_rtl(summary), normal_style))
        elements.append(Spacer(1, 10))

        # Results table (kept)
        rows = [
            [shape_rtl("مبلغ/درصد"), shape_rtl("عنوان")],
            [f"{to_persian_number(total_income)}", shape_rtl("مجموع درآمد فروش کالا یا خدمات (تومان)")],
            [f"{to_persian_number(vat)}", shape_rtl("مالیات بر ارزش افزوده دریافتی از مشتری (تومان)")],
            [f"{to_persian_number(total_income+vat)}", shape_rtl("کل دریافت با ارزش افزوده (تومان)")],
            [f"{to_persian_number(income_tax)}", shape_rtl("عوارض فعالیت اقتصادی (۵٪) (تومان)")],
            [f"{to_persian_number(fee)}", shape_rtl("کارمزد تراکنش (۵۰۰۰ تومان × تعداد مشتریان) (تومان)")],
            [f"{to_persian_number(corporate_tax)}", shape_rtl("مالیات بر سود (۲۵٪) (تومان)")],
            [f"{to_persian_number(vat)}", shape_rtl("مالیات بر ارزش افزوده (۱۰٪ از درآمد) (تومان)")],
            [f"{to_persian_number(total_remaining)}", shape_rtl("مانده برای کسب‌و‌کار (تومان)")],
            [f"{to_persian_number(total_costs)}", shape_rtl("مجموع هزینه تولید کالا یا خدمات (تومان)")],
            [f"{to_persian_number(net_profit)}", shape_rtl("سود خالص (تومان)")],
            [f"{to_persian_number(net_margin)}", shape_rtl("حاشیه سود (%)")],
            [f"{to_persian_number(cost_to_income)}", shape_rtl("نسبت هزینه به درآمد (%)")],
            [f"{to_persian_number(tax_to_income)}", shape_rtl("نسبت پرداخت به صندوق شهر به درآمد (%)")],
            [f"{to_persian_number(profit_per_customer)}", shape_rtl("سود به ازای هر مشتری (تومان)")],
        ]

        table = Table(rows, colWidths=[6*cm, 8*cm])
        table.setStyle(TableStyle([
            ('FONT', (0,0), (-1,-1), font_name, 10),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f7f7f7")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#333333")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.whitesmoke, colors.HexColor("#fcfcfc")]),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))


        # Payment note (kept)
        pay_text = (
            "واریز بفرمایید و رسید واریز به همراه فایل اظهار‌نامه مالی را به آی‌دی تلگرام farnamshahba@ ارسال کنید."
            f"لطفا مبلغ {to_persian_number(total_obligations)} را به حساب مسئول بودجه فرنام شهبا به شماره کارت ۶۲۷۴۸۸۱۱۱۳۱۹۱۶۶۱"
        )
        elements.append(Paragraph(shape_rtl(pay_text), normal_style))

        # Final note (kept)
        elements.append(Spacer(1, 8))
        note = "این گزارش توسط مسئول بودجه، جهت استفاده کلیه مسئولین شهر کیمیاگری ۹ تهیه شده است."
        elements.append(Paragraph(shape_rtl(note), normal_style))

        elements.append(Spacer(1, 8))
        note = "🦸‍♀️🦸‍♂️ تو قهرمان ارزشمند زندگی خودت هستی."
        elements.append(Paragraph(shape_rtl(note), bold_normal_style))

        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    pdf_bytes = build_pdf_bytes()
    pdf_placeholder.download_button(
        label="📄 دانلود گزارش PDF",
        data=pdf_bytes,
        file_name=f"financial_requirements_report_{business_name}.pdf",
        mime="application/pdf"
    )

# ---- Footer (kept EXACTLY) ----
with footer_box:
    st.markdown(
        "<p class='footer-note'>🦸‍♀️🦸‍♂️ تو قهرمان ارزشمند زندگی خودت هستی.</p>",
        unsafe_allow_html=True
    )
