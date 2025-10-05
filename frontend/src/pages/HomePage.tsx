import React from 'react';
import { Link } from 'react-router-dom';
import {
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Box,
  Paper,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  Search as SearchIcon,
  CloudUpload as UploadIcon,
  QuestionAnswer as QAIcon,
  Description as DocumentIcon,
  Speed as SpeedIcon,
  Security as SecurityIcon,
  SmartToy as AIIcon,
} from '@mui/icons-material';

const HomePage: React.FC = () => {
  const features = [
    {
      icon: <SearchIcon color="primary" fontSize="large" />,
      title: 'Tìm kiếm thông minh',
      description: 'Tìm kiếm văn bản pháp luật bằng ngôn ngữ tự nhiên với AI',
      action: 'Tìm kiếm',
      link: '/search',
    },
    {
      icon: <UploadIcon color="primary" fontSize="large" />,
      title: 'Số hóa tài liệu',
      description: 'Tải lên và số hóa các văn bản pháp luật (PDF, DOC, TXT)',
      action: 'Tải lên',
      link: '/upload',
    },
    {
      icon: <QAIcon color="primary" fontSize="large" />,
      title: 'Hỏi đáp AI',
      description: 'Đặt câu hỏi và nhận câu trả lời từ AI dựa trên văn bản pháp luật',
      action: 'Hỏi đáp',
      link: '/qa',
    },
    {
      icon: <DocumentIcon color="primary" fontSize="large" />,
      title: 'Quản lý tài liệu',
      description: 'Xem và quản lý toàn bộ kho tài liệu pháp luật',
      action: 'Xem tài liệu',
      link: '/documents',
    },
  ];

  const benefits = [
    {
      icon: <SpeedIcon />,
      text: 'Tìm kiếm nhanh chóng với công nghệ AI tiên tiến',
    },
    {
      icon: <SecurityIcon />,
      text: 'Bảo mật thông tin với cơ sở dữ liệu MongoDB',
    },
    {
      icon: <AIIcon />,
      text: 'Trả lời câu hỏi thông minh bằng xử lý ngôn ngữ tự nhiên',
    },
  ];

  return (
    <Box>
      {/* Hero Section */}
      <Paper
        sx={{
          py: 6,
          px: 4,
          mb: 4,
          background: 'linear-gradient(135deg, #1976d2 0%, #42a5f5 100%)',
          color: 'white',
          textAlign: 'center',
        }}
      >
        <Typography variant="h3" component="h1" gutterBottom>
          Hệ thống Tra cứu Văn bản Pháp luật
        </Typography>
        <Typography variant="h6" sx={{ mb: 3, maxWidth: 800, mx: 'auto' }}>
          Số hóa và tra cứu văn bản pháp luật với AI, giúp tìm kiếm thông minh 
          và hỏi đáp tự nhiên về các quy định pháp lý
        </Typography>
        <Button
          variant="contained"
          size="large"
          component={Link}
          to="/search"
          sx={{
            bgcolor: 'white',
            color: 'primary.main',
            '&:hover': { bgcolor: 'grey.100' },
          }}
        >
          Bắt đầu tìm kiếm
        </Button>
      </Paper>

      {/* Features Section */}
      <Typography variant="h4" component="h2" gutterBottom sx={{ mb: 3 }}>
        Tính năng chính
      </Typography>
      <Grid container spacing={3} sx={{ mb: 6 }}>
        {features.map((feature, index) => (
          <Grid item xs={12} md={6} lg={3} key={index}>
            <Card
              sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                transition: 'transform 0.2s',
                '&:hover': { transform: 'translateY(-4px)' },
              }}
            >
              <CardContent sx={{ flexGrow: 1, textAlign: 'center' }}>
                <Box sx={{ mb: 2 }}>{feature.icon}</Box>
                <Typography variant="h6" component="h3" gutterBottom>
                  {feature.title}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {feature.description}
                </Typography>
              </CardContent>
              <CardActions sx={{ justifyContent: 'center', pb: 2 }}>
                <Button
                  size="small"
                  component={Link}
                  to={feature.link}
                  variant="contained"
                >
                  {feature.action}
                </Button>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Benefits Section */}
      <Typography variant="h4" component="h2" gutterBottom sx={{ mb: 3 }}>
        Ưu điểm nổi bật
      </Typography>
      <Paper sx={{ p: 3 }}>
        <List>
          {benefits.map((benefit, index) => (
            <ListItem key={index}>
              <ListItemIcon>{benefit.icon}</ListItemIcon>
              <ListItemText primary={benefit.text} />
            </ListItem>
          ))}
        </List>
      </Paper>

      {/* Technology Stack */}
      <Box sx={{ mt: 6, textAlign: 'center' }}>
        <Typography variant="h5" component="h2" gutterBottom>
          Công nghệ sử dụng
        </Typography>
        <Typography variant="body1" color="text.secondary">
          <strong>Backend:</strong> Python + FastAPI + MongoDB + Sentence-BERT + Gemini
          <br />
          <strong>Frontend:</strong> React + TypeScript + Material-UI + React Query
        </Typography>
      </Box>
    </Box>
  );
};

export default HomePage;