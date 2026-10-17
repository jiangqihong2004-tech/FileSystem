"""
知识库会话管理器
=================================
- 支持上传 doc/docx/pdf/excel(xls/xlsx)/csv/txt 等格式文件
- 将文档解析为文本，按固定字符宽度分块
- 每段文本调用 base_agent.get_text_embeddings 转成向量并写入 kb_chunk 表
- 提供基于余弦相似度的检索 + RAG 问答

依赖说明：
- docx:  尝试 python-docx，若未安装则走"按原始文本解析"降级方案
- doc:   仅支持走降级方案（上传前建议转为 docx）
- pdf:   尝试 pdfplumber / PyPDF2，均无则降级为文本
- excel: 尝试 openpyxl + pandas，降级为 csv 原始解析
- csv:   用内置 csv/csv 模块
- txt:   直接读取
"""

import os
import json
import re
import uuid
import csv as _csv
from datetime import datetime

from sqlalchemy.orm import Session
from app.models import KnowledgeBase, KbDocument, KbChunk
from app.base_agent import (
    get_text_embeddings,
    get_single_embedding,
    cosine_similarity,
    hybrid_similarity,
    chat_with_agent,
)


# ============ 配置 ============
KB_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "file_mgr",
    "knowledge_base",
)
os.makedirs(KB_ROOT, exist_ok=True)

CHUNK_SIZE = 300          # 每个文本片段的最大字符数
CHUNK_OVERLAP = 30        # 片段间重叠字符数
TOP_K = 12                # 检索时取余弦相似度最高的前 N 个片段（提升到 12 条）

ALLOWED_EXTS = {
    ".doc", ".docx", ".pdf",
    ".xls", ".xlsx", ".csv",
    ".txt",
}


# ============ 工具函数 ============
def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def _extract_text_docx(path):
    # 优先使用 python-docx（提取段落、表格、标题，结构化更强）
    try:
        from docx import Document
        doc = Document(path)
        lines = []

        # 1. 提取段落（保留空行作为段落分隔，便于后续切块）
        for para in doc.paragraphs:
            if para and para.text and para.text.strip():
                txt = para.text.strip()
                # 尝试识别标题级别（让后续向量化更有结构）
                style_name = ""
                try:
                    if para.style and para.style.name:
                        style_name = para.style.name
                except Exception:
                    pass
                if style_name and ("标题" in style_name or "Heading" in style_name):
                    lines.append(f"【标题】{txt}")
                else:
                    lines.append(txt)

        # 2. 解析表格（每个表格一行一行读，列之间用 | 分隔）
        for table in doc.tables:
            for row in table.rows:
                cells = []
                for c in row.cells:
                    if c and c.text and c.text.strip():
                        cells.append(c.text.strip())
                if cells:
                    # 避免重复合并的单元格
                    if len(set(cells)) == 1 and len(cells) > 3:
                        lines.append(cells[0])
                    else:
                        lines.append(" | ".join(cells))

        # 3. 提取文档属性/注释（可选）
        try:
            if doc.core_properties:
                props = doc.core_properties
                title = getattr(props, "title", None)
                if title and str(title).strip():
                    lines.insert(0, f"【文档标题】{str(title).strip()}")
        except Exception:
            pass

        if lines:
            return "\n".join(lines)
    except Exception:
        pass

    # 降级方案：DOCX 本质是 ZIP 格式，直接解析内部 XML
    try:
        import zipfile
        import xml.etree.ElementTree as ET
        zf = zipfile.ZipFile(path, 'r')
        if 'word/document.xml' not in zf.namelist():
            return None
        data = zf.read('word/document.xml')
        root = ET.fromstring(data)
        texts = []
        for elem in root.iter():
            tag = elem.tag
            if '}' in tag:
                tag = tag.split('}')[1]
            if tag == 't' and elem.text and elem.text.strip():
                texts.append(elem.text)
        zf.close()
        if texts:
            return '\n'.join(texts)
        return None
    except Exception:
        return None


def _extract_text_pdf(path):
    """
    PDF 文本抽取（强鲁棒性版本）。
    策略顺序：
      1) pdfplumber（文本 PDF 首选）
      2) PyPDF2（文本 PDF 备选）
      3) fitz (PyMuPDF)（许多扫描件 PDF 自带 OCR 层或文本）
      4) 若前三者文本都极少，判定为扫描件 PDF，尝试 OCR：
         - PaddleOCR（中文最佳，可选）
         - pytesseract（需要安装 tesseract 引擎，可选）
      5) 终极降级：直接从原始字节提取可读文本
    """
    total_pages = 0

    # 1) pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            total_pages = len(pdf.pages)
            parts = []
            for p_idx, page in enumerate(pdf.pages):
                try:
                    t = page.extract_text() or ""
                    if t.strip():
                        parts.append(f"--- 第 {p_idx + 1} 页 ---\n{t}")
                except Exception:
                    continue
            if parts:
                combined = "\n".join(parts)
                avg = len(combined.replace("\n", "")) / max(1, total_pages)
                if avg >= 20:
                    return combined
                # 文本偏少，尝试 OCR
                ocr = _ocr_pdf_pages(path)
                if ocr and ocr.strip():
                    return ocr
                return combined
    except Exception:
        pass

    # 2) PyPDF2
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(path)
        total_pages = len(reader.pages)
        parts = []
        for i, page in enumerate(reader.pages):
            try:
                t = page.extract_text() or ""
                if t.strip():
                    parts.append(f"--- 第 {i + 1} 页 ---\n{t}")
            except Exception:
                continue
        if parts:
            combined = "\n".join(parts)
            avg = len(combined.replace("\n", "")) / max(1, total_pages)
            if avg >= 20:
                return combined
            ocr = _ocr_pdf_pages(path)
            if ocr and ocr.strip():
                return ocr
            return combined
    except Exception:
        pass

    # 3) fitz (PyMuPDF) - 比上面两个对某些新版 PDF 更兼容
    try:
        import fitz
        doc = fitz.open(path)
        total_pages = doc.page_count
        parts = []
        for p_idx in range(total_pages):
            try:
                page = doc.load_page(p_idx)
                t = page.get_text("text") or ""
                if t.strip():
                    parts.append(f"--- 第 {p_idx + 1} 页 ---\n{t}")
            except Exception:
                continue
        doc.close()
        if parts:
            combined = "\n".join(parts)
            avg = len(combined.replace("\n", "")) / max(1, total_pages)
            if avg >= 20:
                return combined
            # 扫描件：用 PyMuPDF 的 pixmap + OCR
            ocr = _ocr_pdf_pages(path)
            if ocr and ocr.strip():
                return ocr
            return combined
    except Exception:
        pass

    # 4) 尝试 OCR（扫描件 PDF）
    try:
        ocr = _ocr_pdf_pages(path)
        if ocr and ocr.strip():
            return ocr
    except Exception:
        pass

    # 5) 终极降级：从原始字节提取可读文本
    try:
        with open(path, 'rb') as f:
            raw = f.read()
        for enc in ('utf-8', 'gbk', 'latin-1'):
            try:
                text = raw.decode(enc, errors='ignore')
                lines = []
                for line in text.split('\n'):
                    clean = line.strip()
                    if len(clean) > 10:
                        filtered = ''.join(
                            c for c in clean
                            if c.isalnum() or c in ' -_,.()[]{}<>/\\，。；：""''（）《》【】【】、'
                        )
                        if len(filtered) > 10:
                            lines.append(filtered)
                if lines:
                    return "\n".join(lines[:150])
            except Exception:
                continue
    except Exception:
        pass

    return None


