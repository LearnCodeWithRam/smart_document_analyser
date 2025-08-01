# main.py
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from typing import Dict, List, Any
import tempfile
import os
from modules.pdf_processor import PDFTextExtractor
from modules.math_extractor import MathExpressionExtractor
from modules.ner_processor import NERProcessor
from modules.summarizer import TextSummarizer
from pydantic import BaseModel
import gc
import traceback

app = FastAPI(
    title="AI Document Analyzer",
    description="Extract text, math expressions, entities, and summaries from PDF documents",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize template rendering from the 'templates' directory
templates = Jinja2Templates(directory="templates")


class AnalysisResponse(BaseModel):
    text_content: str
    highlighted_text: str  # New field for NER highlighted text
    math_expressions: List[str]
    named_entities: Dict[str, List[str]]
    summary: str
    page_count: int
    word_count: int

# Initialize processors with error handling
try:
    pdf_extractor = PDFTextExtractor()
    print("✓ PDF Extractor initialized successfully")
except Exception as e:
    print(f"✗ Error initializing PDF Extractor: {str(e)}")
    pdf_extractor = None

try:
    math_extractor = MathExpressionExtractor()
    print("✓ Math Extractor initialized successfully")
except Exception as e:
    print(f"✗ Error initializing Math Extractor: {str(e)}")
    math_extractor = None

try:
    ner_processor = NERProcessor()
    print("✓ NER Processor initialized successfully")
except Exception as e:
    print(f"✗ Error initializing NER Processor: {str(e)}")
    ner_processor = None

try:
    summarizer = TextSummarizer()
    print("✓ Text Summarizer initialized successfully")
except Exception as e:
    print(f"✗ Error initializing Text Summarizer: {str(e)}")
    summarizer = None

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    components_status = {
        "pdf_extractor": pdf_extractor is not None,
        "math_extractor": math_extractor is not None,
        "ner_processor": ner_processor is not None,
        "summarizer": summarizer is not None
    }
    
    return {
        "status": "healthy" if all(components_status.values()) else "partial",
        "components": components_status
    }

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_document(file: UploadFile = File(...)):
    """
    Analyze a PDF document and extract text, math expressions, entities, and summary
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    if not pdf_extractor:
        raise HTTPException(status_code=500, detail="PDF extraction service is not available")
    
    tmp_file_path = None
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        print(f"Processing file: {file.filename} ({len(content)} bytes)")
        
        # Extract text from PDF
        extracted_data = pdf_extractor.extract_text(tmp_file_path)
        text_content = extracted_data['text']
        page_count = extracted_data['page_count']
        
        if not text_content.strip():
            raise HTTPException(status_code=400, detail="No text found in the PDF")
        
        print(f"Extracted {len(text_content)} characters from {page_count} pages")
        
        # Extract math expressions
        math_expressions = []
        if math_extractor:
            try:
                math_expressions = math_extractor.extract_expressions(text_content)
                print(f"Found {len(math_expressions)} mathematical expressions")
            except Exception as e:
                print(f"Math extraction error: {str(e)}")
                math_expressions = [f"Math extraction error: {str(e)}"]
        else:
            math_expressions = ["Math extraction service not available"]
        
        # Perform NER and highlight entities in text
        named_entities = {}
        highlighted_text = text_content  # Default to original text
        
        if ner_processor:
            try:
                named_entities = ner_processor.extract_entities(text_content)
                highlighted_text = ner_processor.highlight_entities_in_text(text_content)
                total_entities = sum(len(entities) for entities in named_entities.values() if isinstance(entities, list))
                print(f"Extracted {total_entities} named entities and highlighted text")
            except Exception as e:
                print(f"NER extraction error: {str(e)}")
                named_entities = {"error": [f"NER extraction error: {str(e)}"]}
        else:
            named_entities = {"error": ["NER service not available"]}
        
        # Generate summary with key points and facts
        summary = ""
        if summarizer:
            try:
                summary = summarizer.generate_summary(text_content, max_length=400, min_length=150)
                print(f"Generated comprehensive summary: {len(summary)} characters")
            except Exception as e:
                print(f"Summarization error: {str(e)}")
                summary = f"Summarization error: {str(e)}"
        else:
            summary = "Summarization service not available"
        
        # Calculate word count
        word_count = len(text_content.split())
        
        # Force garbage collection to free memory
        gc.collect()
        
        return AnalysisResponse(
            text_content=text_content,
            highlighted_text=highlighted_text,
            math_expressions=math_expressions,
            named_entities=named_entities,
            summary=summary,
            page_count=page_count,
            word_count=word_count
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")
    
    finally:
        # Clean up temporary file
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.unlink(tmp_file_path)
                print(f"Cleaned up temporary file: {tmp_file_path}")
            except Exception as e:
                print(f"Error cleaning up temporary file: {str(e)}")

@app.post("/extract-text")
async def extract_text_only(file: UploadFile = File(...)):
    """Extract only text content from PDF"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    if not pdf_extractor:
        raise HTTPException(status_code=500, detail="PDF extraction service is not available")
    
    tmp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        print(f"Extracting text from: {file.filename}")
        
        extracted_data = pdf_extractor.extract_text(tmp_file_path)
        
        # Generate highlighted text if NER processor is available
        highlighted_text = extracted_data['text']
        if ner_processor:
            try:
                highlighted_text = ner_processor.highlight_entities_in_text(extracted_data['text'])
            except Exception as e:
                print(f"Error highlighting entities: {str(e)}")
        
        # Force garbage collection
        gc.collect()
        
        return {
            "text_content": extracted_data['text'],
            "highlighted_text": highlighted_text,
            "page_count": extracted_data['page_count'],
            "word_count": len(extracted_data['text'].split())
        }
    
    except Exception as e:
        print(f"Text extraction error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error extracting text: {str(e)}")
    
    finally:
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.unlink(tmp_file_path)
            except Exception as e:
                print(f"Error cleaning up temporary file: {str(e)}")

@app.post("/extract-entities")
async def extract_entities_only(file: UploadFile = File(...)):
    """Extract only named entities from PDF"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    if not pdf_extractor:
        raise HTTPException(status_code=500, detail="PDF extraction service is not available")
    
    if not ner_processor:
        raise HTTPException(status_code=500, detail="NER service is not available")
    
    tmp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        print(f"Extracting entities from: {file.filename}")
        
        extracted_data = pdf_extractor.extract_text(tmp_file_path)
        named_entities = ner_processor.extract_entities(extracted_data['text'])
        
        # Force garbage collection
        gc.collect()
        
        return {"named_entities": named_entities}
    
    except Exception as e:
        print(f"Entity extraction error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error extracting entities: {str(e)}")
    
    finally:
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.unlink(tmp_file_path)
            except Exception as e:
                print(f"Error cleaning up temporary file: {str(e)}")

# Additional endpoint for math expressions only
@app.post("/extract-math")
async def extract_math_only(file: UploadFile = File(...)):
    """Extract only mathematical expressions from PDF"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    if not pdf_extractor:
        raise HTTPException(status_code=500, detail="PDF extraction service is not available")
    
    if not math_extractor:
        raise HTTPException(status_code=500, detail="Math extraction service is not available")
    
    tmp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        print(f"Extracting math expressions from: {file.filename}")
        
        extracted_data = pdf_extractor.extract_text(tmp_file_path)
        math_expressions = math_extractor.extract_expressions(extracted_data['text'])
        
        # Force garbage collection
        gc.collect()
        
        return {
            "math_expressions": math_expressions,
            "expression_count": len(math_expressions)
        }
    
    except Exception as e:
        print(f"Math extraction error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error extracting math expressions: {str(e)}")
    
    finally:
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.unlink(tmp_file_path)
            except Exception as e:
                print(f"Error cleaning up temporary file: {str(e)}")

# Additional endpoint for summary only
@app.post("/extract-summary")
async def extract_summary_only(file: UploadFile = File(...)):
    """Extract only summary from PDF"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    if not pdf_extractor:
        raise HTTPException(status_code=500, detail="PDF extraction service is not available")
    
    if not summarizer:
        raise HTTPException(status_code=500, detail="Summarization service is not available")
    
    tmp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        print(f"Extracting summary from: {file.filename}")
        
        extracted_data = pdf_extractor.extract_text(tmp_file_path)
        summary = summarizer.generate_summary(extracted_data['text'], max_length=400, min_length=150)
        
        # Force garbage collection
        gc.collect()
        
        return {
            "summary": summary,
            "original_word_count": len(extracted_data['text'].split()),
            "summary_word_count": len(summary.split())
        }
    
    except Exception as e:
        print(f"Summary extraction error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error extracting summary: {str(e)}")
    
    finally:
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.unlink(tmp_file_path)
            except Exception as e:
                print(f"Error cleaning up temporary file: {str(e)}")

if __name__ == "__main__":
    print("Starting AI Document Analyzer...")
    print("Checking component status:")
    print(f"  PDF Extractor: {'✓' if pdf_extractor else '✗'}")
    print(f"  Math Extractor: {'✓' if math_extractor else '✗'}")
    print(f"  NER Processor: {'✓' if ner_processor else '✗'}")
    print(f"  Text Summarizer: {'✓' if summarizer else '✗'}")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)









# # main.py
# from fastapi import FastAPI, File, UploadFile, HTTPException, Request
# from fastapi.responses import HTMLResponse
# from fastapi.templating import Jinja2Templates
# from fastapi.staticfiles import StaticFiles
# from fastapi import Depends
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.middleware.trustedhost import TrustedHostMiddleware
# from fastapi.responses import JSONResponse
# import uvicorn
# from typing import Dict, List, Any
# import tempfile
# import os
# from modules.pdf_processor import PDFTextExtractor
# from modules.math_extractor import MathExpressionExtractor
# from modules.ner_processor import NERProcessor
# from modules.summarizer import TextSummarizer
# from pydantic import BaseModel
# import gc
# import traceback

# app = FastAPI(
#     title="AI Document Analyzer",
#     description="Extract text, math expressions, entities, and summaries from PDF documents",
#     version="1.0.0"
# )

# # Add CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Initialize template rendering from the 'templates' directory
# templates = Jinja2Templates(directory="templates")


# class AnalysisResponse(BaseModel):
#     text_content: str
#     math_expressions: List[str]
#     named_entities: Dict[str, List[str]]
#     summary: str
#     page_count: int
#     word_count: int

# # Initialize processors with error handling
# try:
#     pdf_extractor = PDFTextExtractor()
#     print("✓ PDF Extractor initialized successfully")
# except Exception as e:
#     print(f"✗ Error initializing PDF Extractor: {str(e)}")
#     pdf_extractor = None

# try:
#     math_extractor = MathExpressionExtractor()
#     print("✓ Math Extractor initialized successfully")
# except Exception as e:
#     print(f"✗ Error initializing Math Extractor: {str(e)}")
#     math_extractor = None

# try:
#     ner_processor = NERProcessor()
#     print("✓ NER Processor initialized successfully")
# except Exception as e:
#     print(f"✗ Error initializing NER Processor: {str(e)}")
#     ner_processor = None

# try:
#     summarizer = TextSummarizer()
#     print("✓ Text Summarizer initialized successfully")
# except Exception as e:
#     print(f"✗ Error initializing Text Summarizer: {str(e)}")
#     summarizer = None

# @app.get("/", response_class=HTMLResponse)
# async def root(request: Request):
#     return templates.TemplateResponse("index.html", {"request": request})

# @app.get("/health")
# async def health_check():
#     components_status = {
#         "pdf_extractor": pdf_extractor is not None,
#         "math_extractor": math_extractor is not None,
#         "ner_processor": ner_processor is not None,
#         "summarizer": summarizer is not None
#     }
    
#     return {
#         "status": "healthy" if all(components_status.values()) else "partial",
#         "components": components_status
#     }

# @app.post("/analyze", response_model=AnalysisResponse)
# async def analyze_document(file: UploadFile = File(...)):
#     """
#     Analyze a PDF document and extract text, math expressions, entities, and summary
#     """
#     if not file.filename.lower().endswith('.pdf'):
#         raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
#     if not pdf_extractor:
#         raise HTTPException(status_code=500, detail="PDF extraction service is not available")
    
#     tmp_file_path = None
#     try:
#         # Create temporary file
#         with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
#             content = await file.read()
#             tmp_file.write(content)
#             tmp_file_path = tmp_file.name
        
#         print(f"Processing file: {file.filename} ({len(content)} bytes)")
        
#         # Extract text from PDF
#         extracted_data = pdf_extractor.extract_text(tmp_file_path)
#         text_content = extracted_data['text']
#         page_count = extracted_data['page_count']
        
#         if not text_content.strip():
#             raise HTTPException(status_code=400, detail="No text found in the PDF")
        
#         print(f"Extracted {len(text_content)} characters from {page_count} pages")
        
#         # Extract math expressions
#         math_expressions = []
#         if math_extractor:
#             try:
#                 math_expressions = math_extractor.extract_expressions(text_content)
#                 print(f"Found {len(math_expressions)} mathematical expressions")
#             except Exception as e:
#                 print(f"Math extraction error: {str(e)}")
#                 math_expressions = [f"Math extraction error: {str(e)}"]
#         else:
#             math_expressions = ["Math extraction service not available"]
        
#         # Perform NER
#         named_entities = {}
#         if ner_processor:
#             try:
#                 named_entities = ner_processor.extract_entities(text_content)
#                 total_entities = sum(len(entities) for entities in named_entities.values() if isinstance(entities, list))
#                 print(f"Extracted {total_entities} named entities")
#             except Exception as e:
#                 print(f"NER extraction error: {str(e)}")
#                 named_entities = {"error": [f"NER extraction error: {str(e)}"]}
#         else:
#             named_entities = {"error": ["NER service not available"]}
        
#         # Generate summary
#         summary = ""
#         if summarizer:
#             try:
#                 summary = summarizer.generate_summary(text_content, max_length=200, min_length=50)
#                 print(f"Generated summary: {len(summary)} characters")
#             except Exception as e:
#                 print(f"Summarization error: {str(e)}")
#                 summary = f"Summarization error: {str(e)}"
#         else:
#             summary = "Summarization service not available"
        
#         # Calculate word count
#         word_count = len(text_content.split())
        
#         # Force garbage collection to free memory
#         gc.collect()
        
#         return AnalysisResponse(
#             text_content=text_content,
#             math_expressions=math_expressions,
#             named_entities=named_entities,
#             summary=summary,
#             page_count=page_count,
#             word_count=word_count
#         )
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         print(f"Unexpected error: {str(e)}")
#         print(traceback.format_exc())
#         raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")
    
#     finally:
#         # Clean up temporary file
#         if tmp_file_path and os.path.exists(tmp_file_path):
#             try:
#                 os.unlink(tmp_file_path)
#                 print(f"Cleaned up temporary file: {tmp_file_path}")
#             except Exception as e:
#                 print(f"Error cleaning up temporary file: {str(e)}")

# @app.post("/extract-text")
# async def extract_text_only(file: UploadFile = File(...)):
#     """Extract only text content from PDF"""
#     if not file.filename.lower().endswith('.pdf'):
#         raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
#     if not pdf_extractor:
#         raise HTTPException(status_code=500, detail="PDF extraction service is not available")
    
#     tmp_file_path = None
#     try:
#         with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
#             content = await file.read()
#             tmp_file.write(content)
#             tmp_file_path = tmp_file.name
        
#         print(f"Extracting text from: {file.filename}")
        
#         extracted_data = pdf_extractor.extract_text(tmp_file_path)
        
#         # Force garbage collection
#         gc.collect()
        
#         return {
#             "text_content": extracted_data['text'],
#             "page_count": extracted_data['page_count'],
#             "word_count": len(extracted_data['text'].split())
#         }
    
#     except Exception as e:
#         print(f"Text extraction error: {str(e)}")
#         print(traceback.format_exc())
#         raise HTTPException(status_code=500, detail=f"Error extracting text: {str(e)}")
    
#     finally:
#         if tmp_file_path and os.path.exists(tmp_file_path):
#             try:
#                 os.unlink(tmp_file_path)
#             except Exception as e:
#                 print(f"Error cleaning up temporary file: {str(e)}")

# @app.post("/extract-entities")
# async def extract_entities_only(file: UploadFile = File(...)):
#     """Extract only named entities from PDF"""
#     if not file.filename.lower().endswith('.pdf'):
#         raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
#     if not pdf_extractor:
#         raise HTTPException(status_code=500, detail="PDF extraction service is not available")
    
#     if not ner_processor:
#         raise HTTPException(status_code=500, detail="NER service is not available")
    
#     tmp_file_path = None
#     try:
#         with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
#             content = await file.read()
#             tmp_file.write(content)
#             tmp_file_path = tmp_file.name
        
#         print(f"Extracting entities from: {file.filename}")
        
#         extracted_data = pdf_extractor.extract_text(tmp_file_path)
#         named_entities = ner_processor.extract_entities(extracted_data['text'])
        
#         # Force garbage collection
#         gc.collect()
        
#         return {"named_entities": named_entities}
    
#     except Exception as e:
#         print(f"Entity extraction error: {str(e)}")
#         print(traceback.format_exc())
#         raise HTTPException(status_code=500, detail=f"Error extracting entities: {str(e)}")
    
#     finally:
#         if tmp_file_path and os.path.exists(tmp_file_path):
#             try:
#                 os.unlink(tmp_file_path)
#             except Exception as e:
#                 print(f"Error cleaning up temporary file: {str(e)}")

# # Additional endpoint for math expressions only
# @app.post("/extract-math")
# async def extract_math_only(file: UploadFile = File(...)):
#     """Extract only mathematical expressions from PDF"""
#     if not file.filename.lower().endswith('.pdf'):
#         raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
#     if not pdf_extractor:
#         raise HTTPException(status_code=500, detail="PDF extraction service is not available")
    
#     if not math_extractor:
#         raise HTTPException(status_code=500, detail="Math extraction service is not available")
    
#     tmp_file_path = None
#     try:
#         with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
#             content = await file.read()
#             tmp_file.write(content)
#             tmp_file_path = tmp_file.name
        
#         print(f"Extracting math expressions from: {file.filename}")
        
#         extracted_data = pdf_extractor.extract_text(tmp_file_path)
#         math_expressions = math_extractor.extract_expressions(extracted_data['text'])
        
#         # Force garbage collection
#         gc.collect()
        
#         return {
#             "math_expressions": math_expressions,
#             "expression_count": len(math_expressions)
#         }
    
#     except Exception as e:
#         print(f"Math extraction error: {str(e)}")
#         print(traceback.format_exc())
#         raise HTTPException(status_code=500, detail=f"Error extracting math expressions: {str(e)}")
    
#     finally:
#         if tmp_file_path and os.path.exists(tmp_file_path):
#             try:
#                 os.unlink(tmp_file_path)
#             except Exception as e:
#                 print(f"Error cleaning up temporary file: {str(e)}")

# # Additional endpoint for summary only
# @app.post("/extract-summary")
# async def extract_summary_only(file: UploadFile = File(...)):
#     """Extract only summary from PDF"""
#     if not file.filename.lower().endswith('.pdf'):
#         raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
#     if not pdf_extractor:
#         raise HTTPException(status_code=500, detail="PDF extraction service is not available")
    
#     if not summarizer:
#         raise HTTPException(status_code=500, detail="Summarization service is not available")
    
#     tmp_file_path = None
#     try:
#         with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
#             content = await file.read()
#             tmp_file.write(content)
#             tmp_file_path = tmp_file.name
        
#         print(f"Extracting summary from: {file.filename}")
        
#         extracted_data = pdf_extractor.extract_text(tmp_file_path)
#         summary = summarizer.generate_summary(extracted_data['text'], max_length=200, min_length=50)
        
#         # Force garbage collection
#         gc.collect()
        
#         return {
#             "summary": summary,
#             "original_word_count": len(extracted_data['text'].split()),
#             "summary_word_count": len(summary.split())
#         }
    
#     except Exception as e:
#         print(f"Summary extraction error: {str(e)}")
#         print(traceback.format_exc())
#         raise HTTPException(status_code=500, detail=f"Error extracting summary: {str(e)}")
    
#     finally:
#         if tmp_file_path and os.path.exists(tmp_file_path):
#             try:
#                 os.unlink(tmp_file_path)
#             except Exception as e:
#                 print(f"Error cleaning up temporary file: {str(e)}")

# if __name__ == "__main__":
#     print("Starting AI Document Analyzer...")
#     print("Checking component status:")
#     print(f"  PDF Extractor: {'✓' if pdf_extractor else '✗'}")
#     print(f"  Math Extractor: {'✓' if math_extractor else '✗'}")
#     print(f"  NER Processor: {'✓' if ner_processor else '✗'}")
#     print(f"  Text Summarizer: {'✓' if summarizer else '✗'}")
    
#     uvicorn.run(app, host="0.0.0.0", port=8000)