import base64
import json
from openai import OpenAI
from pathlib import Path
from PIL import Image
import pillow_heif
import io


def merge_negative_items(data):
    """
    检查并合并 items 中 amount 为负的项。
    若 item 的 amount < 0，则将该项的 amount 与 tax 加到上一个 item，
    并从列表中删除该项。
    """
    items = data.get("items", [])
    if not items:
        return data

    i = 1
    while i < len(items):
        item = items[i]
        if item.get("amount", 0) < 0:
            prev_item = items[i - 1]
            # 合并金额与税额
            prev_item["amount"] = round(prev_item.get("amount", 0) + item.get("amount", 0), 2)
            prev_item["tax"] = round(prev_item.get("tax", 0) + item.get("tax", 0), 2)
            # 删除该负数项
            del items[i]
            # 删除后不递增 i，因为列表变短了
        else:
            i += 1

    # 更新原数据
    data["items"] = items
    return data



def fix_invoice_number(data):
    invoice_number = data.get("invoice_number", "")
    
    # 如果不是字符串，先转成字符串
    invoice_number = str(invoice_number)
    
    if len(invoice_number) == 20:
        return data  # 长度正确，无需处理
    
    if len(invoice_number) == 8:
        return data  # 长度正确，无需处理

    # 长度不为20，打印警告
    print(f"⚠️ invoice_number 长度为 {len(invoice_number)}/20，尝试自动修正。")
    
    # 找出最长的一串连续的'0'
    import re
    zeros = list(re.finditer(r"0{4,}", invoice_number))
    
    if not zeros:
        # 没有连续四个及以上的0，则简单补或截断
        print("❌ 无法自动修正该发票代码，请手动修正")
    else:
        # 找出最长的一段连续0
        longest_zero_seq = max(zeros, key=lambda m: len(m.group(0)))
        start, end = longest_zero_seq.span()
        zero_len = end - start
        new_invoice_number = list(invoice_number)
        
        diff = 20 - len(invoice_number)
        
        if diff > 0:
            # 长度不足 -> 在该段中增加diff个0
            new_zeros = "0" * (zero_len + diff)
        else:
            # 长度过长 -> 在该段中减少|diff|个0（但最少保留一个0）
            new_len = max(1, zero_len + diff)
            new_zeros = "0" * new_len
        
        # 拼接
        invoice_number = (
            invoice_number[:start] +
            new_zeros +
            invoice_number[end:]
        )

    
    # 更新回原 data
    data["invoice_number"] = invoice_number
    return data

def convert_to_jpg(image_path: str) -> bytes:
    """将各种图片（尤其是HEIC）统一转换为JPEG格式并返回字节流"""
    suffix = Path(image_path).suffix.lower()
    if suffix in [".heic", ".heif"]:
        heif_file = pillow_heif.read_heif(image_path)
        image = Image.frombytes(
            heif_file.mode, heif_file.size, heif_file.data, "raw"
        )
    else:
        image = Image.open(image_path)

    with io.BytesIO() as output:
        image.convert("RGB").save(output, format="JPEG", quality=90)
        return output.getvalue()


def extract_invoice_info(image_path, api_key, base_url, model_name):
    """调用AI读取发票信息并返回JSON"""
    client = OpenAI(api_key=api_key, base_url=base_url)

    image_bytes = convert_to_jpg(image_path)
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    prompt = """
你是一名专业的发票识别助手。请从发票图片中读取以下信息并以严格JSON格式输出,发票上含有几个信息就加入几个items（金额为负数保留，并把"name"项设为null），最多取前五个：
{
  "supplier": "供货厂家（开票公司名称）",
  "invoice_number": "发票号码（一般20位，请自查）",
  "purchase_date": "YYYY年M月D日（发票日期）",
  "entry_date": "YYYY年M月D日（与发票日期相同）",
  "price": "所有物品的总价，一般在发票的右下区域内的数字",
  "price_uppercase": "price金额的汉语大写，如壹佰贰拾元整"
  "items": [
    {
      "name": "材料/易耗品名称1（不超过8个字，如有品牌则输出: 品牌+是什么，如"得力胶带"，没有品牌则输出： 是什么，如"电子模块"）",
      "model": "规格型号(不超8字，超过部分截去，如“单模跳线1560nm FC/PC-FC/PC SMF-28e 光纤”，保留“单模跳线1560nm”即可)",
      "unit": "单位",
      "quantity": 数量(数字),
      "amount": 不含税金额(数字),
      "tax": 税额(数字)
    }
  ]
}
不要输出额外说明或解释。
"""

    print("✅已发请求给ai，等待ai处理")

    for i in range(3):
        try:
            response = client.chat.completions.create(
                model=model_name,  
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                            },
                        ],
                    }
                ]
            )
        except:
            print("ai无响应，或许是服务器过于繁忙或配置错误")
            print("❌ 第{}/3次尝试失败，正在重新尝试".format(i+1))
            continue


        content = response.choices[0].message.content.strip()

        # 🧹 清理markdown包裹符号
        if content.startswith("```"):
            content = content.strip("`")
            if content.lower().startswith("json"):
                content = content[4:].strip()

        try:
            data = json.loads(content)
            print("✅AI返回数据解析成功")
            break
        except json.JSONDecodeError:
            print("⚠️ JSON解析失败，AI返回原文如下：")
            print("❌ 第{}/3次尝试失败，正在重新尝试".format(i+1))
            print(content)
            raise
    
    fix_invoice_number(data)
    merge_negative_items(data)
    # ✅ 逻辑1：只保留前二条，多余项压缩成“详见发票”
    items = data.get("items", [])
    if len(items) > 2:
        items = items[:2] + [{"name": "详见发票", "model": "", "unit": "", "quantity": "", "amount": "", "tax": ""}]
        data["items"] = items

    # ✅ 逻辑2：计算单价
    for item in data["items"]:
        try:
            if item.get("name") == "详见发票":
                item["unit_price"] = None
                continue
            q = float(item["quantity"]) if float(item["quantity"]) != 0 else 1
            total = float(item["amount"]) + float(item["tax"])
            item["unit_price"] = round(total / q, 2)
        except Exception:
            item["unit_price"] = None

    return data


if __name__ == "__main__":
    image_path = Path("测试图片.jpg")
    if not image_path.exists():
        raise FileNotFoundError("请把发票图片放在同目录下并命名为 测试图片.jpg")

    result = extract_invoice_info(str(image_path))
    print(json.dumps(result, ensure_ascii=False, indent=2))
