from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.units import cm
from io import BytesIO
import json
from pathlib import Path

def fill_pdf(template_path, output_path, data, Grant_no):
    """
    在非标准A4模板上填写中文内容（宋体）
    模板尺寸：29.698cm × 20.995cm
    """

    # 🧭 页面尺寸（points）
    PAGE_WIDTH = 29.698 * cm   # ≈ 842 points
    PAGE_HEIGHT = 20.995 * cm  # ≈ 595 points

    # 注册简体中文宋体
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

    # 创建写入层
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    c.setFont("STSong-Light", 12)

    # ========== 示例坐标部分 ==========
    # 你可以用 pdf_coord_picker.py 校准这些点
    c.drawString(218, 514, "南京大学")
    c.drawString(460, 514, Grant_no)
    c.drawString(171, 490, data.get("supplier", ""))        # 供货厂家
    c.drawString(450, 488, data.get("invoice_number", ""))  # 发票号码
    c.drawString(172, 465, data.get("purchase_date", ""))   # 购置日期
    c.drawString(450, 465, data.get("entry_date", ""))      # 入库日期
    c.drawString(161, 95, data.get("price_uppercase", ""))      # 大写总价
    c.drawString(585, 95, str(data.get("price", "")))      # 总价


    # 材料列表，从 y=440 开始，每行间隔 26 points
    start_y = 412
    for i, item in enumerate(data.get("items", [])):
        if i >= 12:
            break
        y = start_y - i * 26
        c.drawString(160, y, item.get("name", ""))
        try:
            c.drawString(291, y, item.get("model", ""))
        except:
            c.drawString(291, y, "") 
        try:
            c.drawString(395, y, item.get("unit", ""))
        except:
            c.drawString(291, y, "") 
        c.drawString(456, y, str(item.get("quantity", "")))
        if item.get("unit_price"):
            c.drawString(524, y, str(item.get("unit_price", "")))
            try:
                amt = float(item.get("amount", 0)) + float(item.get("tax", 0))
                c.drawString(597, y, f"{amt:.2f}")
            except Exception:
                c.drawString(597, y, "")

    # 结束绘制
    c.save()
    packet.seek(0)

    # 读取模板PDF并叠加
    new_pdf = PdfReader(packet)
    template_pdf = PdfReader(open(template_path, "rb"))
    output = PdfWriter()

    page = template_pdf.pages[0]
    page.merge_page(new_pdf.pages[0])
    output.add_page(page)

    #写第二页
    # 创建写入层
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    c.setFont("STSong-Light", 10.5)

    # ========== 示例坐标部分 ==========
    # 你可以用 pdf_coord_picker.py 校准这些点
    c.drawString(203, 542, "南京大学")
    c.drawString(441, 542, Grant_no)
    c.drawString(162, 526, data.get("supplier", ""))        # 供货厂家
    c.drawString(162, 509, data.get("invoice_number", ""))  # 发票号码
    c.drawString(445, 509, data.get("purchase_date", ""))   # 购置日期
    c.drawString(598, 509, data.get("entry_date", ""))      # 入库日期
    c.drawString(161, 341, data.get("price_uppercase", ""))      # 大写总价
    c.drawString(585, 340, str(data.get("price", "")))      # 总价    

    # 材料列表，从 y=440 开始，每行间隔 26 points
    start_y = 474
    for i, item in enumerate(data.get("items", [])):
        if i >= 12:
            break
        y = start_y - i * 17
        c.drawString(160, y, item.get("name", ""))
        try:
            c.drawString(291, y, item.get("model", ""))
        except:
            c.drawString(291, y, "") 
        try:
            c.drawString(395, y, item.get("unit", ""))
        except:
            c.drawString(291, y, "") 
        c.drawString(456, y, str(item.get("quantity", "")))
        if item.get("unit_price"):
            c.drawString(524, y, str(item.get("unit_price", "")))
            try:
                amt = float(item.get("amount", 0)) + float(item.get("tax", 0))
                c.drawString(597, y, f"{amt:.2f}")
            except Exception:
                c.drawString(597, y, "")

    # 你可以用 pdf_coord_picker.py 校准这些点
    c.drawString(203, 261, "南京大学")
    c.drawString(441, 261, Grant_no)
    c.drawString(162, 243, data.get("supplier", ""))        # 供货厂家
    c.drawString(162, 227, data.get("invoice_number", ""))  # 发票号码
    c.drawString(445, 227, data.get("purchase_date", ""))   # 购置日期
    c.drawString(598, 227, data.get("entry_date", ""))      # 入库日期
    c.drawString(161, 59.5, data.get("price_uppercase", ""))      # 大写总价
    c.drawString(585, 59, str(data.get("price", "")))      # 总价
    

    # 材料列表，从 y=440 开始，每行间隔 26 points
    start_y = 193
    for i, item in enumerate(data.get("items", [])):
        if i >= 12:
            break
        y = start_y - i * 17
        c.drawString(160, y, item.get("name", ""))
        try:
            c.drawString(291, y, item.get("model", ""))
        except:
            c.drawString(291, y, "") 
        try:
            c.drawString(395, y, item.get("unit", ""))
        except:
            c.drawString(291, y, "") 
        c.drawString(456, y, str(item.get("quantity", "")))
        if item.get("unit_price"):
            c.drawString(524, y, str(item.get("unit_price", "")))
            try:
                amt = float(item.get("amount", 0)) + float(item.get("tax", 0))
                c.drawString(597, y, f"{amt:.2f}")
            except Exception:
                c.drawString(597, y, "")

    # 结束绘制
    c.save()
    packet.seek(0)

    # 读取模板PDF并叠加
    new_pdf = PdfReader(packet)
    template_pdf = PdfReader(open(template_path, "rb"))

    page = template_pdf.pages[1]
    page.merge_page(new_pdf.pages[0])
    output.add_page(page)

    with open(output_path, "wb") as f:
        output.write(f)

    print(f"✅ 已生成: {output_path}")


if __name__ == "__main__":
    # 从 JSON 读取发票识别结果
    with open("invoice_result.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    template_path = "模板.pdf"      # 你转好的 PDF 模板
    output_path = "出库单1.pdf"

    fill_pdf(template_path, output_path, data, "111")
