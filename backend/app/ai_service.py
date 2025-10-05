from typing import List, Optional
import asyncio
import logging
from app.config import settings

# Lazy imports for Gemini AI only
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
    """AI service for question answering (embedding functionality removed)"""
    
    def __init__(self):
        self.gemini_client = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize AI models"""
        try:
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
            self.gemini_client = None

    async def generate_answer(self, question: str, context_documents: List[str]) -> tuple[str, float]:
        """Generate answer using Gemini AI based on context documents"""
        try:
            logger.info(f"Generating answer for question: {question[:50]}...")
            logger.info(f"Gemini client available: {self.gemini_client is not None}")
            logger.info(f"GEMINI_AVAILABLE: {GEMINI_AVAILABLE}")
            logger.info(f"API Key configured: {bool(settings.GEMINI_API_KEY)}")
            
            if not self.gemini_client or not GEMINI_AVAILABLE:
                logger.warning("Falling back to simple answer generation")
                # Fallback to simple context-based answer
                return await self._generate_simple_answer(question, context_documents)
            
            # Prepare context from documents
            context = "\n\n".join([f"Tài liệu {i+1}:\n{doc}" for i, doc in enumerate(context_documents)])
            logger.info(f"Context length: {len(context)} characters")
            
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
            
            logger.info(f"Calling Gemini with model: {settings.GEMINI_MODEL}")
            
            # Generate content with Gemini
            try:
                response = await asyncio.to_thread(
                    self.gemini_client.models.generate_content,
                    model=settings.GEMINI_MODEL,
                    contents=contents,
                    config=generate_content_config,
                )
                
                logger.info(f"Gemini response received. Response object: {type(response)}")
                logger.info(f"Response attributes: {dir(response) if response else 'None'}")
                
                if response:
                    logger.info(f"Has text attribute: {hasattr(response, 'text')}")
                    if hasattr(response, 'text'):
                        logger.info(f"Text content: '{response.text}'")
                        logger.info(f"Text is None: {response.text is None}")
                        logger.info(f"Text is empty: {not response.text}")
                    
                    # Try different ways to get the response
                    if hasattr(response, 'candidates') and response.candidates:
                        logger.info(f"Number of candidates: {len(response.candidates)}")
                        candidate = response.candidates[0]
                        logger.info(f"Candidate attributes: {dir(candidate) if candidate else 'None'}")
                        
                        if hasattr(candidate, 'content') and candidate.content:
                            logger.info(f"Content attributes: {dir(candidate.content)}")
                            if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                part = candidate.content.parts[0]
                                if hasattr(part, 'text') and part.text:
                                    answer = part.text.strip()
                                    logger.info(f"Got answer from candidate.content.parts[0].text: {len(answer)} chars")
                                else:
                                    logger.warning("candidate.content.parts[0] has no text")
                            else:
                                logger.warning("candidate.content has no parts")
                        else:
                            logger.warning("candidate has no content")
                            
                        # Check if content was blocked
                        if hasattr(candidate, 'finish_reason'):
                            logger.info(f"Finish reason: {candidate.finish_reason}")
                            
                        if hasattr(candidate, 'safety_ratings'):
                            logger.info(f"Safety ratings: {candidate.safety_ratings}")
                            
                    else:
                        logger.warning("Response has no candidates")
                        
                    # Check prompt feedback for safety issues
                    if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                        logger.info(f"Prompt feedback: {response.prompt_feedback}")
                    
                    # If we didn't get an answer, fall back to simple processing
                    if 'answer' not in locals():
                        logger.warning("No answer extracted from Gemini, falling back to simple answer")
                        return await self._generate_simple_answer(question, context_documents)
                
            except Exception as api_error:
                logger.error(f"Gemini API call failed: {str(api_error)}")
                logger.error(f"API Error type: {type(api_error).__name__}")
                raise api_error
            
            if response and hasattr(response, 'text') and response.text:
                answer = response.text.strip()
                logger.info(f"Generated answer length: {len(answer)}")
            elif 'answer' not in locals():
                logger.warning("Gemini response was empty or invalid")
                answer = "Gemini đã phản hồi nhưng không có nội dung."
            
            confidence = 0.8  # Default confidence for Gemini responses
            
            return answer, confidence
            
        except Exception as e:
            logger.error(f"Failed to generate answer with Gemini: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
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
        """Generate a simple answer when Gemini is not available"""
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