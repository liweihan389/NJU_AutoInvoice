import sys
import os
import json
import shutil
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                               QFileDialog, QTextEdit, QProgressBar, QMessageBox,
                               QGroupBox, QFormLayout)
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QIcon

# 导入你的核心业务逻辑
import fitz
from PyPDF2 import PdfMerger
from extract_invoice_info import extract_invoice_info
from fill_pdf import fill_pdf

APP_DATA_DIR = Path.home() / "Documents" / "智能出库单"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

# 然后把原来的配置文件和临时文件夹路径改掉：
CONFIG_FILE = APP_DATA_DIR / "app_config.json"

# ==========================================
# 1. 异步任务层 (Worker Thread)
# ==========================================

def resource_path(relative_path):
    """ 获取资源的绝对路径，兼容开发环境和 PyInstaller 打包环境 """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class InvoiceWorker(QThread):
    log_signal = Signal(str)       
    progress_signal = Signal(int)  
    finished_signal = Signal(bool) 

    def __init__(self, input_dir, template_path, output_file, api_key, base_url, model_name):
        super().__init__()
        self.input_dir = Path(input_dir)
        self.template_path = template_path
        self.output_file = output_file
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name

    def run(self):
        try:
            temp_dir = APP_DATA_DIR / "temp"
            temp_dir.mkdir(exist_ok=True)

            # 清空 temp 目录
            self.log_signal.emit("🧹 正在清理临时文件夹...")
            for root, dirs, files in os.walk(temp_dir):
                for f in files:
                    os.remove(os.path.join(root, f))

            pdf_files = sorted(self.input_dir.glob("*.pdf"))
            total_files = len(pdf_files)
            
            if total_files == 0:
                self.log_signal.emit("⚠️ 未在目录下找到任何发票 PDF 文件！")
                self.finished_signal.emit(False)
                return

            all_output_pdfs = []
            
            for index, pdf_file in enumerate(pdf_files, start=1):
                grant_no = pdf_file.stem
                self.log_signal.emit(f"\n📄 开始处理文件: {pdf_file.name} (经费号: {grant_no})")

                doc = fitz.open(pdf_file)
                self.log_signal.emit(f"  - 检测到 {len(doc)} 页发票")

                for i, page in enumerate(doc, start=1):
                    img_path = temp_dir / f"{grant_no}_page{i}.jpg"
                    
                    # 按照 300 DPI 的清晰度渲染图片 (300 / 72 默认 DPI = 4.16)
                    zoom = 300 / 72  
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat)
                    
                    # 保存为 JPEG
                    pix.save(str(img_path))

                    try:
                        self.log_signal.emit(f"  🤖 正在请求 AI 识别第 {i} 页...")
                        # 传入 API 配置
                        invoice_info = extract_invoice_info(str(img_path), self.api_key, self.base_url, self.model_name)
                        self.log_signal.emit("  ✅ AI 识别成功")
                    except Exception as e:
                        self.log_signal.emit(f"  ❌ AI 识别失败 ({pdf_file.name} 第{i}页): {str(e)}")
                        continue

                    output_pdf = temp_dir / f"出库单_{grant_no}_{i}.pdf"
                    try:
                        fill_pdf(self.template_path, str(output_pdf), invoice_info, grant_no)
                        all_output_pdfs.append(output_pdf)
                        self.log_signal.emit(f"  ✅ 已生成单页出库单: {output_pdf.name}")
                    except Exception as e:
                        self.log_signal.emit(f"  ❌ 填写模板失败: {str(e)}")

                # 更新主进度条
                progress = int((index / total_files) * 90) # 留 10% 给合并操作
                self.progress_signal.emit(progress)

            if all_output_pdfs:
                self.log_signal.emit(f"\n📦 正在合并所有出库单至: {self.output_file} ...")
                merger = PdfMerger()
                for pdf in all_output_pdfs:
                    merger.append(str(pdf))
                merger.write(self.output_file)
                merger.close()
                self.log_signal.emit(f"🎉 全部发票处理完毕！已保存至: {self.output_file}")
                self.progress_signal.emit(100)
                self.finished_signal.emit(True)
            else:
                self.log_signal.emit("⚠️ 任务结束，但未能生成任何出库单。")
                self.finished_signal.emit(False)

        except Exception as e:
            self.log_signal.emit(f"\n❌ 发生严重错误: {str(e)}")
            self.finished_signal.emit(False)


