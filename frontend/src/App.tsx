import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Container } from '@mui/material';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import SearchPage from './pages/SearchPage';
import DocumentPage from './pages/DocumentPage';
import UploadPage from './pages/UploadPage';
import QAPage from './pages/QAPage';

function App() {
  return (
    <Layout>
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/documents" element={<DocumentPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/qa" element={<QAPage />} />
        </Routes>
      </Container>
    </Layout>
  );
}

export default App;