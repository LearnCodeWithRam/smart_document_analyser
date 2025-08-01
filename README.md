# 🤖 smart_document_analyser
> **AI Docs Analyser is an intelligent document processing tool that extracts, classifies, and understands content from PDFs, images, and text files using OCR and NLP. It automates data extraction and tagging, enabling smarter workflows for legal, financial, and business document analysis.**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.68+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](Dockerfile)

## 🌟 Features

- **📄 PDF Text Extraction**: Extract clean text content from PDF documents
- **🏷️ Named Entity Recognition (NER)**: Identify and categorize entities like people, organizations, dates, locations
- **🔢 Mathematical Expression Detection**: Extract and highlight mathematical formulas and expressions
- **📋 AI-Powered Summarization**: Generate intelligent summaries of document content
- **🎨 Interactive Web Interface**: Beautiful, responsive UI with drag-and-drop file upload
- **💾 Export Results**: Save analysis results as formatted text documents
- **⚡ Fast Processing**: Optimized for quick document analysis
- **🐳 Docker Support**: Easy deployment with containerization

## 🎮 Live Demo

🌐 **[Try it live here!](http://115.241.186.203:9090/)**

## 📸 Screenshots

### Main Interface
![Main Interface](screenshots/main-interface.png)
*Clean, intuitive interface with drag-and-drop PDF upload*

### Analysis Results
![Analysis Results](screenshots/analysis-results.png)
*Comprehensive analysis showing extracted text, entities, and mathematical expressions*

### Named Entity Recognition
![Named Entities](screenshots/named-entities.png)
*Categorized named entities with color-coded highlighting*

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- pip package manager
- Git

### Local Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ai-document-analyzer
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python main.py
   ```

5. **Open your browser**
   Navigate to `http://localhost:8000`

### 🐳 Docker Installation

1. **Build the Docker image**
   ```bash
   docker build -t ai-document-analyzer .
   ```

2. **Run the container**
   ```bash
   docker run -p 8000:8000 ai-document-analyzer
   ```

3. **Access the application**
   Open `http://localhost:8000` in your browser

### Docker Compose (Recommended)

1. **Create docker-compose.yml**
   ```yaml
   version: '3.8'
   services:
     ai-document-analyzer:
       build: .
       ports:
         - "8000:8000"
       volumes:
         - ./uploads:/app/uploads
       restart: unless-stopped
   ```

2. **Run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

## 📁 Project Structure

```
ai-document-analyzer/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose configuration
├── README.md              # Project documentation
├── templates/
│   └── index.html         # Frontend interface
├── modules/
│   ├── __init__.py
│   ├── pdf_processor.py   # PDF text extraction
│   ├── math_extractor.py  # Mathematical expression detection
│   ├── ner_processor.py   # Named Entity Recognition
│   └── summarizer.py      # Text summarization
├── static/               # Static assets (CSS, JS, images)
├── uploads/              # Temporary file storage
└── screenshots/          # Demo screenshots
```

## 🔧 API Documentation

### Endpoints

#### **POST /analyze**
Complete document analysis with all features
- **Input**: PDF file (multipart/form-data)
- **Output**: JSON with text, entities, math expressions, and summary

#### **POST /extract-text**
Extract only text content
- **Input**: PDF file
- **Output**: JSON with extracted text and metadata

#### **POST /extract-entities**
Extract only named entities
- **Input**: PDF file
- **Output**: JSON with categorized entities

#### **POST /extract-math**
Extract only mathematical expressions
- **Input**: PDF file
- **Output**: JSON with mathematical expressions

#### **POST /extract-summary**
Generate only document summary
- **Input**: PDF file
- **Output**: JSON with generated summary

#### **GET /health**
Health check endpoint
- **Output**: Service status and component availability

### Example API Usage

```python
import requests

# Complete analysis
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/analyze',
        files={'file': f}
    )
    result = response.json()
    print(result['summary'])
```

## ⚙️ Configuration

### Environment Variables

```bash
# Application settings
HOST=0.0.0.0
PORT=8000
DEBUG=False

# Processing settings
MAX_FILE_SIZE=52428800  # 50MB
TEMP_DIR=/tmp/uploads

# Model settings (optional)
NER_MODEL=en_core_web_sm
SUMMARIZER_MODEL=facebook/bart-large-cnn
```

### Resource Requirements

- **Minimum RAM**: 2GB
- **Recommended RAM**: 4GB+
- **CPU**: 2+ cores recommended
- **Disk Space**: 1GB+ for models and temporary files

## 🔍 Supported Features

### File Types
- ✅ PDF documents
- ✅ Text-based PDFs
- ✅ Scanned PDFs (with OCR)
- ❌ Protected/encrypted PDFs

### Named Entity Types
- **PERSON**: People's names
- **ORG**: Organizations, companies
- **GPE**: Geopolitical entities (countries, cities)
- **DATE**: Dates and time expressions
- **MONEY**: Monetary values
- **PERCENT**: Percentages
- **PRODUCT**: Products and services
- **EVENT**: Named events
- **WORK_OF_ART**: Titles of works
- **LAW**: Legal documents
- **LANGUAGE**: Languages

### Mathematical Expressions
- Equations and formulas
- Statistical expressions
- Mathematical notation
- Variables and constants

## 🚀 Deployment

### Production Deployment

1. **Using Docker (Recommended)**
   ```bash
   # Build production image
   docker build -t ai-document-analyzer:latest .
   
   # Run with environment variables
   docker run -d \
     -p 80:8000 \
     -e HOST=0.0.0.0 \
     -e PORT=8000 \
     --name ai-analyzer \
     ai-document-analyzer:latest
   ```

2. **Using systemd (Linux)**
   ```bash
   # Create service file
   sudo nano /etc/systemd/system/ai-analyzer.service
   
   # Add service configuration
   [Unit]
   Description=AI Document Analyzer
   After=network.target
   
   [Service]
   Type=simple
   User=www-data
   WorkingDirectory=/opt/ai-document-analyzer
   ExecStart=/opt/ai-document-analyzer/venv/bin/python main.py
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   
   # Enable and start service
   sudo systemctl enable ai-analyzer
   sudo systemctl start ai-analyzer
   ```

3. **Using Nginx (Reverse Proxy)**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

### Cloud Deployment Options

- **AWS EC2**: Use the provided Docker image
- **Google Cloud Run**: Deploy as serverless container
- **Heroku**: Use Docker deployment
- **DigitalOcean Droplets**: Docker or direct installation

## 🧪 Testing

### Run Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/

# Run with coverage
pytest --cov=modules tests/
```

### Manual Testing
1. Upload a sample PDF through the web interface
2. Verify all components are working in `/health` endpoint
3. Test API endpoints with curl or Postman

## 🐛 Troubleshooting

### Common Issues

1. **"PDF extraction service not available"**
   - Install required system packages: `poppler-utils`, `tesseract`
   - Check PDF file is not corrupted or password-protected

2. **Memory errors during processing**
   - Increase available RAM
   - Process smaller files
   - Adjust model parameters

3. **Slow processing**
   - Use GPU acceleration if available
   - Optimize model loading
   - Implement caching

4. **Docker build fails**
   - Ensure sufficient disk space
   - Check internet connectivity
   - Use Docker build cache

### Debug Mode
```bash
# Enable debug logging
export DEBUG=True
python main.py
```

## 📋 Requirements

### Python Dependencies
```txt
fastapi>=0.68.0
uvicorn[standard]>=0.15.0
python-multipart>=0.0.5
jinja2>=3.0.0
aiofiles>=0.7.0
python-pdf2image>=1.16.0
pytesseract>=0.3.8
spacy>=3.4.0
transformers>=4.21.0
torch>=1.12.0
numpy>=1.21.0
pandas>=1.3.0
Pillow>=8.3.0
```

### System Dependencies
- `poppler-utils`: PDF processing
- `tesseract-ocr`: OCR functionality
- `gcc`: Compilation tools
- `libffi-dev`: Foreign function interface
- Various audio/video libraries for advanced processing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run code formatting
black .
isort .
flake8
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **spaCy**: Natural Language Processing
- **Transformers**: AI model implementations
- **FastAPI**: Modern web framework
- **PyTesseract**: OCR functionality
- **PDF2Image**: PDF processing

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Documentation**: [Wiki](https://github.com/your-repo/wiki)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)

## 🔄 Changelog

### v1.0.0 (Latest)
- ✅ Initial release
- ✅ PDF text extraction
- ✅ Named Entity Recognition
- ✅ Mathematical expression detection
- ✅ AI-powered summarization
- ✅ Web interface
- ✅ Docker support
- ✅ API documentation

---

**Made with ❤️ for document analysis and AI processing**
