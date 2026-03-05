# 🧾 南京大学出库单生成器 (AutoInvoice)

[![Build and Release App](https://github.com/liweihan389/NJU_AutoInvoice/actions/workflows/build.yml/badge.svg)](https://github.com/liweihan389/NJU_AutoInvoice/actions/workflows/build.yml)
[![Release](https://img.shields.io/github/v/release/liweihan389/NJU_AutoInvoice)](https://github.com/liweihan389/NJU_AutoInvoice/releases)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey)](#)

作为科研打工人，每次报销处理经费都需要手动对着发票核对明细、敲击键盘填写出库单，既枯燥又容易出错。
**南京大学出库单生成器** 是一款基于大语言模型（视觉能力）开发的本地桌面效率工具。它可以自动读取发票 PDF，提取核心信息并精准填入指定的出库单模板中，实现报销做账的全自动化。

---

## 📸 界面预览

<img width="651" height="629" alt="截屏2026-03-05 下午9 35 31" src="https://github.com/user-attachments/assets/7cdcfeab-fc28-4579-826a-0425bf396b2e" />
---

## 📖 详细使用说明 (保姆级教程)

只需简单 6 步，即可完成全自动发票处理：

**1. 发票物理分类**
在开始扫描前，请先将手中的纸质发票/电子发票打印件，严格按照 **经费号** 进行分类归拢。


**2. 扫描并规范命名**
将分类好的发票进行扫描（推荐使用汉王扫描王）。**注意：同一个经费号下的所有发票，请扫描/合并到同一个 PDF 文件中**。
扫描完成后，必须将该 PDF 文件重命名为对应的经费号（例如：`0201-12345678.pdf`）。程序会自动抓取文件名作为后续填表的经费号。

**3. 集中存放**
在电脑上新建一个文件夹（例如命名为 `文件夹1` 或 `待处理发票`），将上一步扫描并命名好的所有 PDF 文件全部放进这个文件夹中。

**4. 启动程序与 API 配置**
双击打开本软件，在界面顶部的 **“API 配置”** 区域填入大模型调用信息（配置会自动保存在本地，下次打开无需重填）：
* **API Key**：填写你获取的大模型密钥。
* **Base URL**：填写对应的 API 接口地址（如使用国内代理或自建网关，请在此修改，默认兼容 OpenAI 接口格式）。
* **Model**：填写你要调用的视觉模型名称（推荐使用识别能力强的多模态模型，如 `gemini-2.5-flash` 等）。

**5. 选择工作路径**
* **发票文件夹**：点击浏览，选择你在第 3 步中创建的 `文件夹1`。
* **出库单模板 PDF**：保持默认即可（程序自带标准模板），一般无需修改。

**6. 一键生成**
点击底部的 **“🚀 开始处理”** 按钮。程序会自动运转并在日志区显示进度。处理完成后，你会在 `文件夹1` 的同级目录下，找到一个名为 **`最终合并出库单.pdf`** 的文件。打开它，你会发现所有经费号下的每一张发票，都已经各自生成了一张出库单，并合并在了一起！

---

## 🧠 核心实现思路

本工具的底层逻辑采用“流水线式”的自动化处理架构，核心分为四大模块：

1.  **PDF 逐页拆解与渲染 (PyMuPDF)**
    程序遍历目标文件夹下的所有 PDF。由于一个 PDF 内可能包含同一经费号下的多张发票，程序使用 `PyMuPDF (fitz)` 引擎将 PDF 逐页拆解，并按照 300 DPI 的高分辨率将每一页独立渲染为 JPEG 图像，确保 **“一页发票对应一张后续的出库单”**。
2.  **AI 视觉结构化提取 (VLM Prompt Engineering)**
    利用 `base64` 编码将发票图像发送给多模态大模型。通过严谨的 Prompt 设定，要求 AI 必须返回严格的 JSON 格式数据。程序内部会自动处理 AI 返回的复杂情况，例如：
    * **负数合并逻辑**：自动检测 `amount < 0` 的明细项（如折扣或退款），将其金额与税额合并至上一条商品中，确保账面逻辑清晰。
    * **冗余信息截断**：长超规格型号自动截去尾部，保持表格排版整洁。
3.  **PDF 坐标级精准填表 (ReportLab)**
    使用 `reportlab` 库并在内存中注册 `STSong-Light`（宋体）中文字体。程序根据预先校准的绝对坐标（X,Y points），将 AI 提取出的 JSON 数据（供货厂家、日期、总价大写、明细列表等）以及从文件名中提取的“经费号”，精准“画”在非标准 A4 尺寸的出库单空白模板之上。
    * *排版优化*：若发票明细超过 2 条，程序会自动触发压缩机制，将多余条目合并为“详见发票”字样，防止表格溢出。
4.  **临时文件回收与终卷合并 (PyPDF2)**
    所有的单张出库单会在底层的 `temp` 目录中生成临时 PDF。全部处理完毕后，通过 `PyPDF2` 的 `PdfMerger` 模块将成百上千张单页 PDF 无缝拼接为一个单一的 `最终合并出库单.pdf` 文件，并在结束后自动执行垃圾回收，清空临时文件夹。

---

## 🚀 下载与安装

进入项目的 [**Releases 页面**](https://github.com/liweihan389/NJU_AutoInvoice/releases)，下载最新版本的安装包：

* **Windows 用户**：下载 `AutoInvoice_Windows.exe`，免安装直接双击运行。
* **macOS 用户**：下载 `AutoInvoice_macOS.dmg`，双击打开后，将软件拖入 `Applications` 文件夹即可。
    > **⚠️ macOS 首次打开提示“无法验证开发者”怎么办？**
    > 请在“应用程序”文件夹中找到该软件，**右键点击图标 -> 选择“打开”**，在弹出的提示框中再次点击“打开”即可永久放行。

## 👨‍💻 二次开发

```bash
# 1. 克隆代码
git clone [https://github.com/liweihan389/NJU_AutoInvoice.git](https://github.com/liweihan389/NJU_AutoInvoice.git)
cd NJU_AutoInvoice

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行程序
python app.py
