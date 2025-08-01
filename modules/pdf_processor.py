import fitz  # PyMuPDF
import pdfplumber
import easyocr
import numpy as np
from PIL import Image
import io
import re
from typing import Dict, List, Any, Optional

class PDFTextExtractor:
    def __init__(self):
        self.reader = easyocr.Reader(['en'])
    
    def preserve_inline_math(self, text: str) -> str:
        """Preserve inline math expressions by wrapping them in $$ tags"""
        math_pattern = r'([A-Za-z0-9\s\^\=\+\-\*/]+=[A-Za-z0-9\s\^\=\+\-\*/]+)'
        matches = re.findall(math_pattern, text)
        for match in matches:
            text = text.replace(match, f"$$ {match.strip()} $$")
        return text
    
    def ocr_image(self, img_bytes: bytes) -> str:
        """Extract text from image using EasyOCR"""
        try:
            image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            img_array = np.array(image)
            result = self.reader.readtext(img_array, detail=0)
            return " ".join(result)
        except Exception as e:
            print(f"OCR error: {str(e)}")
            return ""
    
    def detect_content_types(self, pdf_page, plumber_page) -> Dict[str, bool]:
        """Detect different types of content on a page"""
        types = {
            'has_text': False,
            'has_table': False,
            'has_image': False,
            'has_formula': False
        }
        
        # Check for text content
        text = pdf_page.get_text()
        if len(text.strip()) > 50:
            types['has_text'] = True
        
        # Check for tables
        try:
            tables = plumber_page.extract_tables()
            if tables and len(tables) > 0 and len(tables[0]) > 0:
                types['has_table'] = True
        except Exception:
            pass
        
        # Check for images and formulas
        images = pdf_page.get_images(full=True)
        if images:
            types['has_image'] = True
            for img in images:
                try:
                    xref = img[0]
                    pix = fitz.Pixmap(pdf_page.parent, xref)
                    ocr_text = self.ocr_image(pix.tobytes("png"))
                    if any(sym in ocr_text for sym in ["=", "∑", "π", "+", "−", "^", "/", "*"]):
                        types['has_formula'] = True
                    pix = None  # Free memory
                except Exception as e:
                    print(f"Error processing image: {str(e)}")
                    continue
        
        return types
    
    def process_page(self, pdf_page, plumber_page) -> Dict[str, Any]:
        """Process a single PDF page and extract all content"""
        content = {}
        types = self.detect_content_types(pdf_page, plumber_page)
        content['content_type'] = types
        
        # Extract and process text
        text = pdf_page.get_text()
        if types['has_text']:
            preserved_text = self.preserve_inline_math(text)
            content['text'] = preserved_text
        else:
            content['text'] = ""
        
        # Extract tables
        if types['has_table']:
            try:
                tables = plumber_page.extract_tables()
                content['tables'] = tables
            except Exception:
                content['tables'] = []
        else:
            content['tables'] = []
        
        # Extract images and OCR
        if types['has_image']:
            images = []
            for img in pdf_page.get_images(full=True):
                try:
                    xref = img[0]
                    pix = fitz.Pixmap(pdf_page.parent, xref)
                    img_bytes = pix.tobytes("png")
                    ocr_text = self.ocr_image(img_bytes)
                    images.append({'ocr_text': ocr_text})
                    pix = None  # Free memory
                except Exception as e:
                    print(f"Error processing image: {str(e)}")
                    continue
            content['images'] = images
        else:
            content['images'] = []
        
        return content
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """Extract text and metadata from PDF file"""
        all_text = []
        all_pages_data = []
        
        try:
            with fitz.open(file_path) as pdf, pdfplumber.open(file_path) as plumber:
                page_count = len(pdf)
                
                for i in range(page_count):
                    print(f"Processing page {i + 1}...")
                    page_data = self.process_page(pdf[i], plumber.pages[i])
                    all_pages_data.append(page_data)
                    
                    # Collect all text
                    page_text = page_data['text']
                    
                    # Add OCR text from images
                    for img in page_data['images']:
                        if img['ocr_text'].strip():
                            page_text += "\n" + img['ocr_text']
                    
                    # Add table text (simple conversion)
                    for table in page_data['tables']:
                        if table:
                            for row in table:
                                if row:
                                    table_text = " | ".join([str(cell) if cell else "" for cell in row])
                                    page_text += "\n" + table_text
                    
                    all_text.append(page_text)
                
                combined_text = "\n\n".join(all_text)
                
                return {
                    'text': combined_text,
                    'page_count': page_count,
                    'pages_data': all_pages_data
                }
                
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")