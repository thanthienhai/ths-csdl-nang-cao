import fitz  # PyMuPDF
from docx import Document
import os
import tempfile
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Service for processing uploaded documents"""
    
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            doc = fitz.open(file_path)
            text = ""
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text += page.get_text() + "\n"
            doc.close()
            return text.strip()
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            raise
    
    @staticmethod
    def extract_text_from_docx(file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Failed to extract text from DOCX: {e}")
            raise
    
    @staticmethod
    def extract_text_from_txt(file_path: str) -> str:
        """Extract text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin1') as file:
                    return file.read().strip()
            except Exception as e:
                logger.error(f"Failed to extract text from TXT: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to extract text from TXT: {e}")
            raise
    
    @classmethod
    async def process_uploaded_file(cls, file_content: bytes, filename: str) -> tuple[str, str]:
        """Process uploaded file and extract text"""
        try:
            # Get file extension
            file_extension = os.path.splitext(filename)[1].lower()
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
                tmp_file.write(file_content)
                tmp_file_path = tmp_file.name
            
            try:
                # Extract text based on file type
                if file_extension == '.pdf':
                    extracted_text = cls.extract_text_from_pdf(tmp_file_path)
                elif file_extension in ['.doc', '.docx']:
                    extracted_text = cls.extract_text_from_docx(tmp_file_path)
                elif file_extension == '.txt':
                    extracted_text = cls.extract_text_from_txt(tmp_file_path)
                else:
                    raise ValueError(f"Unsupported file type: {file_extension}")
                
                return extracted_text, file_extension
                
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
                    
        except Exception as e:
            logger.error(f"Failed to process uploaded file {filename}: {e}")
            raise
    
    @staticmethod
    def generate_summary(text: str, max_length: int = 500) -> str:
        """Generate a simple summary of the text"""
        try:
            # Simple extractive summarization
            sentences = text.split('.')
            sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
            
            if not sentences:
                return text[:max_length] + "..." if len(text) > max_length else text
            
            # Take first few sentences up to max_length
            summary = ""
            for sentence in sentences:
                if len(summary + sentence) > max_length:
                    break
                summary += sentence + ". "
            
            return summary.strip() if summary else text[:max_length] + "..."
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return text[:max_length] + "..." if len(text) > max_length else text

# Create global document processor instance
document_processor = DocumentProcessor()