def _ocr_pdf_pages(path: str):
    """
    对扫描件 PDF 做 OCR 识别。
    优先 PaddleOCR（中文最佳），其次 pytesseract。
    都不可用时返回 None。
    """
    try:
        from pdf2image import convert_from_path
    except Exception:
        return None

    try:
        try:
            import platform
            if platform.system() == "Windows":
                images = convert_from_path(path, dpi=200, first_page=1, last_page=30, fmt="jpeg")
            else:
                images = convert_from_path(path, dpi=200, first_page=1, last_page=30, fmt="jpeg")
        except Exception:
            try:
                images = convert_from_path(path, dpi=150, first_page=1, last_page=30)
            except Exception:
                images = None
    except Exception:
        images = None

    if not images:
        # 兜底：尝试用 fitz 自己将 PDF 转图片（依赖 pdf2image 失败时的备选）
        try:
            import fitz
            doc = fitz.open(path)
            images = []
            for p_idx in range(min(30, doc.page_count)):
                try:
                    page = doc.load_page(p_idx)
                    pix = page.get_pixmap(dpi=150)
                    # 转成 PIL.Image
                    from PIL import Image
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    images.append(img)
                except Exception:
                    continue
            doc.close()
        except Exception:
            pass

    if not images:
        return None

    # 尝试 PaddleOCR
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
        result_lines = []
        for p_idx, img in enumerate(images):
            try:
                result = ocr.ocr(img, cls=True)
                if not result or not result[0]:
                    continue
                page_text = []
                for line in result[0]:
                    try:
                        txt = line[1][0]
                        conf = line[1][1]
                        if txt and conf > 0.5:
                            page_text.append(txt.strip())
                    except Exception:
                        continue
                if page_text:
                    result_lines.append(f"--- 第 {p_idx + 1} 页（OCR）---\n" + "\n".join(page_text))
            except Exception:
                continue
        if result_lines:
            return "\n\n".join(result_lines)
    except Exception:
        pass

    # 尝试 pytesseract
    try:
        import pytesseract
        result_lines = []
        for p_idx, img in enumerate(images):
            try:
                text = pytesseract.image_to_string(img, lang="chi_sim+eng")
                if text and text.strip():
                    result_lines.append(f"--- 第 {p_idx + 1} 页（OCR）---\n{text.strip()}")
            except Exception:
                continue
        if result_lines:
            return "\n\n".join(result_lines)
    except Exception:
        pass

    return None


def _extract_text_doc(path):
    """
    解析旧式 .doc 文件。由于该格式为复合二进制文档，需要特殊库。
    若无库则降级：直接提取可读文本。
    """
    # 尝试 antiword (需系统安装，Linux/macOS 常见)
    try:
        import subprocess
        result = subprocess.run(['antiword', path], capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    # 尝试 textract (需安装额外库)
    try:
        import textract
        text = textract.process(path).decode('utf-8')
        if text and text.strip():
            return text.strip()
    except Exception:
        pass

    # 降级：以 GBK/UTF-8 读取原始内容，提取可读文本
    try:
        with open(path, 'rb') as f:
            raw = f.read()
        for enc in ('gbk', 'utf-8', 'utf-16', 'latin-1'):
            try:
                text = raw.decode(enc, errors='ignore')
                lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 10]
                if len(lines) > 3:
                    return '\n'.join(lines[:200])
            except Exception:
                continue
    except Exception:
        pass
    return None


