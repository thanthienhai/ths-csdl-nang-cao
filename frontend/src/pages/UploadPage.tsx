import React, { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  Grid,
  Alert,
  LinearProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Paper,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Description as FileIcon,
} from '@mui/icons-material';
import { documentApi } from '../services/api';
import { UploadProgress } from '../types/api';
import { validateFile, formatFileSize } from '../utils/helpers';

const UploadPage: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('');
  const [tags, setTags] = useState('');
  const [uploadProgress, setUploadProgress] = useState<UploadProgress>({
    progress: 0,
    status: 'idle',
  });

  // Fetch categories
  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: documentApi.getCategories,
  });

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: ({ file, title, category, tags }: {
      file: File;
      title: string;
      category: string;
      tags?: string;
    }) => documentApi.uploadDocument(
      file,
      title,
      category,
      tags,
      (progress) => setUploadProgress(prev => ({ ...prev, progress }))
    ),
    onMutate: () => {
      setUploadProgress({ progress: 0, status: 'uploading' });
    },
    onSuccess: () => {
      setUploadProgress({ progress: 100, status: 'completed' });
      // Reset form
      setSelectedFile(null);
      setTitle('');
      setCategory('');
      setTags('');
    },
    onError: (error: any) => {
      setUploadProgress({ 
        progress: 0, 
        status: 'error', 
        message: error.response?.data?.detail || 'Lỗi khi tải lên file' 
      });
    },
  });

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const validation = validateFile(file);
    if (!validation.valid) {
      setUploadProgress({
        progress: 0,
        status: 'error',
        message: validation.error,
      });
      return;
    }

    setSelectedFile(file);
    setUploadProgress({ progress: 0, status: 'idle' });
    
    // Auto-fill title from filename if empty
    if (!title) {
      const filename = file.name.replace(/\.[^/.]+$/, '');
      setTitle(filename);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !title.trim() || !category) {
      setUploadProgress({
        progress: 0,
        status: 'error',
        message: 'Vui lòng điền đầy đủ thông tin và chọn file',
      });
      return;
    }

    uploadMutation.mutate({
      file: selectedFile,
      title: title.trim(),
      category,
      tags: tags.trim(),
    });
  };

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    if (file) {
      const fakeEvent = {
        target: { files: [file] }
      } as React.ChangeEvent<HTMLInputElement>;
      handleFileSelect(fakeEvent);
    }
  };

  const tagList = tags.split(',').map(tag => tag.trim()).filter(tag => tag);

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Tải lên tài liệu
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          {/* File Upload Area */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Chọn file tài liệu
              </Typography>
              
              <Paper
                sx={{
                  p: 4,
                  textAlign: 'center',
                  border: '2px dashed',
                  borderColor: selectedFile ? 'success.main' : 'grey.300',
                  bgcolor: selectedFile ? 'success.50' : 'grey.50',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  '&:hover': {
                    borderColor: 'primary.main',
                    bgcolor: 'primary.50',
                  },
                }}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                onClick={() => document.getElementById('file-input')?.click()}
              >
                <input
                  id="file-input"
                  type="file"
                  accept=".pdf,.doc,.docx,.txt"
                  onChange={handleFileSelect}
                  style={{ display: 'none' }}
                />
                
                <UploadIcon sx={{ fontSize: 48, color: 'grey.400', mb: 2 }} />
                
                {selectedFile ? (
                  <Box>
                    <Typography variant="h6" color="success.main" gutterBottom>
                      <SuccessIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                      File đã chọn
                    </Typography>
                    <Typography variant="body1" gutterBottom>
                      {selectedFile.name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Kích thước: {formatFileSize(selectedFile.size)}
                    </Typography>
                  </Box>
                ) : (
                  <Box>
                    <Typography variant="h6" gutterBottom>
                      Kéo và thả file vào đây hoặc click để chọn
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Hỗ trợ: PDF, DOC, DOCX, TXT (tối đa 10MB)
                    </Typography>
                  </Box>
                )}
              </Paper>
            </CardContent>
          </Card>

          {/* Document Information */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Thông tin tài liệu
              </Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Tiêu đề tài liệu"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    required
                    placeholder="Nhập tiêu đề mô tả nội dung tài liệu"
                  />
                </Grid>
                
                <Grid item xs={12} md={6}>
                  <FormControl fullWidth required>
                    <InputLabel>Danh mục</InputLabel>
                    <Select
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      label="Danh mục"
                    >
                      {categories.map((cat) => (
                        <MenuItem key={cat} value={cat}>
                          {cat}
                        </MenuItem>
                      ))}
                      <MenuItem value="other">Khác</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Từ khóa (phân cách bằng dấu phẩy)"
                    value={tags}
                    onChange={(e) => setTags(e.target.value)}
                    placeholder="luật, hợp đồng, lao động"
                  />
                </Grid>
                
                {tagList.length > 0 && (
                  <Grid item xs={12}>
                    <Typography variant="body2" gutterBottom>
                      Từ khóa:
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {tagList.map((tag, index) => (
                        <Chip key={index} label={tag} size="small" />
                      ))}
                    </Box>
                  </Grid>
                )}
              </Grid>
            </CardContent>
          </Card>

          {/* Upload Progress */}
          {uploadProgress.status !== 'idle' && (
            <Card sx={{ mt: 3 }}>
              <CardContent>
                {uploadProgress.status === 'uploading' && (
                  <Box>
                    <Typography variant="body2" gutterBottom>
                      Đang tải lên... {uploadProgress.progress}%
                    </Typography>
                    <LinearProgress 
                      variant="determinate" 
                      value={uploadProgress.progress} 
                    />
                  </Box>
                )}
                
                {uploadProgress.status === 'completed' && (
                  <Alert severity="success">
                    Tải lên thành công! Tài liệu đã được xử lý và lưu vào hệ thống.
                  </Alert>
                )}
                
                {uploadProgress.status === 'error' && (
                  <Alert severity="error">
                    {uploadProgress.message}
                  </Alert>
                )}
              </CardContent>
            </Card>
          )}

          {/* Upload Button */}
          <Box sx={{ mt: 3, textAlign: 'right' }}>
            <Button
              variant="contained"
              size="large"
              onClick={handleUpload}
              disabled={!selectedFile || !title.trim() || !category || uploadMutation.isPending}
              startIcon={<UploadIcon />}
            >
              {uploadMutation.isPending ? 'Đang tải lên...' : 'Tải lên'}
            </Button>
          </Box>
        </Grid>

        {/* Information Panel */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Hướng dẫn
              </Typography>
              
              <List dense>
                <ListItem>
                  <ListItemIcon>
                    <FileIcon color="primary" />
                  </ListItemIcon>
                  <ListItemText 
                    primary="Định dạng hỗ trợ"
                    secondary="PDF, DOC, DOCX, TXT"
                  />
                </ListItem>
                
                <ListItem>
                  <ListItemIcon>
                    <UploadIcon color="primary" />
                  </ListItemIcon>
                  <ListItemText 
                    primary="Kích thước tối đa"
                    secondary="10MB mỗi file"
                  />
                </ListItem>
                
                <ListItem>
                  <ListItemIcon>
                    <SuccessIcon color="primary" />
                  </ListItemIcon>
                  <ListItemText 
                    primary="Xử lý tự động"
                    secondary="AI sẽ tự động tạo tóm tắt và embedding"
                  />
                </ListItem>
              </List>
              
              <Alert severity="info" sx={{ mt: 2 }}>
                Sau khi tải lên, tài liệu sẽ được xử lý bằng AI để tạo vector embedding 
                cho tìm kiếm ngữ nghĩa và tóm tắt nội dung.
              </Alert>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default UploadPage;