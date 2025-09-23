import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  Grid,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Paper,
  List,
  ListItem,
  ListItemText,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Avatar,
} from '@mui/material';
import {
  Send as SendIcon,
  QuestionAnswer as QAIcon,
  SmartToy as AIIcon,
  Person as PersonIcon,
  ExpandMore as ExpandMoreIcon,
  Source as SourceIcon,
  Lightbulb as SuggestionIcon,
} from '@mui/icons-material';
import { qaApi, documentApi } from '../services/api';
import { QARequest, QAResponse } from '../types/api';
import { formatDate, truncateText } from '../utils/helpers';

interface Conversation {
  id: string;
  question: string;
  answer: QAResponse;
  timestamp: Date;
}

const QAPage: React.FC = () => {
  const [question, setQuestion] = useState('');
  const [category, setCategory] = useState('');
  const [contextLimit, setContextLimit] = useState(5);
  const [conversations, setConversations] = useState<Conversation[]>([]);

  // Fetch categories
  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: documentApi.getCategories,
  });

  // Fetch question suggestions
  const { data: suggestions = [] } = useQuery({
    queryKey: ['suggestions', category],
    queryFn: () => qaApi.getQuestionSuggestions(category || undefined),
  });

  // Q&A mutation
  const qaMutation = useMutation({
    mutationFn: (request: QARequest) => qaApi.askQuestion(request),
    onSuccess: (response) => {
      const newConversation: Conversation = {
        id: Date.now().toString(),
        question,
        answer: response,
        timestamp: new Date(),
      };
      setConversations(prev => [newConversation, ...prev]);
      setQuestion('');
    },
  });

  const handleAskQuestion = async () => {
    if (!question.trim()) return;

    const request: QARequest = {
      question: question.trim(),
      context_limit: contextLimit,
      category: category || undefined,
    };

    qaMutation.mutate(request);
  };

  const handleSuggestionClick = (suggestion: string) => {
    setQuestion(suggestion);
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'success';
    if (confidence >= 0.6) return 'warning';
    return 'error';
  };

  const getConfidenceText = (confidence: number) => {
    if (confidence >= 0.8) return 'Cao';
    if (confidence >= 0.6) return 'Trung bình';
    return 'Thấp';
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Hỏi đáp AI về pháp luật
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          {/* Question Input */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Đặt câu hỏi
              </Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    multiline
                    rows={3}
                    label="Câu hỏi của bạn"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Ví dụ: Quy định về thời hiệu khởi kiện trong vụ việc dân sự là gì?"
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && e.ctrlKey) {
                        handleAskQuestion();
                      }
                    }}
                  />
                </Grid>
                
                <Grid item xs={12} md={4}>
                  <FormControl fullWidth>
                    <InputLabel>Danh mục (tùy chọn)</InputLabel>
                    <Select
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      label="Danh mục (tùy chọn)"
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
                
                <Grid item xs={12} md={4}>
                  <FormControl fullWidth>
                    <InputLabel>Số tài liệu tham khảo</InputLabel>
                    <Select
                      value={contextLimit}
                      onChange={(e) => setContextLimit(Number(e.target.value))}
                      label="Số tài liệu tham khảo"
                    >
                      <MenuItem value={3}>3 tài liệu</MenuItem>
                      <MenuItem value={5}>5 tài liệu</MenuItem>
                      <MenuItem value={10}>10 tài liệu</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                
                <Grid item xs={12} md={4}>
                  <Button
                    fullWidth
                    variant="contained"
                    onClick={handleAskQuestion}
                    disabled={qaMutation.isPending || !question.trim()}
                    startIcon={qaMutation.isPending ? <CircularProgress size={20} /> : <SendIcon />}
                    sx={{ height: '100%' }}
                  >
                    {qaMutation.isPending ? 'Đang xử lý...' : 'Hỏi AI'}
                  </Button>
                </Grid>
              </Grid>
              
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                Nhấn Ctrl + Enter để gửi câu hỏi nhanh
              </Typography>
            </CardContent>
          </Card>

          {/* Error Display */}
          {qaMutation.error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              Lỗi khi xử lý câu hỏi. Vui lòng thử lại.
            </Alert>
          )}

          {/* Conversations */}
          {conversations.length > 0 ? (
            <Box>
              <Typography variant="h6" gutterBottom>
                Lịch sử hỏi đáp
              </Typography>
              
              {conversations.map((conv) => (
                <Card key={conv.id} sx={{ mb: 3 }}>
                  <CardContent>
                    {/* Question */}
                    <Box sx={{ display: 'flex', mb: 2 }}>
                      <Avatar sx={{ bgcolor: 'primary.main', mr: 2 }}>
                        <PersonIcon />
                      </Avatar>
                      <Box sx={{ flexGrow: 1 }}>
                        <Typography variant="subtitle2" color="primary" gutterBottom>
                          Câu hỏi
                        </Typography>
                        <Typography variant="body1">
                          {conv.question}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {formatDate(conv.timestamp.toISOString())}
                        </Typography>
                      </Box>
                    </Box>

                    {/* Answer */}
                    <Box sx={{ display: 'flex', mb: 2 }}>
                      <Avatar sx={{ bgcolor: 'secondary.main', mr: 2 }}>
                        <AIIcon />
                      </Avatar>
                      <Box sx={{ flexGrow: 1 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                          <Typography variant="subtitle2" color="secondary" sx={{ mr: 2 }}>
                            Trả lời AI
                          </Typography>
                          <Chip
                            label={`Độ tin cậy: ${getConfidenceText(conv.answer.confidence)}`}
                            color={getConfidenceColor(conv.answer.confidence)}
                            size="small"
                          />
                        </Box>
                        <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                          <Typography variant="body1" sx={{ whiteSpace: 'pre-line' }}>
                            {conv.answer.answer}
                          </Typography>
                        </Paper>
                        <Typography variant="caption" color="text.secondary">
                          Thời gian xử lý: {conv.answer.execution_time.toFixed(2)}s
                        </Typography>
                      </Box>
                    </Box>

                    {/* Sources */}
                    {conv.answer.sources.length > 0 && (
                      <Accordion>
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center' }}>
                            <SourceIcon sx={{ mr: 1, fontSize: 'small' }} />
                            Tài liệu tham khảo ({conv.answer.sources.length})
                          </Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          <List dense>
                            {conv.answer.sources.map((source, idx) => (
                              <ListItem key={source.id} divider>
                                <ListItemText
                                  primary={source.title}
                                  secondary={
                                    <Box>
                                      <Typography variant="body2" color="text.secondary">
                                        {truncateText(source.summary || source.content, 100)}
                                      </Typography>
                                      <Box sx={{ mt: 1 }}>
                                        <Chip
                                          label={source.category}
                                          size="small"
                                          sx={{ mr: 1 }}
                                        />
                                        <Typography variant="caption" color="text.secondary">
                                          {formatDate(source.date_created)}
                                        </Typography>
                                      </Box>
                                    </Box>
                                  }
                                />
                              </ListItem>
                            ))}
                          </List>
                        </AccordionDetails>
                      </Accordion>
                    )}
                  </CardContent>
                </Card>
              ))}
            </Box>
          ) : (
            <Box sx={{ textAlign: 'center', py: 6 }}>
              <QAIcon sx={{ fontSize: 80, color: 'grey.400', mb: 2 }} />
              <Typography variant="h6" color="text.secondary">
                Hãy đặt câu hỏi đầu tiên
              </Typography>
              <Typography variant="body2" color="text.secondary">
                AI sẽ tìm kiếm và trả lời dựa trên cơ sở dữ liệu pháp luật
              </Typography>
            </Box>
          )}
        </Grid>

        {/* Sidebar */}
        <Grid item xs={12} md={4}>
          {/* Question Suggestions */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                <SuggestionIcon sx={{ mr: 1 }} />
                Câu hỏi gợi ý
              </Typography>
              
              {suggestions.length > 0 ? (
                <List dense>
                  {suggestions.slice(0, 8).map((suggestion, index) => (
                    <ListItem
                      key={index}
                      button
                      onClick={() => handleSuggestionClick(suggestion)}
                      sx={{
                        borderRadius: 1,
                        mb: 0.5,
                        '&:hover': { bgcolor: 'primary.50' },
                      }}
                    >
                      <ListItemText
                        primary={suggestion}
                        primaryTypographyProps={{
                          variant: 'body2',
                          color: 'primary',
                        }}
                      />
                    </ListItem>
                  ))}
                </List>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Đang tải gợi ý...
                </Typography>
              )}
            </CardContent>
          </Card>

          {/* Usage Tips */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Hướng dẫn sử dụng
              </Typography>
              
              <List dense>
                <ListItem>
                  <ListItemText
                    primary="Đặt câu hỏi cụ thể"
                    secondary="Câu hỏi càng chi tiết, câu trả lời càng chính xác"
                  />
                </ListItem>
                
                <ListItem>
                  <ListItemText
                    primary="Chọn danh mục"
                    secondary="Giúp thu hẹp phạm vi tìm kiếm"
                  />
                </ListItem>
                
                <ListItem>
                  <ListItemText
                    primary="Kiểm tra độ tin cậy"
                    secondary="Chú ý đến chỉ số độ tin cậy của câu trả lời"
                  />
                </ListItem>
                
                <ListItem>
                  <ListItemText
                    primary="Xem tài liệu gốc"
                    secondary="Tham khảo tài liệu nguồn để có thông tin đầy đủ"
                  />
                </ListItem>
              </List>
              
              <Alert severity="warning" sx={{ mt: 2 }}>
                <Typography variant="body2">
                  <strong>Lưu ý:</strong> Câu trả lời chỉ mang tính tham khảo. 
                  Vui lòng tham khảo ý kiến chuyên gia pháp lý cho các vấn đề quan trọng.
                </Typography>
              </Alert>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default QAPage;