export interface Document {
  id: string;
  title: string;
  content: string;
  summary?: string;
  category: string;
  tags: string[];
  date_created: string;
  date_updated?: string;
  file_path?: string;
  file_size?: number;
  file_type?: string;
  metadata?: Record<string, any>;
}

export interface DocumentCreate {
  title: string;
  content: string;
  summary?: string;
  category: string;
  tags: string[];
  metadata?: Record<string, any>;
}

export interface DocumentUpdate {
  title?: string;
  content?: string;
  summary?: string;
  category?: string;
  tags?: string[];
  metadata?: Record<string, any>;
}

export interface SearchRequest {
  query: string;
  category?: string;
  tags?: string[];
  limit?: number;
  offset?: number;
}

export interface SearchResult {
  document: Document;
  score: number;
  highlights?: string[];
}

export interface SearchResponse {
  results: SearchResult[];
  total_count: number;
  query: string;
  execution_time: number;
}

export interface QARequest {
  question: string;
  context_limit?: number;
  category?: string;
}

export interface QAResponse {
  question: string;
  answer: string;
  confidence: number;
  sources: Document[];
  execution_time: number;
}

export interface ApiError {
  detail: string;
}

export interface UploadProgress {
  progress: number;
  status: 'idle' | 'uploading' | 'processing' | 'completed' | 'error';
  message?: string;
}