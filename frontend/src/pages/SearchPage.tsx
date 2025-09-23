import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  TextField,
  Button,
  Typography,
  Grid,
  Card,
  CardContent,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Pagination,
} from '@mui/material';
import {
  Search as SearchIcon,
  ExpandMore as ExpandMoreIcon,
  Highlight as HighlightIcon,
} from '@mui/icons-material';
import { searchApi, documentApi } from '../services/api';
import { SearchRequest, SearchResponse } from '../types/api';
import { formatDate, truncateText } from '../utils/helpers';

const SearchPage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [category, setCategory] = useState('');
  const [searchType, setSearchType] = useState<'text' | 'semantic'>('text');
  const [page, setPage] = useState(1);
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  const limit = 10;

  // Fetch categories
  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: documentApi.getCategories,
  });

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      const request: SearchRequest = {
        query: searchQuery,
        category: category || undefined,
        limit,
        offset: (page - 1) * limit,
      };

      const results = searchType === 'semantic' 
        ? await searchApi.semanticSearch(request)
        : await searchApi.searchDocuments(request);

      setSearchResults(results);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setIsSearching(false);
    }
  };

  const handlePageChange = (event: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
    if (searchQuery.trim()) {
      handleSearch();
    }
  };

  const totalPages = searchResults 
    ? Math.ceil(searchResults.total_count / limit) 
    : 0;

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Tìm kiếm văn bản pháp luật
      </Typography>

      {/* Search Form */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Nhập từ khóa tìm kiếm"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Ví dụ: hợp đồng lao động, thời hiệu khởi kiện..."
                InputProps={{
                  endAdornment: (
                    <SearchIcon color="action" />
                  ),
                }}
              />
            </Grid>
            <Grid item xs={12} md={2}>
              <FormControl fullWidth>
                <InputLabel>Danh mục</InputLabel>
                <Select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  label="Danh mục"
                >
                  <MenuItem value="">Tất cả</MenuItem>
                  {categories.map((cat) => (
                    <MenuItem key={cat} value={cat}>
                      {cat}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={2}>
              <FormControl fullWidth>
                <InputLabel>Loại tìm kiếm</InputLabel>
                <Select
                  value={searchType}
                  onChange={(e) => setSearchType(e.target.value as 'text' | 'semantic')}
                  label="Loại tìm kiếm"
                >
                  <MenuItem value="text">Văn bản</MenuItem>
                  <MenuItem value="semantic">Ngữ nghĩa AI</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={2}>
              <Button
                fullWidth
                variant="contained"
                onClick={handleSearch}
                disabled={isSearching || !searchQuery.trim()}
                startIcon={isSearching ? <CircularProgress size={20} /> : <SearchIcon />}
              >
                {isSearching ? 'Đang tìm...' : 'Tìm kiếm'}
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Search Type Info */}
      <Alert severity="info" sx={{ mb: 3 }}>
        <strong>
          {searchType === 'semantic' ? 'Tìm kiếm ngữ nghĩa AI:' : 'Tìm kiếm văn bản:'}
        </strong>{' '}
        {searchType === 'semantic' 
          ? 'Sử dụng AI để hiểu ngữ nghĩa và tìm tài liệu liên quan theo ý nghĩa'
          : 'Tìm kiếm dựa trên từ khóa chính xác trong nội dung tài liệu'
        }
      </Alert>

      {/* Search Results */}
      {searchResults && (
        <Box>
          <Typography variant="h6" gutterBottom>
            Kết quả tìm kiếm: {searchResults.total_count} tài liệu 
            (thời gian: {searchResults.execution_time.toFixed(2)}s)
          </Typography>

          {searchResults.results.length === 0 ? (
            <Alert severity="warning">
              Không tìm thấy tài liệu nào phù hợp với từ khóa "{searchResults.query}"
            </Alert>
          ) : (
            <>
              {searchResults.results.map((result, index) => (
                <Card key={result.document.id} sx={{ mb: 2 }}>
                  <CardContent>
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={8}>
                        <Typography variant="h6" component="h3" gutterBottom>
                          {result.document.title}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" paragraph>
                          {truncateText(result.document.summary || result.document.content, 200)}
                        </Typography>
                        
                        {/* Highlights */}
                        {result.highlights && result.highlights.length > 0 && (
                          <Accordion>
                            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                              <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center' }}>
                                <HighlightIcon sx={{ mr: 1, fontSize: 'small' }} />
                                Đoạn văn liên quan ({result.highlights.length})
                              </Typography>
                            </AccordionSummary>
                            <AccordionDetails>
                              {result.highlights.map((highlight, idx) => (
                                <Typography 
                                  key={idx} 
                                  variant="body2" 
                                  sx={{ 
                                    mb: 1, 
                                    p: 1, 
                                    bgcolor: 'grey.50', 
                                    borderRadius: 1,
                                    fontStyle: 'italic' 
                                  }}
                                >
                                  "...{highlight}..."
                                </Typography>
                              ))}
                            </AccordionDetails>
                          </Accordion>
                        )}
                      </Grid>
                      
                      <Grid item xs={12} md={4}>
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                          <Chip 
                            label={result.document.category} 
                            color="primary" 
                            size="small" 
                          />
                          <Typography variant="caption" color="text.secondary">
                            Điểm số: {(result.score * 100).toFixed(1)}%
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {formatDate(result.document.date_created)}
                          </Typography>
                          {result.document.tags.length > 0 && (
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                              {result.document.tags.slice(0, 3).map((tag) => (
                                <Chip 
                                  key={tag} 
                                  label={tag} 
                                  size="small" 
                                  variant="outlined" 
                                />
                              ))}
                            </Box>
                          )}
                        </Box>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              ))}

              {/* Pagination */}
              {totalPages > 1 && (
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
                  <Pagination
                    count={totalPages}
                    page={page}
                    onChange={handlePageChange}
                    color="primary"
                  />
                </Box>
              )}
            </>
          )}
        </Box>
      )}

      {/* Empty State */}
      {!searchResults && !isSearching && (
        <Box sx={{ textAlign: 'center', py: 6 }}>
          <SearchIcon sx={{ fontSize: 80, color: 'grey.400', mb: 2 }} />
          <Typography variant="h6" color="text.secondary">
            Nhập từ khóa để bắt đầu tìm kiếm
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Hệ thống hỗ trợ tìm kiếm văn bản và ngữ nghĩa bằng AI
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default SearchPage;