def _extract_text_xlsx(path):
    """
    解析 XLSX 文件（Office 2007+）。
    使用 Python 原生 zipfile + xml 模块，不依赖 openpyxl，
    避免 Windows 上 numpy/mingw 导致的兼容性问题。
    """
    try:
        import zipfile
        import xml.etree.ElementTree as ET
    except Exception:
        return None

    try:
        zf = zipfile.ZipFile(path, 'r')
    except Exception:
        return None

    try:
        # 1) 读取 sharedStrings.xml（共享字符串表）
        #    XLSX 中的字符串文本通常存储在共享字符串表中
        shared_strings = []
        try:
            ss_data = zf.read('xl/sharedStrings.xml')
            root = ET.fromstring(ss_data)
            ns = ''
            if root.tag.startswith('{'):
                ns = root.tag[:root.tag.index('}') + 1]
            for si in root.findall(f'{ns}si'):
                text_parts = []
                for t in si.iter(f'{ns}t'):
                    if t.text:
                        text_parts.append(t.text)
                if not text_parts:
                    v = si.find(f'{ns}v')
                    if v is not None and v.text:
                        text_parts.append(v.text)
                shared_strings.append(''.join(text_parts))
        except Exception:
            shared_strings = []

        # 2) 读取工作表列表
        workbook_sheets = []
        try:
            wb_data = zf.read('xl/workbook.xml')
            root = ET.fromstring(wb_data)
            ns = ''
            if root.tag.startswith('{'):
                ns = root.tag[:root.tag.index('}') + 1]
            sheets_el = root.find(f'{ns}sheets')
            if sheets_el is not None:
                for sheet in sheets_el.findall(f'{ns}sheet'):
                    sheet_name = sheet.get('name', 'Sheet')
                    sheet_id = sheet.get(
                        '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id',
                        ''
                    )
                    workbook_sheets.append((sheet_name, sheet_id))
        except Exception:
            workbook_sheets = []

        # 3) 通过 relationships 找到 sheet 实际 XML 路径
        rel_map = {}
        try:
            rel_data = zf.read('xl/_rels/workbook.xml.rels')
            root = ET.fromstring(rel_data)
            for rel in root.findall(
                './/{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'
            ):
                rel_id = rel.get('Id', '')
                target = rel.get('Target', '')
                rel_map[rel_id] = target
        except Exception:
            pass

        # 4) 如果没找到 workbook 配置，尝试直接读取所有 worksheet 文件
        if not workbook_sheets:
            sheet_files = sorted(
                [name for name in zf.namelist()
                 if name.startswith('xl/worksheets/sheet') and name.endswith('.xml')],
                key=lambda x: int(x.split('sheet')[-1].split('.')[0])
            )
            for i, sf in enumerate(sheet_files):
                workbook_sheets.append((f'Sheet{i + 1}', sf))

        # 5) 解析每个工作表
        rows_out = []
        for sheet_name, sheet_id_or_path in workbook_sheets:
            rows_out.append(f"=== Sheet: {sheet_name} ===")
            sheet_path = sheet_id_or_path
            if sheet_id_or_path in rel_map:
                target = rel_map[sheet_id_or_path]
                if target.startswith('worksheets/'):
                    sheet_path = 'xl/' + target
                elif not target.startswith('xl/'):
                    sheet_path = 'xl/' + target
            elif not sheet_path.endswith('.xml'):
                sheet_idx = workbook_sheets.index((sheet_name, sheet_id_or_path)) + 1
                sheet_path = f'xl/worksheets/sheet{sheet_idx}.xml'

            try:
                sheet_data = zf.read(sheet_path)
            except Exception:
                continue

            try:
                root = ET.fromstring(sheet_data)
                ns = ''
                if root.tag.startswith('{'):
                    ns = root.tag[:root.tag.index('}') + 1]
                sheetData = root.find(f'{ns}sheetData')
                if sheetData is None:
                    continue

                for row in sheetData.findall(f'{ns}row'):
                    cell_values = []
                    for cell in row.findall(f'{ns}c'):
                        t = cell.get('t', '')
                        s = cell.get('s', '')  # 样式引用（用于判断日期格式）
                        value = ''
                        v = cell.find(f'{ns}v')
                        is_text = cell.find(f'{ns}is')
                        if is_text is not None:
                            for t_node in is_text.iter(f'{ns}t'):
                                if t_node.text:
                                    value += t_node.text
                        elif t == 's' and v is not None and v.text:
                            try:
                                idx = int(v.text)
                                if 0 <= idx < len(shared_strings):
                                    value = shared_strings[idx]
                            except Exception:
                                value = v.text or ''
                        elif t == 'b' and v is not None:
                            value = 'True' if v.text == '1' else 'False'
                        elif v is not None and v.text is not None:
                            raw = v.text.strip()
                            # 检测 Excel 数字日期（serial date：1900 年起的天数）
                            # 数字在 10000~80000 范围内且样式引用存在时，推测为日期
                            try:
                                num = float(raw)
                                is_likely_date = (
                                    bool(s)
                                    and 10000 <= num <= 80000
                                    and raw.count('.') <= 1
                                )
                                if is_likely_date:
                                    # 转换为 YYYY-MM-DD（Excel 有著名的 1900 闰年 bug）
                                    from datetime import datetime, timedelta
                                    excel_epoch = datetime(1899, 12, 30)
                                    days_int = int(num)
                                    frac = num - days_int
                                    dt = excel_epoch + timedelta(days=days_int)
                                    hours = int(frac * 24)
                                    minutes = int((frac * 24 - hours) * 60)
                                    if hours == 0 and minutes == 0:
                                        value = dt.strftime('%Y-%m-%d')
                                    else:
                                        value = dt.strftime('%Y-%m-%d %H:%M')
                                else:
                                    # 整数保持原格式，浮点保留原始值
                                    if num == int(num):
                                        value = str(int(num))
                                    else:
                                        value = raw
                            except ValueError:
                                value = raw
                        cell_values.append(value.strip() if value else '')

                    if any(cell_values):
                        rows_out.append(" | ".join(cell_values))
            except Exception:
                continue

        zf.close()
        if len(rows_out) <= 1:
            return None
        return "\n".join(rows_out)
    except Exception:
        try:
            zf.close()
        except Exception:
            pass
        return None


def _extract_text_xls(path):
    """
    解析旧式 .xls 文件 (Excel 97-2003)。
    需要 xlrd 库。如果 xlrd 不可用或解析失败，返回 None。
    注意：xlrd 2.0+ 不再支持 xlsx，仅支持 xls。
    """
    try:
        import xlrd
    except Exception:
        return None
    try:
        book = xlrd.open_workbook(path)
        rows_out = []
        for sheet in book.sheets():
            rows_out.append(f"=== Sheet: {sheet.name} ===")
            for r in range(sheet.nrows):
                cells = []
                for c in range(sheet.ncols):
                    v = sheet.cell_value(r, c)
                    cells.append("" if v is None else str(v).strip())
                if any(cells):
                    rows_out.append(" | ".join(cells))
        return "\n".join(rows_out)
    except Exception:
        return None


