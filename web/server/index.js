import express from 'express';
import cors from 'cors';
import {
  getCleanPapers,
  getCorruptedPapers,
  getRepairedPapers,
  getRawRecords,
  getComparisonData,
  getObservabilityAlerts,
  getPipelineStatus,
  handleChatQuery,
  crawlCrossrefPaper
} from './data_service.js';

const app = express();
const PORT = process.env.PORT || 5001;

app.use(cors());
app.use(express.json());

// API Endpoints
app.get('/api/pipeline/status', (req, res) => {
  res.json(getPipelineStatus());
});

app.get('/api/data/comparison', (req, res) => {
  res.json(getComparisonData());
});

app.get('/api/data/observability', (req, res) => {
  res.json(getObservabilityAlerts());
});

app.get('/api/data/raw', (req, res) => {
  const records = getRawRecords();
  res.json({
    total: records.length,
    sample: records.slice(0, 5),
    records
  });
});

app.post('/api/pipeline/crawl', (req, res) => {
  const { topic } = req.body;
  if (!topic) {
    return res.status(400).json({ error: 'Topic or description is required' });
  }
  const result = crawlCrossrefPaper(topic);
  res.json(result);
});

app.post('/api/chat/query', (req, res) => {

  const { query, mode } = req.body;
  if (!query) {
    return res.status(400).json({ error: 'Query parameter is required' });
  }
  const result = handleChatQuery(query, mode || 'clean');
  res.json(result);
});

app.listen(PORT, () => {
  console.log(`🚀 Data Observability Server running on http://localhost:${PORT}`);
});
