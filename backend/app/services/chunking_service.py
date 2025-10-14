import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models import DocumentChunk, ChunkingRequest, ChunkingResponse

logger = logging.getLogger(__name__)

class ChunkingService:
    """Service for splitting documents into chunks for RAG"""
    
    def __init__(self):
        self.sentence_endings = r'[.!?]+(?=\s|$)'
        self.paragraph_separator = r'\n\s*\n'
    
    def recursive_text_splitter(
        self, 
        text: str, 
        chunk_size: int = 1000, 
        chunk_overlap: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Recursive text splitting similar to LangChain's RecursiveCharacterTextSplitter
        """
        separators = ["\n\n", "\n", ". ", " ", ""]
        chunks = []
        
        def _split_text_with_separator(text: str, separator: str) -> List[str]:
            if separator:
                return text.split(separator)
            else:
                return list(text)
        
        def _merge_splits(splits: List[str], separator: str) -> List[str]:
            """Merge splits into chunks of appropriate size"""
            chunks = []
            current_chunk = ""
            
            for split in splits:
                if len(current_chunk) + len(split) + len(separator) <= chunk_size:
                    if current_chunk:
                        current_chunk += separator + split
                    else:
                        current_chunk = split
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                        # Handle overlap
                        if chunk_overlap > 0 and len(current_chunk) > chunk_overlap:
                            current_chunk = current_chunk[-chunk_overlap:] + separator + split
                        else:
                            current_chunk = split
                    else:
                        # Split is too large, need to break it down further
                        current_chunk = split
            
            if current_chunk:
                chunks.append(current_chunk)
            
            return chunks
        
        def _split_text_recursive(text: str, separators: List[str]) -> List[str]:
            """Recursively split text using different separators"""
            if not separators:
                return [text]
            
            separator = separators[0]
            remaining_separators = separators[1:]
            
            splits = _split_text_with_separator(text, separator)
            
            # If we only got one split, try the next separator
            if len(splits) == 1:
                return _split_text_recursive(text, remaining_separators)
            
            # Merge splits into appropriate chunks
            merged_chunks = _merge_splits(splits, separator)
            
            # Recursively process chunks that are still too large
            final_chunks = []
            for chunk in merged_chunks:
                if len(chunk) > chunk_size and remaining_separators:
                    final_chunks.extend(_split_text_recursive(chunk, remaining_separators))
                else:
                    final_chunks.append(chunk)
            
            return final_chunks
        
        if not text.strip():
            return []
        
        text_chunks = _split_text_recursive(text, separators)
        
        # Create chunk objects with metadata
        start_pos = 0
        for i, chunk_text in enumerate(text_chunks):
            end_pos = start_pos + len(chunk_text)
            
            chunks.append({
                "chunk_index": i,
                "content": chunk_text.strip(),
                "content_length": len(chunk_text.strip()),
                "start_position": start_pos,
                "end_position": end_pos,
                "chunk_type": "text"
            })
            
            # Update start position for next chunk (accounting for overlap)
            start_pos = end_pos - chunk_overlap if chunk_overlap < len(chunk_text) else end_pos
        
        return chunks
    
    def sentence_splitter(self, text: str, chunk_size: int = 1000) -> List[Dict[str, Any]]:
        """Split text by sentences, keeping related sentences together"""
        sentences = re.split(self.sentence_endings, text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = ""
        start_pos = 0
        chunk_index = 0
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 2 <= chunk_size:  # +2 for punctuation and space
                if current_chunk:
                    current_chunk += ". " + sentence
                else:
                    current_chunk = sentence
            else:
                if current_chunk:
                    chunks.append({
                        "chunk_index": chunk_index,
                        "content": current_chunk.strip(),
                        "content_length": len(current_chunk.strip()),
                        "start_position": start_pos,
                        "end_position": start_pos + len(current_chunk),
                        "chunk_type": "sentence_group"
                    })
                    start_pos += len(current_chunk) + 2
                    chunk_index += 1
                
                current_chunk = sentence
        
        # Add the last chunk
        if current_chunk:
            chunks.append({
                "chunk_index": chunk_index,
                "content": current_chunk.strip(),
                "content_length": len(current_chunk.strip()),
                "start_position": start_pos,
                "end_position": start_pos + len(current_chunk),
                "chunk_type": "sentence_group"
            })
        
        return chunks
    
    def paragraph_splitter(self, text: str, chunk_size: int = 1000) -> List[Dict[str, Any]]:
        """Split text by paragraphs, combining small paragraphs"""
        paragraphs = re.split(self.paragraph_separator, text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        chunks = []
        current_chunk = ""
        start_pos = 0
        chunk_index = 0
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) + 2 <= chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    chunks.append({
                        "chunk_index": chunk_index,
                        "content": current_chunk.strip(),
                        "content_length": len(current_chunk.strip()),
                        "start_position": start_pos,
                        "end_position": start_pos + len(current_chunk),
                        "chunk_type": "paragraph_group"
                    })
                    start_pos += len(current_chunk) + 2
                    chunk_index += 1
                
                # If single paragraph is too large, split it recursively
                if len(paragraph) > chunk_size:
                    para_chunks = self.recursive_text_splitter(paragraph, chunk_size, 0)
                    for para_chunk in para_chunks:
                        para_chunk["chunk_index"] = chunk_index
                        para_chunk["start_position"] = start_pos + para_chunk["start_position"]
                        para_chunk["end_position"] = start_pos + para_chunk["end_position"]
                        chunks.append(para_chunk)
                        chunk_index += 1
                    start_pos += len(paragraph) + 2
                    current_chunk = ""
                else:
                    current_chunk = paragraph
        
        # Add the last chunk
        if current_chunk:
            chunks.append({
                "chunk_index": chunk_index,
                "content": current_chunk.strip(),
                "content_length": len(current_chunk.strip()),
                "start_position": start_pos,
                "end_position": start_pos + len(current_chunk),
                "chunk_type": "paragraph_group"
            })
        
        return chunks
    
    def extract_section_info(self, text: str, chunk_start: int, chunk_end: int) -> Optional[str]:
        """Extract section title if chunk contains a heading"""
        chunk_text = text[chunk_start:chunk_end]
        lines = chunk_text.split('\n')
        
        # Look for potential headings (short lines, all caps, numbered, etc.)
        for line in lines[:3]:  # Check first 3 lines
            line = line.strip()
            if line and (
                len(line) < 100 and  # Short line
                (line.isupper() or  # All uppercase
                 re.match(r'^\d+\.', line) or  # Numbered section
                 re.match(r'^[A-Z][A-Z\s]+$', line))  # Title case
            ):
                return line
        
        return None
    
    async def create_chunks_for_document(
        self, 
        db: AsyncIOMotorDatabase,
        document_id: str, 
        request: ChunkingRequest
    ) -> ChunkingResponse:
        """Create chunks for a document and store them in database"""
        try:
            # Get the document
            from bson import ObjectId
            doc = await db.documents.find_one({"_id": ObjectId(document_id)})
            if not doc:
                raise ValueError(f"Document not found: {document_id}")
            
            content = doc.get("content", "")
            if not content:
                raise ValueError("Document has no content to chunk")
            
            # Delete existing chunks for this document
            await db.document_chunks.delete_many({"document_id": document_id})
            
            # Choose chunking strategy
            start_time = datetime.utcnow()
            
            if request.chunk_strategy == "sentence":
                chunks_data = self.sentence_splitter(content, request.chunk_size)
            elif request.chunk_strategy == "paragraph":
                chunks_data = self.paragraph_splitter(content, request.chunk_size)
            else:  # default to recursive
                chunks_data = self.recursive_text_splitter(
                    content, 
                    request.chunk_size, 
                    request.chunk_overlap
                )
            
            # Create chunk objects
            chunks_to_insert = []
            for chunk_data in chunks_data:
                section_title = None
                if request.preserve_structure:
                    section_title = self.extract_section_info(
                        content, 
                        chunk_data["start_position"], 
                        chunk_data["end_position"]
                    )
                
                chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_index=chunk_data["chunk_index"],
                    content=chunk_data["content"],
                    content_length=chunk_data["content_length"],
                    start_position=chunk_data["start_position"],
                    end_position=chunk_data["end_position"],
                    chunk_type=chunk_data["chunk_type"],
                    section_title=section_title,
                    date_created=datetime.utcnow()
                )
                
                chunks_to_insert.append(chunk.to_mongo())
            
            # Insert chunks into database
            if chunks_to_insert:
                await db.document_chunks.insert_many(chunks_to_insert)
            
            # Calculate statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            total_chars = sum(chunk["content_length"] for chunk in chunks_data)
            avg_chunk_size = total_chars / len(chunks_data) if chunks_data else 0
            
            logger.info(f"Created {len(chunks_data)} chunks for document {document_id}")
            
            return ChunkingResponse(
                document_id=document_id,
                chunks_created=len(chunks_data),
                total_characters=total_chars,
                average_chunk_size=avg_chunk_size,
                processing_time=processing_time,
                status="completed"
            )
            
        except Exception as e:
            logger.error(f"Failed to create chunks for document {document_id}: {e}")
            raise
    
    async def get_chunks_for_document(
        self, 
        db: AsyncIOMotorDatabase, 
        document_id: str
    ) -> List[DocumentChunk]:
        """Get all chunks for a document"""
        try:
            chunks_cursor = db.document_chunks.find(
                {"document_id": document_id}
            ).sort("chunk_index", 1)
            
            chunks = []
            async for chunk_data in chunks_cursor:
                chunk = DocumentChunk.from_mongo(chunk_data)
                chunks.append(chunk)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to get chunks for document {document_id}: {e}")
            raise
    
    async def delete_chunks_for_document(
        self, 
        db: AsyncIOMotorDatabase, 
        document_id: str
    ) -> int:
        """Delete all chunks for a document"""
        try:
            result = await db.document_chunks.delete_many({"document_id": document_id})
            logger.info(f"Deleted {result.deleted_count} chunks for document {document_id}")
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete chunks for document {document_id}: {e}")
            raise

# Create global chunking service instance
chunking_service = ChunkingService()