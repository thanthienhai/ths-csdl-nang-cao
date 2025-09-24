from typing import List, Optional
import numpy as np
import asyncio
import logging
from app.config import settings

# Lazy imports to avoid dependency issues
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"SentenceTransformers not available: {e}")
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Google Gemini not available: {e}")
    genai = None
    types = None
    GEMINI_AVAILABLE = False

logger = logging.getLogger(__name__)

class AIService:
    """AI service for embedding generation and question answering"""
    
    def __init__(self):
        self.sentence_transformer = None
        self.gemini_client = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize AI models"""
        try:
            # Initialize Sentence Transformer for embeddings
            if SENTENCE_TRANSFORMERS_AVAILABLE and SentenceTransformer:
                self.sentence_transformer = SentenceTransformer(settings.SENTENCE_TRANSFORMER_MODEL)
                logger.info(f"Loaded Sentence Transformer model: {settings.SENTENCE_TRANSFORMER_MODEL}")
            else:
                logger.warning("SentenceTransformers not available. Embedding functionality disabled.")
                self.sentence_transformer = None
            
            # Initialize Gemini client if API key is provided
            if GEMINI_AVAILABLE and settings.GEMINI_API_KEY:
                self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
                logger.info("Gemini client initialized")
            else:
                if not GEMINI_AVAILABLE:
                    logger.warning("Gemini not available. Install google-genai package.")
                else:
                    logger.warning("Gemini API key not provided. Q&A functionality will be limited.")
                self.gemini_client = None
                
        except Exception as e:
            logger.error(f"Failed to initialize AI models: {e}")
            # Don't raise exception, allow app to continue with limited functionality
            self.sentence_transformer = None
            self.gemini_client = None
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate vector embedding for text"""
        try:
            if not self.sentence_transformer:
                raise ValueError("Sentence Transformer model not available. Please install compatible versions.")
            
            # Generate embedding
            embedding = self.sentence_transformer.encode(text)
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            # Return a dummy embedding as fallback
            logger.warning("Returning dummy embedding. Install sentence-transformers for real embeddings.")
            return [0.0] * 384  # Standard dimension for MiniLM model
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        try:
            # Convert to numpy arrays
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0
    
    async def generate_answer(self, question: str, context_documents: List[str]) -> tuple[str, float]:
        """Generate answer using Gemini AI based on context documents"""
        try:
            if not self.gemini_client or not GEMINI_AVAILABLE:
                # Fallback to simple context-based answer
                return await self._generate_simple_answer(question, context_documents)
            
            # Prepare context from documents
            context = "\n\n".join([f"Tài liệu {i+1}:\n{doc}" for i, doc in enumerate(context_documents)])
            
            # Create prompt for Gemini
            prompt = f"""Dựa trên các tài liệu pháp luật sau đây, hãy trả lời câu hỏi một cách chính xác và súc tích.

Tài liệu tham khảo:
{context}

Câu hỏi: {question}

Trả lời (chỉ dựa trên các tài liệu được cung cấp):"""

            # Generate response using Gemini
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                    ],
                ),
            ]
            
            generate_content_config = types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=500,
            )
            
            # Generate content with Gemini
            response = await asyncio.to_thread(
                self.gemini_client.models.generate_content,
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=generate_content_config,
            )
            
            answer = response.text.strip() if response.text else "Không thể tạo phản hồi từ Gemini."
            confidence = 0.8  # Default confidence for Gemini responses
            
            return answer, confidence
            
        except Exception as e:
            logger.error(f"Failed to generate answer with Gemini: {e}")
            # Fallback to simple answer
            return await self._generate_simple_answer(question, context_documents)
    
    async def generate_answer_stream(self, question: str, context_documents: List[str]):
        """Generate answer using Gemini AI with streaming response"""
        try:
            if not self.gemini_client or not GEMINI_AVAILABLE:
                yield "Gemini client không được khởi tạo. Sử dụng phương thức trả lời đơn giản."
                simple_answer, _ = await self._generate_simple_answer(question, context_documents)
                yield simple_answer
                return
            
            # Prepare context from documents
            context = "\n\n".join([f"Tài liệu {i+1}:\n{doc}" for i, doc in enumerate(context_documents)])
            
            # Create prompt for Gemini
            prompt = f"""Dựa trên các tài liệu pháp luật sau đây, hãy trả lời câu hỏi một cách chính xác và súc tích.

Tài liệu tham khảo:
{context}

Câu hỏi: {question}

Trả lời (chỉ dựa trên các tài liệu được cung cấp):"""

            # Generate response using Gemini streaming
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                    ],
                ),
            ]
            
            generate_content_config = types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=500,
                thinking_config=types.ThinkingConfig(
                    thinking_budget=-1,
                ),
            )
            
            # Stream response from Gemini
            for chunk in self.gemini_client.models.generate_content_stream(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=generate_content_config,
            ):
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            logger.error(f"Failed to generate streaming answer with Gemini: {e}")
            yield f"Lỗi khi tạo phản hồi: {str(e)}"
    
    async def _generate_simple_answer(self, question: str, context_documents: List[str]) -> tuple[str, float]:
        """Generate a simple answer when OpenAI is not available"""
        try:
            # Simple keyword-based answer generation
            question_lower = question.lower()
            relevant_sentences = []
            
            for doc in context_documents:
                sentences = doc.split('.')
                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) > 20:  # Filter out very short sentences
                        # Check if sentence contains keywords from question
                        words_in_question = set(question_lower.split())
                        words_in_sentence = set(sentence.lower().split())
                        overlap = len(words_in_question.intersection(words_in_sentence))
                        
                        if overlap >= 2:  # At least 2 words overlap
                            relevant_sentences.append(sentence)
            
            if relevant_sentences:
                # Take the most relevant sentences
                answer = ". ".join(relevant_sentences[:3])  # Top 3 sentences
                confidence = 0.6
            else:
                answer = "Tôi không thể tìm thấy thông tin liên quan đến câu hỏi của bạn trong các tài liệu được cung cấp."
                confidence = 0.3
            
            return answer, confidence
            
        except Exception as e:
            logger.error(f"Failed to generate simple answer: {e}")
            return "Xin lỗi, tôi gặp lỗi khi xử lý câu hỏi của bạn.", 0.1

# Create global AI service instance
ai_service = AIService()