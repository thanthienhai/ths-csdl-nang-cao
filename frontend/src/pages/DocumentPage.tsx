import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Chip,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Pagination,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Alert,
} from '@mui/material';
import {
  Visibility as ViewIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  FileDownload as DownloadIcon,
} from '@mui/icons-material';
import { documentApi } from '../services/api';
import { Document } from '../types/api';
import { formatDate, formatFileSize, getFileIcon, truncateText } from '../utils/helpers';

const DocumentPage: React.FC = () => {
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);

  const limit = 12;

  // Fetch documents
  const { data: documents = [], isLoading, error } = useQuery({
    queryKey: ['documents', page, category],
    queryFn: () => documentApi.getDocuments((page - 1) * limit, limit, category || undefined),
  });

  // Fetch categories
  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: documentApi.getCategories,
  });

  const handlePageChange = (event: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
  };

  const handleViewDocument = (document: Document) => {
    setSelectedDocument(document);
    setViewDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setViewDialogOpen(false);
    setSelectedDocument(null);
  };

  // Filter documents by search term
  const filteredDocuments = documents.filter(doc =>
    doc.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    doc.content.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const totalPages = Math.ceil(filteredDocuments.length / limit);

  if (error) {
    return (
      <Alert severity="error">
        Lỗi khi tải tài liệu. Vui lòng thử lại sau.
      </Alert>
    );
  }

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Quản lý tài liệu
      </Typography>

      {/* Search and Filter */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Tìm kiếm tài liệu"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Nhập tên hoặc nội dung tài liệu..."
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <FormControl fullWidth>
                <InputLabel>Danh mục</InputLabel>
                <Select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  label="Danh mục"
                >
                  <MenuItem value="">Tất cả danh mục</MenuItem>
                  {categories.map((cat) => (
                    <MenuItem key={cat} value={cat}>
                      {cat}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={2}>
              <Typography variant="body2" color="text.secondary">
                {filteredDocuments.length} tài liệu
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Documents Grid */}
      {isLoading ? (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography>Đang tải tài liệu...</Typography>
        </Box>
      ) : filteredDocuments.length === 0 ? (
        <Alert severity="info">
          Không có tài liệu nào được tìm thấy.
        </Alert>
      ) : (
        <>
          <Grid container spacing={3}>
            {filteredDocuments.map((document) => (
              <Grid item xs={12} md={6} lg={4} key={document.id}>
                <Card 
                  sx={{ 
                    height: '100%', 
                    display: 'flex', 
                    flexDirection: 'column',
                    transition: 'transform 0.2s',
                    '&:hover': { transform: 'translateY(-2px)' },
                  }}
                >
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <Typography variant="h6" component="h3" sx={{ flexGrow: 1 }}>
                        {getFileIcon(document.file_type || '')} {truncateText(document.title, 50)}
                      </Typography>
                      <IconButton 
                        size="small" 
                        onClick={() => handleViewDocument(document)}
                        color="primary"
                      >
                        <ViewIcon />
                      </IconButton>
                    </Box>
                    
                    <Typography variant="body2" color="text.secondary" paragraph>
                      {truncateText(document.summary || document.content, 120)}
                    </Typography>
                    
                    <Box sx={{ mb: 2 }}>
                      <Chip 
                        label={document.category} 
                        color="primary" 
                        size="small" 
                        sx={{ mb: 1 }}
                      />
                      {document.tags.slice(0, 2).map((tag) => (
                        <Chip 
                          key={tag} 
                          label={tag} 
                          size="small" 
                          variant="outlined" 
                          sx={{ ml: 0.5, mb: 1 }}
                        />
                      ))}
                    </Box>
                    
                    <Typography variant="caption" color="text.secondary" display="block">
                      {formatDate(document.date_created)}
                    </Typography>
                    
                    {document.file_size && (
                      <Typography variant="caption" color="text.secondary" display="block">
                        Kích thước: {formatFileSize(document.file_size)}
                      </Typography>
                    )}
                  </CardContent>
                  
                  <Box sx={{ p: 1, pt: 0, display: 'flex', justifyContent: 'flex-end' }}>
                    <IconButton size="small" color="primary">
                      <EditIcon />
                    </IconButton>
                    <IconButton size="small" color="error">
                      <DeleteIcon />
                    </IconButton>
                    <IconButton size="small">
                      <DownloadIcon />
                    </IconButton>
                  </Box>
                </Card>
              </Grid>
            ))}
          </Grid>

          {/* Pagination */}
          {totalPages > 1 && (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
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

      {/* Document View Dialog */}
      <Dialog
        open={viewDialogOpen}
        onClose={handleCloseDialog}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {selectedDocument?.title}
        </DialogTitle>
        <DialogContent>
          {selectedDocument && (
            <Box>
              <Box sx={{ mb: 2 }}>
                <Chip 
                  label={selectedDocument.category} 
                  color="primary" 
                  sx={{ mr: 1 }}
                />
                {selectedDocument.tags.map((tag) => (
                  <Chip 
                    key={tag} 
                    label={tag} 
                    variant="outlined" 
                    size="small"
                    sx={{ mr: 0.5 }}
                  />
                ))}
              </Box>
              
              {selectedDocument.summary && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    Tóm tắt
                  </Typography>
                  <Typography variant="body2" paragraph>
                    {selectedDocument.summary}
                  </Typography>
                </Box>
              )}
              
              <Typography variant="h6" gutterBottom>
                Nội dung
              </Typography>
              <Typography 
                variant="body2" 
                component="div"
                sx={{ 
                  maxHeight: 400, 
                  overflow: 'auto',
                  whiteSpace: 'pre-line',
                  bgcolor: 'grey.50',
                  p: 2,
                  borderRadius: 1,
                }}
              >
                {selectedDocument.content}
              </Typography>
              
              <Box sx={{ mt: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  Ngày tạo: {formatDate(selectedDocument.date_created)}
                </Typography>
                {selectedDocument.file_size && (
                  <Typography variant="caption" color="text.secondary" display="block">
                    Kích thước: {formatFileSize(selectedDocument.file_size)}
                  </Typography>
                )}
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Đóng</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DocumentPage;