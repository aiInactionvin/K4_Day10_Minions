import React, { useState } from 'react';
import { Send, Bot, User, Sparkles, AlertTriangle, CheckCircle, FileText, BarChart2, Search, Download, Database, Layers, ArrowRight } from 'lucide-react';

export default function ChatbotSandbox({ cleanPapers = [], onCrawlSubmit }) {
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'bot',
      text: 'Hello! I am your RAG Assistant. Ask me any question about the ingested research papers. Try toggling between **Data Sạch** vs **Data Đểu** to see how data quality directly impacts my answers!',
      sources: [],
      eval: null
    }
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [activeMode, setActiveMode] = useState('clean');
  const [isLoading, setIsLoading] = useState(false);

  // Left Sidebar Crawl State
  const [crawlTopic, setCrawlTopic] = useState('');
  const [isCrawling, setIsCrawling] = useState(false);
  const [sourceSearch, setSourceSearch] = useState('');
  const [selectedSourceDetail, setSelectedSourceDetail] = useState(null);

  const presetQueries = [
    "What is Agentic Retrieval-Augmented Generation?",
    "Show me research papers about Large Language Models.",
    "Tell me about data observability and pipeline monitoring."
  ];

  const handleCrawlSubmit = async (e) => {
    e.preventDefault();
    if (!crawlTopic.trim() || isCrawling) return;

    setIsCrawling(true);
    try {
      const res = await fetch('/api/pipeline/crawl', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: crawlTopic })
      });
      const data = await res.json();
      if (data.success && data.paper) {
        setCrawlTopic('');
        if (onCrawlSubmit) {
          onCrawlSubmit(data.paper);
        }
      }
    } catch (err) {
      console.error('Error crawling paper:', err);
    } finally {
      setIsCrawling(false);
    }
  };

  const handleSend = async (queryText) => {
    const q = queryText || inputQuery;
    if (!q.trim() || isLoading) return;

    const userMsg = { id: Date.now(), sender: 'user', text: q };
    setMessages(prev => [...prev, userMsg]);
    setInputQuery('');
    setIsLoading(true);

    try {
      const res = await fetch('/api/chat/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, mode: activeMode })
      });
      const data = await res.json();

      const botMsg = {
        id: Date.now() + 1,
        sender: 'bot',
        text: data.answer,
        sources: data.retrieved_sources || [],
        eval: data.eval_metrics,
        mode: activeMode
      };
      setMessages(prev => [...prev, botMsg]);
    } catch (err) {
      console.error('Chat query error:', err);
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'bot',
        text: '❌ Error connecting to RAG backend service.',
        sources: []
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredSources = cleanPapers.filter(item => {
    const p = item.clean || item;
    const title = (p.title || '').toLowerCase();
    const authors = (p.authors_joined || p.authors || '').toLowerCase();
    const q = sourceSearch.toLowerCase();
    return title.includes(q) || authors.includes(q) || (p.paper_id || '').toLowerCase().includes(q);
  });

  return (
    <div style={{ padding: '0 32px 32px 32px', display: 'grid', gridTemplateColumns: '340px 1fr', gap: '24px' }}>
      
      {/* LEFT SIDEBAR */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        
        {/* Card 1: Crawl Document Input Tool */}
        <div className="glass-panel" style={{ padding: '20px', borderLeft: '4px solid var(--accent-cyan)' }}>
          <h3 style={{ fontSize: '1rem', color: '#ffffff', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Download size={18} color="#06b6d4" />
            Crawl Crossref Papers Tool
          </h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '14px' }}>
            Describe topic to crawl Crossref REST API & run step-by-step pipeline DAG.
          </p>

          <form onSubmit={handleCrawlSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <input
              type="text"
              placeholder="e.g. Agentic RAG in Healthcare"
              value={crawlTopic}
              onChange={(e) => setCrawlTopic(e.target.value)}
              disabled={isCrawling}
              style={{
                width: '100%',
                background: 'rgba(0, 0, 0, 0.3)',
                border: '1px solid var(--border-card)',
                borderRadius: '8px',
                padding: '10px 12px',
                color: '#ffffff',
                fontSize: '0.85rem',
                outline: 'none'
              }}
            />

            <button
              type="submit"
              disabled={isCrawling || !crawlTopic.trim()}
              style={{
                width: '100%',
                background: 'linear-gradient(135deg, #06b6d4, #3b82f6)',
                border: 'none',
                borderRadius: '8px',
                padding: '10px',
                color: '#ffffff',
                fontWeight: 600,
                fontSize: '0.85rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                opacity: isCrawling || !crawlTopic.trim() ? 0.6 : 1
              }}
            >
              <Sparkles size={16} />
              {isCrawling ? 'Crawling Crossref...' : 'Crawl & Run Pipeline DAG'}
            </button>
          </form>
        </div>

        {/* Card 2: Cleaned Sources Document Corpus */}
        <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', flex: 1, minHeight: '450px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 style={{ fontSize: '1rem', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Database size={18} color="#34d399" />
              Cleaned Document Sources
            </h3>
            <span className="glass-pill" style={{ fontSize: '0.7rem', color: '#34d399' }}>
              {filteredSources.length} Papers
            </span>
          </div>

          {/* Search bar inside sidebar */}
          <div style={{ position: 'relative', marginBottom: '12px' }}>
            <Search size={14} color="var(--text-muted)" style={{ position: 'absolute', left: '10px', top: '10px' }} />
            <input
              type="text"
              placeholder="Filter cleaned sources..."
              value={sourceSearch}
              onChange={(e) => setSourceSearch(e.target.value)}
              style={{
                width: '100%',
                background: 'rgba(0, 0, 0, 0.3)',
                border: '1px solid var(--border-card)',
                borderRadius: '6px',
                padding: '6px 10px 6px 30px',
                color: '#ffffff',
                fontSize: '0.8rem',
                outline: 'none'
              }}
            />
          </div>

          {/* Scrollable Document Cards List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', overflowY: 'auto', maxHeight: '420px', paddingRight: '4px' }}>
            {filteredSources.map((item, idx) => {
              const p = item.clean || item;
              const isSelected = selectedSourceDetail?.paper_id === p.paper_id;

              return (
                <div
                  key={idx}
                  onClick={() => setSelectedSourceDetail(p)}
                  style={{
                    padding: '10px 12px',
                    background: isSelected ? 'rgba(52, 211, 153, 0.15)' : 'rgba(0, 0, 0, 0.25)',
                    border: isSelected ? '1px solid #34d399' : '1px solid rgba(255, 255, 255, 0.05)',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <span className="code-font" style={{ fontSize: '0.7rem', color: '#38bdf8' }}>
                      {(p.paper_id || 'doi').slice(0, 22)}
                    </span>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                      {p.published || '2026'}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#ffffff', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden', lineHeight: 1.3 }}>
                    {p.title || 'Untitled Paper'}
                  </div>

                  <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '4px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    👤 {p.authors_joined || p.authors || 'Unknown Author'}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

      </div>

      {/* RIGHT MAIN CHATBOT PANEL */}
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        
        {/* Top Mode Bar */}
        <div className="glass-panel" style={{ padding: '16px 20px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h2 style={{ fontSize: '1.15rem', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Bot size={20} color="#818cf8" />
              RAG QA Agent Sandbox
            </h2>
          </div>

          <div style={{ display: 'flex', background: 'rgba(0, 0, 0, 0.4)', padding: '4px', borderRadius: '10px', border: '1px solid var(--border-card)' }}>
            <button
              onClick={() => setActiveMode('clean')}
              style={{
                padding: '6px 14px',
                borderRadius: '8px',
                border: 'none',
                background: activeMode === 'clean' ? 'rgba(16, 185, 129, 0.2)' : 'transparent',
                color: activeMode === 'clean' ? '#34d399' : 'var(--text-muted)',
                fontSize: '0.82rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <CheckCircle size={14} /> Data Sạch
            </button>

            <button
              onClick={() => setActiveMode('corrupted')}
              style={{
                padding: '6px 14px',
                borderRadius: '8px',
                border: 'none',
                background: activeMode === 'corrupted' ? 'rgba(239, 68, 68, 0.2)' : 'transparent',
                color: activeMode === 'corrupted' ? '#f87171' : 'var(--text-muted)',
                fontSize: '0.82rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <AlertTriangle size={14} /> Data Đểu
            </button>

            <button
              onClick={() => setActiveMode('repaired')}
              style={{
                padding: '6px 14px',
                borderRadius: '8px',
                border: 'none',
                background: activeMode === 'repaired' ? 'rgba(59, 130, 246, 0.2)' : 'transparent',
                color: activeMode === 'repaired' ? '#60a5fa' : 'var(--text-muted)',
                fontSize: '0.82rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <Sparkles size={14} /> Data Đã Sửa
            </button>
          </div>
        </div>

        {/* Preset query chips */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
          {presetQueries.map((pq, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(pq)}
              className="glass-panel"
              style={{
                padding: '6px 12px',
                fontSize: '0.78rem',
                color: '#818cf8',
                cursor: 'pointer',
                border: '1px solid rgba(99, 102, 241, 0.2)'
              }}
            >
              💬 "{pq}"
            </button>
          ))}
        </div>

        {/* Messages Box */}
        <div className="glass-panel" style={{ padding: '20px', minHeight: '380px', maxHeight: '500px', overflowY: 'auto', marginBottom: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {messages.map(msg => (
            <div
              key={msg.id}
              style={{
                alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: msg.sender === 'user' ? '75%' : '90%',
                display: 'flex',
                gap: '12px'
              }}
            >
              {msg.sender === 'bot' && (
                <div style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', padding: '8px', borderRadius: '10px', height: 'fit-content' }}>
                  <Bot size={18} color="#ffffff" />
                </div>
              )}

              <div style={{
                background: msg.sender === 'user' ? 'linear-gradient(135deg, #4f46e5, #6366f1)' : 'rgba(22, 30, 46, 0.8)',
                padding: '14px 18px',
                borderRadius: '12px',
                border: msg.sender === 'user' ? 'none' : '1px solid var(--border-card)',
                color: '#ffffff'
              }}>
                <div style={{ fontSize: '0.9rem', whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
                  {msg.text}
                </div>

                {msg.eval && (
                  <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid rgba(255, 255, 255, 0.1)', display: 'flex', gap: '14px', flexWrap: 'wrap' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.72rem', color: msg.eval.faithfulness_score > 0.8 ? '#34d399' : '#f87171' }}>
                      <BarChart2 size={12} /> Faithfulness: {(msg.eval.faithfulness_score * 100).toFixed(0)}%
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.72rem', color: msg.eval.answer_relevance > 0.8 ? '#34d399' : '#f87171' }}>
                      <BarChart2 size={12} /> Relevance: {(msg.eval.answer_relevance * 100).toFixed(0)}%
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.72rem', color: msg.eval.context_precision > 0.8 ? '#34d399' : '#f87171' }}>
                      <BarChart2 size={12} /> Precision: {(msg.eval.context_precision * 100).toFixed(0)}%
                    </div>
                  </div>
                )}

                {msg.sources && msg.sources.length > 0 && (
                  <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <FileText size={12} color="#06b6d4" />
                      Retrieved Context Citations:
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {msg.sources.map((src, idx) => (
                        <div key={idx} style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '6px 10px', borderRadius: '6px', fontSize: '0.75rem' }}>
                          <div style={{ color: '#38bdf8', fontWeight: 600 }}>{src.title}</div>
                          <div style={{ color: 'var(--text-muted)' }}>Authors: {src.authors}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {msg.sender === 'user' && (
                <div style={{ background: '#3b82f6', padding: '8px', borderRadius: '10px', height: 'fit-content' }}>
                  <User size={18} color="#ffffff" />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Input Form */}
        <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} style={{ display: 'flex', gap: '10px' }}>
          <input
            type="text"
            placeholder={`Ask a question against [${activeMode.toUpperCase()}] corpus...`}
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            disabled={isLoading}
            style={{
              flex: 1,
              background: 'var(--bg-card)',
              border: '1px solid var(--border-card)',
              borderRadius: '10px',
              padding: '12px 16px',
              color: '#ffffff',
              fontSize: '0.9rem',
              outline: 'none'
            }}
          />
          <button
            type="submit"
            disabled={isLoading}
            style={{
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              border: 'none',
              borderRadius: '10px',
              padding: '0 20px',
              color: '#ffffff',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Send size={16} /> {isLoading ? 'Thinking...' : 'Send'}
          </button>
        </form>

      </div>

    </div>
  );
}
