# -*- coding: utf-8 -*-
import io
import os
import streamlit as st
import plotly.express as px

# ماژول‌های اختیاری برای رندر فارسی در PDF
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_RTL_LIBS = True
except Exception:
    HAS_RTL_LIBS = False

# ---- تبدیل عدد به رقم فارسی + جداکننده هزار ----
PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
def to_persian_number(num, decimals=0):
    """
    num: عدد
    decimals: تعداد اعشار برای نمایش (پیش‌فرض 0 برای تومان)
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

# ---- تنظیمات صفحه ----
st.set_page_config(page_title="الزامات مالی - ماشین‌حساب", page_icon="💰", layout="centered")

# ---- استایل RTL ----
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

# ---- عنوان و "لوگو" ----
st.markdown("<div class='kimiya-note'>کارگاه کیمیاگری 9</div>", unsafe_allow_html=True)
st.markdown("<h1 style='text-align:center;'>الزامات مالی</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;'>محاسبه‌گر انواع الزامات مالی، مالیات‌ها، سود و شاخص‌های ساده کسب‌وکار</p>", unsafe_allow_html=True)

# ---- ورودی‌ها ----
st.header("📥 ورود اطلاعات")
col1, col2, col3 = st.columns([1,1,1])
with col1:
    num_customers = st.number_input("👥 تعداد مشتریان", min_value=0, value=0, step=1)
with col2:
    total_income = st.number_input("💵 کل درآمد (تومان)", min_value=0.0, value=0.0, step=100000.0, format="%.0f")
with col3:
    total_costs = st.number_input("💰 کل هزینه‌ها (تومان)", min_value=0.0, value=0.0, step=100000.0, format="%.0f")

calc_col, pdf_col = st.columns([1,1])
do_calc = calc_col.button("📊 محاسبه کن")
pdf_placeholder = pdf_col.empty()  # دکمه PDF بعد از محاسبه نمایان می‌شود

results_box = st.container()
charts_box = st.container()
footer_box = st.container()

if do_calc:
    # ---- قوانین مالیاتی (همه بر حسب تومان) ----
    income_tax = 0.05 * total_income                     # ۵٪ از درآمد
    fee = 5000 * num_customers                           # ۵۰۰۰ تومان به ازای هر مشتری
    corporate_tax_base = total_income - (total_costs + income_tax + fee)
    corporate_tax = 0.25 * corporate_tax_base if corporate_tax_base > 0 else 0
    vat = 0.10 * total_income                             # ۱۰٪ از درآمد
    net_profit = total_income - (total_costs + income_tax + fee + corporate_tax)

    # ---- شاخص‌های کسب‌وکار ----
    gross_profit = total_income - total_costs
    gross_margin = (gross_profit / total_income * 100) if total_income > 0 else 0
    net_margin = (net_profit / total_income * 100) if total_income > 0 else 0
    total_obligations = income_tax + fee + corporate_tax + vat
    tax_to_income = ((total_obligations - vat) / total_income * 100) if total_income > 0 else 0
    cost_to_income = (total_costs / total_income * 100) if total_income > 0 else 0
    profit_per_customer = (net_profit / num_customers) if num_customers > 0 else 0

    with results_box:
        st.header("📤 نتایج محاسبه")
        st.success("✅ محاسبه انجام شد! نتایج زیر را بررسی کنید.")

        # متریک‌های کلیدی
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("سود خالص (تومان)", f"{to_persian_number(net_profit)}")
        m2.metric("حاشیه سود خالص", f"{to_persian_number(round(net_margin, 1), decimals=1)}٪")
        m3.metric("کل پرداختی‌ها (تومان)", f"{to_persian_number(total_obligations)}")
        m4.metric("سهم پرداختی‌ها از درآمد", f"{to_persian_number(round(tax_to_income, 1), decimals=1)}٪")

        st.subheader("جزئیات محاسبات")
        st.write(f"**عوارض فعالیت اقتصادی (۵٪ از درآمد):** {to_persian_number(income_tax)} تومان")
        st.write(f"**کارمزد تراکنش (۵۰۰۰ تومان × تعداد مشتریان):** {to_persian_number(fee)} تومان")
        st.write(f"**مالیات بر سود (۲۵٪ از سود پس از هزینه و مالیات/کارمزد تراکنش):** {to_persian_number(corporate_tax)} تومان")
        st.write(f"**مالیات بر ارزش افزوده (۱۰٪ از درآمد):** {to_persian_number(vat)} تومان")
        st.write(f"**سود ناخالص:** {to_persian_number(gross_profit)} تومان")
        st.write(f"**حاشیه سود ناخالص:** {to_persian_number(round(gross_margin, 1), decimals=1)}٪")
        st.write(f"**سود خالص:** {to_persian_number(net_profit)} تومان")
        st.write(f"**نسبت هزینه به درآمد:** {to_persian_number(round(cost_to_income, 1), decimals=1)}٪")
        st.write(f"**سود به ازای هر مشتری:** {to_persian_number(profit_per_customer)} تومان")

        st.subheader("📑 جدول خلاصه")
        st.table({
            "عنوان": [
                "تعداد مشتریان", "کل درآمد (تومان)", "کل هزینه‌ها (تومان)",
                "عوارض فعالیت اقتصادی", "کارمزد تراکنش", "مالیات بر سود", "مالیات بر ارزش افزوده",
                "سود ناخالص", "حاشیه سود ناخالص (%)",
                "سود خالص", "حاشیه سود خالص (%)",
                "کل پرداختی‌ها", "سهم پرداختی‌ها از درآمد (%)",
                "نسبت هزینه به درآمد (%)", "سود به ازای هر مشتری (تومان)"
            ],
            "مبلغ/درصد": [
                to_persian_number(num_customers),
                to_persian_number(total_income),
                to_persian_number(total_costs),
                to_persian_number(income_tax),
                to_persian_number(fee),
                to_persian_number(corporate_tax),
                to_persian_number(vat),
                to_persian_number(gross_profit),
                to_persian_number(round(gross_margin, 1), decimals=1),
                to_persian_number(net_profit),
                to_persian_number(round(net_margin, 1), decimals=1),
                to_persian_number(total_obligations),
                to_persian_number(round(tax_to_income, 1), decimals=1),
                to_persian_number(round(cost_to_income, 1), decimals=1),
                to_persian_number(profit_per_customer),
            ]
        })

        st.markdown(
            "<div class='pay-note'>"
            "🧾 <b>نحوه پرداخت الزامات مالی:</b><br>"
            "مبلغ الزامات مالی را به حساب مسئول بودجه <b>فرنام شهبا</b> به شماره کارت "
            "<b>۶۲۷۴-۸۸۱۱-۱۳۱۹-۱۶۶۱</b> واریز بفرمایید و رسید واریز به همراه فایل محاسبه‌شده را به آی‌دی تلگرام "
            "<b>@farnamshahba</b> ارسال کنید."
            "</div>", unsafe_allow_html=True
        )

    # ---- نمودارها ----
    with charts_box:
        st.subheader("📊 نمودار توزیع پرداخت‌ها")
        pie_data = {
            "نوع": ["عوارض فعالیت اقتصادی", "کارمزد تراکنش", "مالیات بر سود", "مالیات بر ارزش افزوده"],
            "مقدار": [income_tax, fee, corporate_tax, vat]
        }
        colors = ["#FFB74D", "#4DB6AC", "#E57373", "#64B5F6"]  # رنگ‌های ثابت
        fig_pie = px.pie(
            pie_data, names="نوع", values="مقدار",
            title="سهم هر بخش از کل پرداخت‌ها",
            hole=0.4, color="نوع", color_discrete_sequence=colors
        )
        fig_pie.update_traces(textinfo="label+percent", textfont_size=14)
        st.plotly_chart(fig_pie, use_container_width=True)

        st.subheader("📈 مقایسه سود و تعهدات")
        bar_data = {
            "شاخص": ["سود ناخالص", "سود خالص", "کل پرداختی‌ها"],
            "مقدار": [gross_profit, net_profit, total_obligations],
        }
        # برچسب‌های فارسیِ قالب‌بندی‌شده به‌عنوان text
        bar_text = [
            to_persian_number(gross_profit) + " تومان",
            to_persian_number(net_profit) + " تومان",
            to_persian_number(total_obligations) + " تومان",
        ]
        fig_bar = px.bar(
            bar_data, x="شاخص", y="مقدار",
            title="مقایسه سود ناخالص، سود خالص و کل پرداختی‌ها (تومان)",
            text=bar_text, color="شاخص",
            color_discrete_sequence=["#81C784", "#4DB6AC", "#E57373"]
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(yaxis_title="تومان", xaxis_title="", uniformtext_minsize=12, uniformtext_mode='show')
        st.plotly_chart(fig_bar, use_container_width=True)

    # ---- تولید PDF رسمی ----
    def shape_rtl(text):
        if not text:
            return text
        if HAS_RTL_LIBS:
            return get_display(arabic_reshaper.reshape(text))
        return text

    def build_pdf_bytes():
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

        # ثبت فونت فارسی در صورت وجود
        font_name = "Vazirmatn"
        font_path = "Vazirmatn-Regular.ttf"
        try:
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont(font_name, font_path))
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

        elements = []

        # "لوگو" (یادداشت فانتزی)
        elements.append(Paragraph(f"<b>{shape_rtl('کارگاه کیمیاگری 9')}</b>", subtitle_style))
        elements.append(Spacer(1, 6))

        # تیتر
        elements.append(Paragraph(shape_rtl("الزامات مالی"), title_style))
        elements.append(Spacer(1, 10))

        # خلاصه ورودی‌ها
        summary = (
            f"تعداد مشتریان: {to_persian_number(num_customers)} | "
            f"کل درآمد: {to_persian_number(total_income)} تومان | "
            f"کل هزینه‌ها: {to_persian_number(total_costs)} تومان"
        )
        elements.append(Paragraph(shape_rtl(summary), normal_style))
        elements.append(Spacer(1, 8))

        # جدول نتایج
        rows = [
            [shape_rtl("عنوان"), shape_rtl("مبلغ/درصد")],
            [shape_rtl("عوارض فعالیت اقتصادی  (۵٪)"), f"{to_persian_number(income_tax)} تومان"],
            [shape_rtl("کارمزد تراکنش (۵۰۰۰ تومان × مشتری)"), f"{to_persian_number(fee)} تومان"],
            [shape_rtl("مالیات بر سود (۲۵٪)"), f"{to_persian_number(corporate_tax)} تومان"],
            [shape_rtl("مالیات بر ارزش افزوده (۱۰٪)"), f"{to_persian_number(vat)} تومان"],
            [shape_rtl("سود ناخالص"), f"{to_persian_number(gross_profit)} تومان"],
            [shape_rtl("حاشیه سود ناخالص (%)"), f"{to_persian_number(round(gross_margin,1), decimals=1)}٪"],
            [shape_rtl("سود خالص"), f"{to_persian_number(net_profit)} تومان"],
            [shape_rtl("حاشیه سود خالص (%)"), f"{to_persian_number(round(net_margin,1), decimals=1)}٪"],
            [shape_rtl("کل پرداختی‌ها"), f"{to_persian_number(total_obligations)} تومان"],
            [shape_rtl("سهم پرداختی‌ها از درآمد (%)"), f"{to_persian_number(round(tax_to_income,1), decimals=1)}٪"],
            [shape_rtl("نسبت هزینه به درآمد (%)"), f"{to_persian_number(round(cost_to_income,1), decimals=1)}٪"],
            [shape_rtl("سود به ازای هر مشتری"), f"{to_persian_number(profit_per_customer)} تومان"],
        ]

        from reportlab.platypus import Table
        table = Table(rows, colWidths=[8*cm, 6*cm])
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
        elements.append(Spacer(1, 10))

        # یادداشت پرداخت
        pay_text = (
            "مبلغ الزامات مالی را به حساب مسئول بودجه فرنام شهبا به شماره کارت ۶۲۷۴۸۸۱۱۱۳۱۹۱۶۶۱ "
            "واریز بفرمایید و رسید واریز به همراه فایل محاسبه شده را به آی‌دی تلگرام @farnamshahba ارسال کنید."
        )
        elements.append(Paragraph(shape_rtl(pay_text), normal_style))

        # یادداشت پایانی
        elements.append(Spacer(1, 8))
        note = "این گزارش توسط مسئول بودجه، جهت اطلاع مسئولین کارگاه کیمیاگری 9 تهیه شده است."
        elements.append(Paragraph(shape_rtl(note), normal_style))

        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    pdf_bytes = build_pdf_bytes()
    pdf_placeholder.download_button(
        label="📄 دانلود گزارش PDF",
        data=pdf_bytes,
        file_name="financial_requirements_report.pdf",
        mime="application/pdf"
    )

with footer_box:
    st.markdown(
        "<p class='footer-note'>🦸‍♀️🦸‍♂️ تو قهرمان ارزشمند زندگی خودت هستی.</p>",
        unsafe_allow_html=True
    )