def _extract_text_csv(path):
    try:
        rows_out = []
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            reader = _csv.reader(f)
            for row in reader:
                cleaned = [c.strip() for c in row]
                if any(cleaned):
                    rows_out.append(" | ".join(cleaned))
        return "\n".join(rows_out) if rows_out else None
    except Exception:
        # 尝试 gbk
        try:
            rows_out = []
            with open(path, "r", encoding="gbk", errors="ignore") as f:
                reader = _csv.reader(f)
                for row in reader:
                    cleaned = [c.strip() for c in row]
                    if any(cleaned):
                        rows_out.append(" | ".join(cleaned))
            return "\n".join(rows_out) if rows_out else None
        except Exception:
            return None


def _extract_text_txt(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        try:
            with open(path, "r", encoding="gbk", errors="ignore") as f:
                return f.read()
        except Exception:
            return None


def extract_file_text(path: str, ext: str) -> (str, str):
    """
    从文件中抽取纯文本内容。
    返回 (text, status_msg)，失败时 text=None。
    """
    ext = (ext or "").lower()
    if ext == ".docx":
        t = _extract_text_docx(path)
        if t is None:
            return (None, "DOCX 文件解析失败，请确保文件完整或尝试另存为其他格式")
        return (t, "ok")
    if ext == ".doc":
        t = _extract_text_doc(path)
        if t is None:
            return (None, "旧版 .doc 格式解析受限，请另存为 .docx 后重新上传")
        return (t, "ok")
    if ext == ".pdf":
        t = _extract_text_pdf(path)
        if t is None:
            return (None, "PDF 文件解析失败，可能是图片扫描版 PDF，建议安装 pdfplumber：pip install pdfplumber")
        return (t, "ok")
    if ext == ".xlsx":
        t = _extract_text_xlsx(path)
        if t is None:
            return (None, "缺少 openpyxl 库，建议安装：pip install openpyxl")
        return (t, "ok")
    if ext == ".xls":
        t = _extract_text_xls(path)
        if t is None:
            return (None, "缺少 xlrd 库，或该 .xls 不被支持，建议另存为 .xlsx")
        return (t, "ok")
    if ext == ".csv":
        t = _extract_text_csv(path)
        return (t, "ok") if t else (None, "CSV 文件为空或编码无法识别")
    if ext == ".txt":
        t = _extract_text_txt(path)
        return (t, "ok") if t else (None, "TXT 文件为空")
    return (None, f"不支持的文件类型 {ext}")


def split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list:
    """
    按固定字符宽度切分文本，保留一定重叠以避免跨段信息丢失。
    同时保留空行、段落分隔的结构信息。
    """
    if not text:
        return []
    # 统一换行
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 将多个连续空白行简化为段分隔符
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = text.split("\n")

    chunks = []
    buf = ""
    for line in lines:
        line = line.strip()
        if not line:
            # 空行作为段落分隔
            if buf:
                # 把当前 buf 输出为一个片段（若较长）
                if len(buf) >= chunk_size // 2:
                    chunks.append(buf)
                    buf = buf[-overlap:] if overlap > 0 else ""
            continue
        if buf:
            buf += "\n"
        buf += line
        # 达到 chunk_size 就切块
        while len(buf) >= chunk_size:
            # 找最近的句号/换行作为切分点
            cut = chunk_size
            # 在 [chunk_size*0.7, chunk_size] 内寻找合适的切分点
            search_start = int(chunk_size * 0.7)
            for i in range(chunk_size - 1, search_start - 1, -1):
                if i >= len(buf):
                    continue
                ch = buf[i]
                if ch in "。.!！?？;；\n":
                    cut = i + 1
                    break
            chunks.append(buf[:cut])
            buf = buf[cut:]
    if buf.strip():
        chunks.append(buf)

    # 对超长片段再强行切一次（兜底）
    final_chunks = []
    for c in chunks:
        if len(c) <= chunk_size * 2:
            final_chunks.append(c)
        else:
            for i in range(0, len(c), chunk_size):
                piece = c[i:i + chunk_size]
                if piece.strip():
                    final_chunks.append(piece)
    return final_chunks


def split_tabular_rows(raw_lines: list) -> list:
    """
    针对表格类数据（每行数据）切成「表头 + 该行」的独立片段。
    便于针对具体的每行精准匹配「张三/李四/...」等。
    raw_lines: list[str]: 按行解析的原始数据，首行为表头。
    """
    if not raw_lines:
        return []
    # 第一行作为表头；后续为数据行
    header = raw_lines[0].strip()
    data_rows = [l.strip() for l in raw_lines[1:]]
    # 每个数据行拼接「表头 + 该行」作为一个片段
    chunks = []
    for row in data_rows:
        if not row:
            continue
        chunks.append(header + "\n" + row)
    # 如果数据量很少，也合并出一个大的概览片段便于整体检索
    if not chunks:
        # 退化为按字符宽度切分（此时 raw_lines 仅表头）
        chunks = split_into_chunks("\n".join(raw_lines))
    return chunks


# ============ 业务层 ============
class KnowledgeSession:
    """
    知识库会话：负责文件存储、文本解析、向量化、查询。
    每个实例绑定一个 db session 与 当前 user。
    """

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    # ---------- 知识库 CRUD ----------
    def list_knowledge_bases(self) -> list:
        items = (
            self.db.query(KnowledgeBase)
            .filter(KnowledgeBase.user_id == self.user_id)
            .order_by(KnowledgeBase.update_time.desc())
            .all()
        )
        # 读取每个知识库的实际 chunk 数量（保证显示一致）
        result = []
        for kb in items:
            real_doc_count = (
                self.db.query(KbDocument).filter(KbDocument.kb_id == kb.id).count()
            )
            real_chunk_count = (
                self.db.query(KbChunk).filter(KbChunk.kb_id == kb.id).count()
            )
            d = self._kb_to_dict(kb)
            d["doc_count"] = real_doc_count
            d["chunk_count"] = real_chunk_count
            result.append(d)
        return result

    def create_knowledge_base(self, name: str, description: str = "") -> dict:
        name = (name or "").strip()
        if not name:
            raise ValueError("知识库名称不能为空")
        # 若同名已存在，直接返回
        exist = (
            self.db.query(KnowledgeBase)
            .filter(KnowledgeBase.user_id == self.user_id, KnowledgeBase.name == name)
            .first()
        )
        if exist:
            return self._kb_to_dict(exist)
        kb = KnowledgeBase(
            user_id=self.user_id,
            name=name,
            description=description or "",
            doc_count=0,
            chunk_count=0,
        )
        self.db.add(kb)
        self.db.commit()
        self.db.refresh(kb)
        return self._kb_to_dict(kb)

    def get_knowledge_base(self, kb_id: int) -> KnowledgeBase | None:
        return (
            self.db.query(KnowledgeBase)
            .filter(KnowledgeBase.id == kb_id, KnowledgeBase.user_id == self.user_id)
            .first()
        )

    def delete_knowledge_base(self, kb_id: int) -> bool:
        kb = self.get_knowledge_base(kb_id)
        if not kb:
            return False
        # 删除相关 chunk
        self.db.query(KbChunk).filter(KbChunk.kb_id == kb.id).delete(synchronize_session=False)
        # 删除相关文档记录（并清理文件）
        docs = self.db.query(KbDocument).filter(KbDocument.kb_id == kb.id).all()
        for doc in docs:
            try:
                if doc.file_path and os.path.exists(doc.file_path):
                    os.remove(doc.file_path)
            except Exception:
                pass
        self.db.query(KbDocument).filter(KbDocument.kb_id == kb.id).delete(synchronize_session=False)
        self.db.delete(kb)
        self.db.commit()
        return True

    # ---------- 文档上传与向量化 ----------
    def upload_document(self, kb_id: int, filename: str, file_bytes: bytes):
        """
        保存上传文件到磁盘并解析为文本/向量化/写入数据库。
        返回 dict 文档元数据。
        """
        kb = self.get_knowledge_base(kb_id)
        if not kb:
            raise ValueError("指定的知识库不存在或无权限")

        filename = filename or "untitled"
        ext = os.path.splitext(filename)[1].lower()
        if not ext:
            ext = ".txt"
        if ext not in ALLOWED_EXTS:
            raise ValueError(f"不支持的文件类型：{ext}（支持 doc/docx/pdf/xls/xlsx/csv/txt）")

        # 存文件
        user_dir = os.path.join(KB_ROOT, f"user_{self.user_id}", f"kb_{kb.id}")
        _ensure_dir(user_dir)
        save_name = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(user_dir, save_name)
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        file_size = len(file_bytes)

        doc = KbDocument(
            kb_id=kb.id,
            user_id=self.user_id,
            original_name=filename,
            save_name=save_name,
            file_path=file_path,
            file_size=file_size,
            file_type=ext.lstrip("."),
            status="processing",
            status_msg="正在解析与向量化...",
            chunk_count=0,
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)

        try:
            # 文本抽取
            text, msg = extract_file_text(file_path, ext)
            if text is None:
                doc.status = "failed"
                doc.status_msg = msg or "文本抽取失败"
                self.db.commit()
                return self._doc_to_dict(doc)

            # 分段：CSV/Excel 按行分（表头 + 每行），其他文本按字符宽度
            if ext in (".csv", ".xls", ".xlsx"):
                lines = [l.strip() for l in text.split("\n") if l and l.strip()]
                # 跳过 sheet 头（"=== Sheet: xxx ===" 这类）
                clean_lines = [l for l in lines if not l.startswith("=== Sheet")]
                chunks = split_tabular_rows(clean_lines)
            else:
                chunks = split_into_chunks(text)
            if not chunks:
                doc.status = "failed"
                doc.status_msg = "文档无有效文本内容"
                self.db.commit()
                return self._doc_to_dict(doc)

            # 向量化（分批，避免一次请求过长）
            all_vectors = []
            batch_size = 16
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                vecs = get_text_embeddings(batch)
                all_vectors.extend(vecs)
            # 保证长度一致
            if len(all_vectors) != len(chunks):
                # 兜底：如果批之间长度不一致，重新用单条封装
                all_vectors = [get_single_embedding(c) for c in chunks]

            # 写入库
            insert_count = 0
            for idx, chunk_text in enumerate(chunks):
                vec = all_vectors[idx] if idx < len(all_vectors) else get_single_embedding(chunk_text)
                chunk = KbChunk(
                    kb_id=kb.id,
                    doc_id=doc.id,
                    user_id=self.user_id,
                    content=chunk_text,
                    vector_json=json.dumps(vec, ensure_ascii=False),
                    vector_dim=len(vec),
                    char_count=len(chunk_text),
                    page_info=f"chunk-{idx + 1}",
                )
                self.db.add(chunk)
                insert_count += 1
            doc.chunk_count = insert_count
            doc.status = "ready"
            doc.status_msg = f"向量化完成，共 {insert_count} 段"

            # 同步知识库统计
            all_doc_count = self.db.query(KbDocument).filter(KbDocument.kb_id == kb.id).count()
            all_chunk_count = self.db.query(KbChunk).filter(KbChunk.kb_id == kb.id).count()
            kb.doc_count = all_doc_count
            kb.chunk_count = all_chunk_count
            kb.update_time = datetime.now()
            self.db.commit()
            self.db.refresh(doc)
            return self._doc_to_dict(doc)
        except Exception as e:
            doc.status = "failed"
            doc.status_msg = f"处理异常：{e}"
            self.db.commit()
            return self._doc_to_dict(doc)

    def list_documents(self, kb_id: int) -> list:
        kb = self.get_knowledge_base(kb_id)
        if not kb:
            return []
        items = (
            self.db.query(KbDocument)
            .filter(KbDocument.kb_id == kb.id, KbDocument.user_id == self.user_id)
            .order_by(KbDocument.update_time.desc())
            .all()
        )
        return [self._doc_to_dict(d) for d in items]

    def delete_document(self, doc_id: int) -> bool:
        doc = (
            self.db.query(KbDocument)
            .filter(KbDocument.id == doc_id, KbDocument.user_id == self.user_id)
            .first()
        )
        if not doc:
            return False
        # 删除磁盘文件
        try:
            if doc.file_path and os.path.exists(doc.file_path):
                os.remove(doc.file_path)
        except Exception:
            pass
        # 删除 chunk
        self.db.query(KbChunk).filter(KbChunk.doc_id == doc.id).delete(synchronize_session=False)
        kb_id = doc.kb_id
        self.db.delete(doc)
        self.db.commit()
        # 更新知识库统计
        kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if kb:
            kb.doc_count = self.db.query(KbDocument).filter(KbDocument.kb_id == kb.id).count()
            kb.chunk_count = self.db.query(KbChunk).filter(KbChunk.kb_id == kb.id).count()
            kb.update_time = datetime.now()
            self.db.commit()
        return True

    # ---------- 知识库和文档的重命名/移动/下载 ----------
    def rename_knowledge_base(self, kb_id: int, new_name: str, new_desc: str = None) -> dict:
        """重命名知识库（同时可更新描述）"""
        kb = self.get_knowledge_base(kb_id)
        if not kb:
            raise ValueError("知识库不存在或无权限")
        new_name = (new_name or "").strip()
        if not new_name:
            raise ValueError("知识库名称不能为空")
        kb.name = new_name
        if new_desc is not None:
            kb.description = new_desc
        kb.update_time = datetime.now()
        self.db.commit()
        self.db.refresh(kb)
        return self._kb_to_dict(kb)

    def rename_document(self, doc_id: int, new_name: str) -> dict:
        """重命名文档（仅修改显示名，不修改磁盘文件）"""
        doc = (
            self.db.query(KbDocument)
            .filter(KbDocument.id == doc_id, KbDocument.user_id == self.user_id)
            .first()
        )
        if not doc:
            raise ValueError("文档不存在或无权限")
        new_name = (new_name or "").strip()
        if not new_name:
            raise ValueError("文档名称不能为空")
        doc.original_name = new_name
        doc.update_time = datetime.now()
        self.db.commit()
        self.db.refresh(doc)
        return self._doc_to_dict(doc)

    def move_document(self, doc_id: int, target_kb_id: int) -> dict:
        """将文档移动到另一个知识库"""
        doc = (
            self.db.query(KbDocument)
            .filter(KbDocument.id == doc_id, KbDocument.user_id == self.user_id)
            .first()
        )
        if not doc:
            raise ValueError("文档不存在或无权限")
        target_kb = self.get_knowledge_base(target_kb_id)
        if not target_kb:
            raise ValueError("目标知识库不存在或无权限")
        old_kb_id = doc.kb_id
        doc.kb_id = target_kb_id
        doc.update_time = datetime.now()
        self.db.commit()

        # 同步旧知识库的统计
        old_kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == old_kb_id).first()
        if old_kb:
            old_kb.doc_count = self.db.query(KbDocument).filter(KbDocument.kb_id == old_kb_id).count()
            old_kb.chunk_count = self.db.query(KbChunk).filter(KbChunk.kb_id == old_kb_id).count()
        # 同步新知识库的统计
        target_kb.doc_count = self.db.query(KbDocument).filter(KbDocument.kb_id == target_kb_id).count()
        target_kb.chunk_count = self.db.query(KbChunk).filter(KbChunk.kb_id == target_kb_id).count()
        target_kb.update_time = datetime.now()
        self.db.commit()
        self.db.refresh(doc)
        return self._doc_to_dict(doc)

    def get_document_path(self, doc_id: int) -> dict:
        """获取文档磁盘路径（用于下载）"""
        doc = (
            self.db.query(KbDocument)
            .filter(KbDocument.id == doc_id, KbDocument.user_id == self.user_id)
            .first()
        )
        if not doc:
            raise ValueError("文档不存在或无权限")
        if not doc.file_path or not os.path.exists(doc.file_path):
            raise ValueError("磁盘文件已丢失")
        return {
            "file_path": doc.file_path,
            "original_name": doc.original_name,
            "file_size": doc.file_size,
        }

    def get_knowledge_base_docs(self, kb_id: int) -> list:
        """获取知识库中所有文档的下载信息（打包下载）"""
        kb = self.get_knowledge_base(kb_id)
        if not kb:
            raise ValueError("知识库不存在或无权限")
        docs = (
            self.db.query(KbDocument)
            .filter(KbDocument.kb_id == kb.id, KbDocument.user_id == self.user_id)
            .all()
        )
        result = []
        for doc in docs:
            if doc.file_path and os.path.exists(doc.file_path):
                result.append({
                    "file_path": doc.file_path,
                    "original_name": doc.original_name,
                    "file_size": doc.file_size,
                })
        return result

    # ---------- 基于向量的检索 + RAG 问答 ----------
    def search_all_top_k(self, query_text: str, top_k: int = TOP_K) -> list:
        """
        在用户所有知识库中按混合相似度检索最相关 top_k 条片段。
        支持去重与上下文窗口扩展（对高分片段拼接相邻 chunk）。
        """
        query_text = (query_text or "").strip() or " "
        q_vec = get_single_embedding(query_text)
        all_chunks = (
            self.db.query(KbChunk)
            .filter(KbChunk.user_id == self.user_id)
            .all()
        )
        if not all_chunks:
            return []

        scored = []
        for c in all_chunks:
            try:
                vec = json.loads(c.vector_json) if c.vector_json else []
            except Exception:
                vec = []
            score = hybrid_similarity(q_vec, vec, query_text, c.content or "")
            scored.append((score, c))
        scored.sort(key=lambda x: x[0], reverse=True)

        # 放宽过滤阈值（0.02 即可保留潜在相关片段）
        scored = [item for item in scored if item[0] > 0.02]

        # 内容去重
        seen = set()
        deduped = []
        for s, c in scored:
            key = (c.content or "").strip()
            if key and key not in seen:
                seen.add(key)
                deduped.append((s, c))

        # 对高分片段做上下文窗口扩展
        final_items = []
        added_ids = set()
        for i, (s, c) in enumerate(deduped):
            if c.id in added_ids:
                continue
            extended_content = c.content or ""
            if s > 0.3:
                try:
                    same_doc = [cj for sj, cj in deduped if cj.doc_id == c.doc_id and cj.id != c.id]
                    same_doc.sort(key=lambda x: x.id)
                    ids_sorted = [x.id for x in same_doc]
                    try:
                        pos = ids_sorted.index(c.id)
                    except ValueError:
                        pos = -1
                    if pos > 0 and same_doc[pos - 1].id not in added_ids:
                        extended_content = (same_doc[pos - 1].content or "") + "\n" + extended_content
                        added_ids.add(same_doc[pos - 1].id)
                    if 0 <= pos < len(same_doc) - 1 and same_doc[pos + 1].id not in added_ids:
                        extended_content = extended_content + "\n" + (same_doc[pos + 1].content or "")
                        added_ids.add(same_doc[pos + 1].id)
                except Exception:
                    pass
            added_ids.add(c.id)
            final_items.append((s, c, extended_content))
            if len(final_items) >= top_k * 2:
                break

        top = final_items[:top_k]
        return [
            {
                "score": round(float(s), 4),
                "content": ext_content or c.content or "",
                "doc_id": c.doc_id,
                "chunk_id": c.id,
                "kb_id": c.kb_id,
                "page_info": c.page_info or f"chunk-{i + 1}",
                "char_count": c.char_count or 0,
            }
            for i, (s, c, ext_content) in enumerate(top)
        ]

    def search_top_k(self, kb_id: int, query_text: str, top_k: int = TOP_K) -> list:
        """
        在指定知识库中按「混合相似度评分（余弦 + 关键词 ngram 重叠）」检索最相关的 top_k 条片段。
        支持内容去重与上下文窗口扩展。
        """
        kb = self.get_knowledge_base(kb_id)
        if not kb:
            return []
        query_text = (query_text or "").strip() or " "
        q_vec = get_single_embedding(query_text)
        all_chunks = (
            self.db.query(KbChunk)
            .filter(KbChunk.kb_id == kb.id, KbChunk.user_id == self.user_id)
            .all()
        )
        if not all_chunks:
            return []

        scored = []
        for c in all_chunks:
            try:
                vec = json.loads(c.vector_json) if c.vector_json else []
            except Exception:
                vec = []
            score = hybrid_similarity(q_vec, vec, query_text, c.content or "")
            scored.append((score, c))
        scored.sort(key=lambda x: x[0], reverse=True)

        # 放宽过滤阈值（0.02）
        scored = [item for item in scored if item[0] > 0.02]

        # 内容去重
        seen = set()
        deduped = []
        for s, c in scored:
            key = (c.content or "").strip()
            if key and key not in seen:
                seen.add(key)
                deduped.append((s, c))

        # 对高分片段做上下文窗口扩展
        final_items = []
        added_ids = set()
        for i, (s, c) in enumerate(deduped):
            if c.id in added_ids:
                continue
            extended_content = c.content or ""
            if s > 0.3:
                try:
                    same_doc = [cj for sj, cj in deduped if cj.doc_id == c.doc_id and cj.id != c.id]
                    same_doc.sort(key=lambda x: x.id)
                    ids_sorted = [x.id for x in same_doc]
                    try:
                        pos = ids_sorted.index(c.id)
                    except ValueError:
                        pos = -1
                    if pos > 0 and same_doc[pos - 1].id not in added_ids:
                        extended_content = (same_doc[pos - 1].content or "") + "\n" + extended_content
                        added_ids.add(same_doc[pos - 1].id)
                    if 0 <= pos < len(same_doc) - 1 and same_doc[pos + 1].id not in added_ids:
                        extended_content = extended_content + "\n" + (same_doc[pos + 1].content or "")
                        added_ids.add(same_doc[pos + 1].id)
                except Exception:
                    pass
            added_ids.add(c.id)
            final_items.append((s, c, extended_content))
            if len(final_items) >= top_k * 2:
                break

        top = final_items[:top_k]
        return [
            {
                "score": round(float(s), 4),
                "content": ext_content or c.content or "",
                "doc_id": c.doc_id,
                "chunk_id": c.id,
                "kb_id": c.kb_id,
                "page_info": c.page_info or f"chunk-{i + 1}",
                "char_count": c.char_count or 0,
            }
            for i, (s, c, ext_content) in enumerate(top)
        ]

    def rag_answer(self, kb_id: int, user_query: str) -> dict:
        """
        构建 RAG 上下文，调用 chat_with_agent 让模型基于知识库回答。
        改进：
          - 给 LLM 明确的「相关性-回答」模板
          - 最高分低于 0.08 时直接提示"暂未检索到足够相关内容"，避免模型凭空猜测
        """
        kb = self.get_knowledge_base(kb_id)
        if not kb:
            return {
                "answer": "知识库不存在或无权限访问。",
                "hits": [],
                "kb": {"id": kb_id, "name": ""},
            }
        hits = self.search_top_k(kb_id, user_query, top_k=TOP_K)
        kb_stat = {
            "id": kb.id,
            "name": kb.name,
            "doc_count": kb.doc_count or 0,
            "chunk_count": kb.chunk_count or 0,
        }

        if not hits:
            reply_text = (
                f"该知识库「{kb.name}」当前没有可供检索的向量化片段。"
                "请先上传 doc/docx/pdf/xls/xlsx/csv/txt 等格式的文档，"
                "让系统完成向量化后再提问。"
            )
            return {"answer": reply_text, "hits": [], "kb": kb_stat}

        max_score = max([h["score"] for h in hits]) if hits else 0.0

        # 构建 RAG 上下文
        context_parts = []
        for i, hit in enumerate(hits, 1):
            page = hit.get("page_info") or f"片段{i}"
            doc_id = hit.get("doc_id", "")
            context_parts.append(
                f"[片段 {i}] 相似度 {hit['score']:.3f}；文档ID：{doc_id}；位置：{page}\n"
                f"{hit['content']}"
            )
        context_block = "\n\n".join(context_parts)

        # 相似度很低时给出提示
        low_relevance_note = ""
        if max_score < 0.08:
            low_relevance_note = (
                "【系统提示】检索到的片段与您的问题相似度较低（最高 "
                f"{max_score:.3f}），内容可能与问题无关。请参考片段内容，"
                "并明确告知用户哪些信息在知识库中能找到，哪些找不到。"
            )
        elif max_score < 0.15:
            low_relevance_note = (
                f"【系统提示】最高分片段的相似度为 {max_score:.3f}，"
                "建议在回答中注明「部分信息来自知识库片段」，并在不能完整回答时明确说明。"
            )

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个知识库问答助手。用户上传了文档，系统按相似度排序返回若干片段。"
                    "请严格依据片段中的内容回答用户问题。\n"
                    "\n"
                    "【核心规则】\n"
                    "1) 只使用片段中明确提到的信息，不得编造、不得推断、不得引用片段外的常识；\n"
                    "2) 若片段内容不足以回答问题，请说「未能在知识库中找到足够相关的内容来回答该问题」，"
                    "并列出片段中与问题最接近的若干要点；\n"
                    "3) 若片段互相矛盾，请指出矛盾点并分别列出；\n"
                    "4) 回答使用中文，结构清晰，语言自然，不输出括号内的指令。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"### 知识库名称：{kb.name}\n"
                    f"### 检索总体相关度：最高相似度 {max_score:.3f}（满分 1.00）\n"
                    + (f"\n{low_relevance_note}\n" if low_relevance_note else "\n")
                    + "### 参考片段（已按相关度排序，片段之间用空行分隔）：\n"
                    + f"{context_block}\n\n"
                    f"### 用户问题：\n{user_query}\n\n"
                    "请先判断片段与问题的相关性，再基于片段内容给出中文回答。"
                ),
            },
        ]

        try:
            reply = chat_with_agent(messages, use_tools=False)
        except Exception as e:
            reply = f"（调用 AI 模型时出现异常：{e}）"
        return {"answer": reply or "", "hits": hits, "kb": kb_stat}

    def rag_answer_all(self, user_query: str) -> dict:
        """跨所有知识库的 RAG 问答。"""
        hits = self.search_all_top_k(user_query, top_k=TOP_K)

        all_kbs = (
            self.db.query(KnowledgeBase)
            .filter(KnowledgeBase.user_id == self.user_id)
            .all()
        )
        total_chunks = (
            self.db.query(KbChunk)
            .filter(KbChunk.user_id == self.user_id)
            .count()
        )
        kb_names = "、".join([kb.name for kb in all_kbs]) if all_kbs else "(暂无知识库)"
        kb_stat = {
            "kb_count": len(all_kbs),
            "kb_names": kb_names,
            "total_chunks": total_chunks,
        }

        if not hits:
            reply_text = (
                "当前尚未上传任何文档到知识库，无法进行检索问答。"
                "请先在知识库页面上传 doc/docx/pdf/xls/xlsx/csv/txt 等格式的文档，"
                "让系统完成向量化后再提问。"
            )
            return {"answer": reply_text, "hits": [], "kb": kb_stat}

        max_score = max([h["score"] for h in hits]) if hits else 0.0

        context_parts = []
        for i, hit in enumerate(hits, 1):
            page = hit.get("page_info") or f"片段{i}"
            kb_ref = hit.get("kb_id", "")
            context_parts.append(
                f"[片段 {i}] 相似度 {hit['score']:.3f}；知识库ID：{kb_ref}；位置：{page}\n"
                f"{hit['content']}"
            )
        context_block = "\n\n".join(context_parts)

        low_relevance_note = ""
        if max_score < 0.08:
            low_relevance_note = (
                f"【系统提示】检索到的片段与问题相似度较低（最高 {max_score:.3f}），"
                "请在回答中明确告知用户：未能在知识库中找到足够相关的内容来完整回答该问题。"
            )
        elif max_score < 0.15:
            low_relevance_note = (
                f"【系统提示】最高分片段的相似度为 {max_score:.3f}，"
                "请在回答中注明「部分内容来自知识库片段」，并在不能完整回答时明确说明。"
            )

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个跨知识库的问答助手。请严格依据下方「参考片段」回答用户问题。\n"
                    "【核心规则】\n"
                    "1) 只使用片段中明确提到的信息，不编造、不推断、不引用片段外的常识；\n"
                    "2) 若片段内容不足以回答问题，说明「在知识库中未找到足够相关内容」，并列出最接近的片段要点；\n"
                    "3) 回答使用中文，结构清晰，语言自然。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"### 用户知识库：共 {len(all_kbs)} 个知识库，{total_chunks} 条向量化片段\n"
                    f"知识库列表：{kb_names}\n"
                    f"### 检索总体相关度：最高相似度 {max_score:.3f}（满分 1.00）\n"
                    + (f"\n{low_relevance_note}\n" if low_relevance_note else "\n")
                    + f"### 参考片段（已按相关度排序）：\n{context_block}\n\n"
                    f"### 用户问题：\n{user_query}\n\n"
                    "请先评估片段与问题的相关性，再基于片段给出中文回答。"
                ),
            },
        ]

        try:
            reply = chat_with_agent(messages, use_tools=False)
        except Exception as e:
            reply = f"（调用 AI 模型时出现异常：{e}）"
        return {"answer": reply or "", "hits": hits, "kb": kb_stat}

    # ---------- 工具函数 ----------
    @staticmethod
    def _kb_to_dict(kb: KnowledgeBase) -> dict:
        return {
            "id": kb.id,
            "user_id": kb.user_id,
            "name": kb.name,
            "description": kb.description or "",
            "doc_count": kb.doc_count or 0,
            "chunk_count": kb.chunk_count or 0,
            "create_time": kb.create_time.strftime("%Y-%m-%d %H:%M:%S") if kb.create_time else None,
            "update_time": kb.update_time.strftime("%Y-%m-%d %H:%M:%S") if kb.update_time else None,
        }

    @staticmethod
    def _doc_to_dict(doc: KbDocument) -> dict:
        return {
            "id": doc.id,
            "kb_id": doc.kb_id,
            "user_id": doc.user_id,
            "original_name": doc.original_name,
            "file_size": doc.file_size,
            "file_type": doc.file_type,
            "status": doc.status,
            "status_msg": doc.status_msg or "",
            "chunk_count": doc.chunk_count or 0,
            "create_time": doc.create_time.strftime("%Y-%m-%d %H:%M:%S") if doc.create_time else None,
            "update_time": doc.update_time.strftime("%Y-%m-%d %H:%M:%S") if doc.update_time else None,
        }
