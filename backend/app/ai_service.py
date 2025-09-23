from sentence_transformers import SentenceTransformer
import openai
from typing import List, Optional
import numpy as np
import asyncio
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class AIService:
    """AI service for embedding generation and question answering"""
    
    def __init__(self):
        self.sentence_transformer = None
        self.openai_client = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize AI models"""
        try:
            # Initialize Sentence Transformer for embeddings
            self.sentence_transformer = SentenceTransformer(settings.SENTENCE_TRANSFORMER_MODEL)
            logger.info(f"Loaded Sentence Transformer model: {settings.SENTENCE_TRANSFORMER_MODEL}")
            
            # Initialize OpenAI client if API key is provided
            if settings.OPENAI_API_KEY:
                openai.api_key = settings.OPENAI_API_KEY
                self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("OpenAI client initialized")
            else:
                logger.warning("OpenAI API key not provided. Q&A functionality will be limited.")
                
        except Exception as e:
            logger.error(f"Failed to initialize AI models: {e}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate vector embedding for text"""
        try:
            if not self.sentence_transformer:
                raise ValueError("Sentence Transformer model not initialized")
            
            # Generate embedding
            embedding = self.sentence_transformer.encode(text)
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
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
        """Generate answer using LLM based on context documents"""
        try:
            if not self.openai_client:
                # Fallback to simple context-based answer
                return await self._generate_simple_answer(question, context_documents)
            
            # Prepare context from documents
            context = "\n\n".join([f"Document {i+1}:\n{doc}" for i, doc in enumerate(context_documents)])
            
            # Create prompt for the LLM
            prompt = f"""Based on the following legal documents, please answer the question accurately and concisely.

Context Documents:
{context}

Question: {question}

Answer (based only on the provided documents):"""

            # Generate response using OpenAI
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a legal expert assistant. Answer questions based only on the provided legal documents. If the answer is not in the documents, say so clearly."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            answer = response.choices[0].message.content.strip()
            confidence = 0.8  # Default confidence for OpenAI responses
            
            return answer, confidence
            
        except Exception as e:
            logger.error(f"Failed to generate answer with OpenAI: {e}")
            # Fallback to simple answer
            return await self._generate_simple_answer(question, context_documents)
    
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