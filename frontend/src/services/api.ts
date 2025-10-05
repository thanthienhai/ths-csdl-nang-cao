import axios from 'axios';
import {
  Document,
  DocumentCreate,
  DocumentUpdate,
  SearchRequest,
  SearchResponse,
  QARequest,
  QAResponse,
} from '../types/api';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// // Response interceptor
// api.interceptors.response.use(
//   (response) => response,
//   (error) => {
//     if (error.response?.status === 401) {
//       // Handle unauthorized access
//       localStorage.removeItem('auth_token');
//       window.location.href = '/login';
//     }
//     return Promise.reject(error);
//   }
// );

// Document API
export const documentApi = {
  // Get all documents
  getDocuments: async (
    skip: number = 0,
    limit: number = 10,
    category?: string
  ): Promise<Document[]> => {
    const params = new URLSearchParams();
    params.append('skip', skip.toString());
    params.append('limit', limit.toString());
    if (category) params.append('category', category);

    const response = await api.get(`/documents?${params}`);
    // Map _id to id for each document
    return response.data.map((doc: any) => ({ ...doc, id: doc._id }));
  },

  // Get document by ID
  getDocument: async (id: string): Promise<Document> => {
    const response = await api.get(`/documents/${id}`);
    return response.data;
  },

  // Create document
  createDocument: async (document: DocumentCreate): Promise<Document> => {
    const response = await api.post('/documents', document);
    return response.data;
  },

  // Update document
  updateDocument: async (
    id: string,
    document: DocumentUpdate
  ): Promise<Document> => {
    const response = await api.put(`/documents/${id}`, document);
    return response.data;
  },

  // Delete document
  deleteDocument: async (id: string): Promise<void> => {
    await api.delete(`/documents/${id}`);
  },

  // Upload document file
  uploadDocument: async (
    file: File,
    title: string,
    category: string,
    tags?: string,
    onProgress?: (progress: number) => void
  ): Promise<Document> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title);
    formData.append('category', category);
    if (tags) formData.append('tags', tags);

    const response = await api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(progress);
        }
      },
    });
    return response.data;
  },

  // Get categories
  getCategories: async (): Promise<string[]> => {
    const response = await api.get('/documents/categories/list');
    return response.data.categories;
  },

  // Download document file
  downloadDocument: async (id: string): Promise<void> => {
    const response = await api.get(`/documents/${id}/download`, {
      responseType: 'blob',
    });
    // Get filename from response headers or fallback
    const disposition = response.headers['content-disposition'];
    let filename = 'document.txt';
    if (disposition) {
      const match = disposition.match(/filename="?([^";]+)"?/);
      if (match) filename = match[1];
    }
    // Create a link and trigger download
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

};

// Search API
export const searchApi = {
  // Search documents
  searchDocuments: async (request: SearchRequest): Promise<SearchResponse> => {
    const response = await api.post('/search', request);
    return response.data;
  },

  // Semantic search
  semanticSearch: async (request: SearchRequest): Promise<SearchResponse> => {
    const response = await api.post('/search/semantic', request);
    return response.data;
  },
};

// Q&A API
export const qaApi = {
  // Ask question
  askQuestion: async (request: QARequest): Promise<QAResponse> => {
    const response = await api.post('/qa', request);
    return response.data;
  },

  // Get question suggestions
  getQuestionSuggestions: async (category?: string): Promise<string[]> => {
    const params = category ? `?category=${encodeURIComponent(category)}` : '';
    const response = await api.get(`/qa/suggestions${params}`);
    return response.data.suggestions;
  },
};

// Health check API
export const healthApi = {
  checkHealth: async (): Promise<{ status: string; database: string }> => {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;