# ==========================================
# 2. 界面展现层 (UI Layer)
# ==========================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("智能发票出库单生成器")
        self.resize(650, 600)
        self.worker = None
        self.init_ui()
        self.load_config()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- 1. API 配置面板 ---
        api_group = QGroupBox("API 配置 (自动保存)")
        api_layout = QFormLayout()
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.PasswordEchoOnEdit) # 密码模式，保护隐私
        self.base_url_input = QLineEdit()
        self.model_input = QLineEdit()
        
        api_layout.addRow("API Key:", self.api_key_input)
        api_layout.addRow("Base URL:", self.base_url_input)
        api_layout.addRow("Model:", self.model_input)
        api_group.setLayout(api_layout)
        main_layout.addWidget(api_group)

        # --- 2. 路径选择区 ---
        path_group = QGroupBox("文件路径")
        path_layout = QVBoxLayout()

        dir_layout = QHBoxLayout()
        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("选择包含发票 PDF 的文件夹...")
        dir_btn = QPushButton("📁 发票文件夹路径浏览")
        dir_btn.clicked.connect(self.select_input_dir)
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(dir_btn)
        path_layout.addLayout(dir_layout)

        tpl_layout = QHBoxLayout()
        self.tpl_input = QLineEdit()
        self.tpl_input.setPlaceholderText("选择出库单模板 PDF...")
        default_template = resource_path("template.pdf")
        self.tpl_input.setText(default_template)
        tpl_btn = QPushButton("📄 出库单浏览")
        tpl_btn.clicked.connect(self.select_template_file)
        tpl_layout.addWidget(self.tpl_input)
        tpl_layout.addWidget(tpl_btn)
        path_layout.addLayout(tpl_layout)

        path_group.setLayout(path_layout)
        main_layout.addWidget(path_group)

        # --- 3. 日志显示区 ---
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("background-color: #f8f9fa; color: #333; font-family: monospace;")
        main_layout.addWidget(self.log_view)

        # --- 4. 进度与控制区 ---
        bottom_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        
        self.start_btn = QPushButton("🚀 开始处理")
        self.start_btn.setMinimumHeight(45)
        self.start_btn.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.start_btn.clicked.connect(self.start_processing)
        
        bottom_layout.addWidget(self.progress_bar)
        bottom_layout.addWidget(self.start_btn)
        main_layout.addLayout(bottom_layout)

    # --- 配置保存与读取 ---
    def save_config(self):
        config = {
            "api_key": self.api_key_input.text().strip(),
            "base_url": self.base_url_input.text().strip(),
            "model_name": self.model_input.text().strip(),
            "last_dir": self.dir_input.text().strip(),
            "last_tpl": self.tpl_input.text().strip()
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

    def load_config(self):
        # 1. 默认先把当次运行的内置模板最新路径填上
        default_tpl = resource_path("template.pdf")
        self.tpl_input.setText(default_tpl)

        if Path(CONFIG_FILE).exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.api_key_input.setText(config.get("api_key", ""))
                    self.base_url_input.setText(config.get("base_url", "https://api.openai.com/v1"))
                    self.model_input.setText(config.get("model_name", "gemini-2.5-flash-plus"))
                    self.dir_input.setText(config.get("last_dir", ""))
                    
                    # 2. 核心修复：检查保存的模板路径
                    saved_tpl = config.get("last_tpl", "")
                    # 只有当保存的路径不是空的、不包含 "_MEI"（说明是用户自定义的外部永久文件），
                    # 并且这个文件确实存在时，才覆盖掉默认路径
                    if saved_tpl and "_MEI" not in saved_tpl and Path(saved_tpl).exists():
                        self.tpl_input.setText(saved_tpl)
            except:
                pass

    # --- 槽函数 ---
    def select_input_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "选择发票文件夹")
        if directory:
            self.dir_input.setText(directory)
            self.save_config()

    def select_template_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择模板", "", "PDF Files (*.pdf)")
        if file_path:
            self.tpl_input.setText(file_path)
            self.save_config()

    def update_log(self, message):
        self.log_view.append(message)
        scrollbar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def task_finished(self, success):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("🚀 开始处理")
        if success:
            QMessageBox.information(self, "完成", "所有发票处理完毕并已成功合并！")

    def start_processing(self):
        input_dir = self.dir_input.text().strip()
        template_path = self.tpl_input.text().strip()
        api_key = self.api_key_input.text().strip()
        base_url = self.base_url_input.text().strip()
        model_name = self.model_input.text().strip()

        if not all([input_dir, template_path, api_key, base_url, model_name]):
            QMessageBox.warning(self, "参数不全", "请确保所有 API 配置和路径都已填写！")
            return

        self.save_config()

        self.log_view.clear()
        self.progress_bar.setValue(0)
        self.start_btn.setEnabled(False)
        self.start_btn.setText("⏳ 正在全力处理中...")

        output_file = Path(input_dir).parent / "最终合并出库单.pdf"

        # 传入真实参数启动线程
        self.worker = InvoiceWorker(input_dir, template_path, str(output_file), api_key, base_url, model_name)
        self.worker.log_signal.connect(self.update_log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.task_finished)
        self.worker.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())