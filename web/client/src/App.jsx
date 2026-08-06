import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import PipelineVisualizer from './components/PipelineVisualizer';
import DataComparison from './components/DataComparison';
import ObservabilityDashboard from './components/ObservabilityDashboard';
import ChatbotSandbox from './components/ChatbotSandbox';

export default function App() {
  const [activeTab, setActiveTab] = useState('visualizer');
  
  const [pipelineData, setPipelineData] = useState({});
  const [comparisonData, setComparisonData] = useState({});
  const [observabilityData, setObservabilityData] = useState({});
  const [isLoading, setIsLoading] = useState(true);

  // Animation state for Pipeline DAG execution
  const [isAnimating, setIsAnimating] = useState(false);
  const [animatingStep, setAnimatingStep] = useState(-1);
  const [crawledPaper, setCrawledPaper] = useState(null);

  const loadAllData = async () => {
    try {
      const [pipelineRes, compRes, obsRes] = await Promise.all([
        fetch('/api/pipeline/status').then(r => r.json()),
        fetch('/api/data/comparison').then(r => r.json()),
        fetch('/api/data/observability').then(r => r.json())
      ]);
      setPipelineData(pipelineRes);
      setComparisonData(compRes);
      setObservabilityData(obsRes);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);

  const triggerCrawlAnimation = (paper) => {
    setCrawledPaper(paper);
    setActiveTab('visualizer');
    setIsAnimating(true);
    setAnimatingStep(0);

    let currentStep = 0;
    const interval = setInterval(() => {
      currentStep += 1;
      if (currentStep < 6) {
        setAnimatingStep(currentStep);
      } else {
        clearInterval(interval);
        setIsAnimating(false);
        setAnimatingStep(-1);
        loadAllData(); // reload updated dataset
      }
    }, 1200); // 1.2s per stage step
  };

  const healthSummary = observabilityData.freshness_summary || {};

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Header activeTab={activeTab} setActiveTab={setActiveTab} healthSummary={healthSummary} />

      <main style={{ flex: 1 }}>
        {isLoading ? (
          <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            Loading Data Observability Metrics...
          </div>
        ) : (
          <>
            {activeTab === 'visualizer' && (
              <PipelineVisualizer
                pipelineData={pipelineData}
                isAnimating={isAnimating}
                animatingStep={animatingStep}
                crawledPaper={crawledPaper}
              />
            )}
            {activeTab === 'comparison' && <DataComparison comparisonData={comparisonData} />}
            {activeTab === 'observability' && <ObservabilityDashboard observabilityData={observabilityData} />}
            {activeTab === 'chatbot' && (
              <ChatbotSandbox
                cleanPapers={comparisonData.papers || []}
                onCrawlSubmit={triggerCrawlAnimation}
              />
            )}
          </>
        )}
      </main>

      <footer style={{ padding: '20px 32px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem', borderTop: '1px solid var(--border-card)' }}>
        Minions Data Observability & RAG Evaluation Platform • Day 10 In-Class Lab
      </footer>
    </div>
  );
}

