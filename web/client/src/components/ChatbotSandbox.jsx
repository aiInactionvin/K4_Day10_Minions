import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Sparkles, AlertTriangle, CheckCircle, FileText, BarChart2, Search, Download, Database, Layers, ArrowRight, X, Code, Copy } from 'lucide-react';

export default function ChatbotSandbox({ cleanPapers = [], onCrawlSubmit }) {
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'bot',
      text: 'Hello! I am your RAG QA Assistant. I am connected to the indexed Crossref scholarly paper corpus. Ask me any technical question or toggle between **Data Sạch**, **Data Đểu**, and **Data Đã Sửa** to see how data quality directly impacts answer faithfulness and LLM hallucinations!',
      sources: [],
      eval: null
    }
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [activeMode, setActiveMode] = useState('clean');
  const [isLoading, setIsLoading] = useState(false);

  // Left Sidebar Crawl & Sources State
  const [crawlTopic, setCrawlTopic] = useState('');
  const [isCrawling, setIsCrawling] = useState(false);
  const [sourceSearch, setSourceSearch] = useState('');
  const [selectedSourceDetail, setSelectedSourceDetail] = useState(null);

  // Auto-scroll ref
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

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
    <div style={{ padding: '0 32px 16px 32px', display: 'grid', gridTemplateColumns: '360px 1fr', gap: '20px', flex: 1, height: '100%', minHeight: 0, overflow: 'hidden' }}>
      
      {/* LEFT SIDEBAR */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', height: '100%', overflow: 'hidden' }}>
        
        {/* Sidebar Header Tool 1: Crawl Crossref Form */}
        <div className="glass-panel" style={{ padding: '16px', borderLeft: '4px solid var(--accent-cyan)', flexShrink: 0 }}>
          <h3 style={{ fontSize: '0.95rem', color: '#ffffff', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Download size={18} color="#06b6d4" />
            Crawl Crossref Papers Tool
          </h3>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            Enter topic/description to trigger Crossref Ingestion Agent & run pipeline DAG.
          </p>

          <form onSubmit={handleCrawlSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <input
              type="text"
              placeholder="e.g. Agentic RAG in Medical Imaging"
              value={crawlTopic}
              onChange={(e) => setCrawlTopic(e.target.value)}
              disabled={isCrawling}
              style={{
                width: '100%',
                background: 'rgba(0, 0, 0, 0.35)',
                border: '1px solid var(--border-card)',
                borderRadius: '8px',
                padding: '9px 12px',
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
                padding: '9px',
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
              {isCrawling ? 'Crawling Crossref API...' : 'Crawl & Run Pipeline DAG'}
            </button>
          </form>
        </div>

        {/* Sidebar Tool 2: Cleaned Document Sources Corpus */}
        <div className="glass-panel" style={{ padding: '18px', display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 style={{ fontSize: '0.98rem', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Database size={18} color="#34d399" />
              Cleaned Document Corpus
            </h3>
            <span className="glass-pill" style={{ fontSize: '0.7rem', color: '#34d399' }}>
              {filteredSources.length} Papers
            </span>
          </div>

          <div style={{ position: 'relative', marginBottom: '12px' }}>
            <Search size={14} color="var(--text-muted)" style={{ position: 'absolute', left: '10px', top: '10px' }} />
            <input
              type="text"
              placeholder="Search cleaned sources by title/DOI..."
              value={sourceSearch}
              onChange={(e) => setSourceSearch(e.target.value)}
              style={{
                width: '100%',
                background: 'rgba(0, 0, 0, 0.35)',
                border: '1px solid var(--border-card)',
                borderRadius: '6px',
                padding: '7px 10px 7px 30px',
                color: '#ffffff',
                fontSize: '0.8rem',
                outline: 'none'
              }}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1, overflowY: 'auto', paddingRight: '4px' }}>
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

      {/* RIGHT EXPANDED MAIN CHATBOT WORKSPACE */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '20px', overflow: 'hidden' }}>
        
        {/* Chat Workspace Header Bar */}
        <div style={{ paddingBottom: '14px', marginBottom: '14px', borderBottom: '1px solid var(--border-card)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', padding: '8px', borderRadius: '10px' }}>
              <Bot size={22} color="#ffffff" />
            </div>
            <div>
              <h2 style={{ fontSize: '1.2rem', color: '#ffffff' }}>
                RAG Agent Conversational Workspace
              </h2>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Ground truth paper corpus QA engine connected to Chroma Vector DB
              </p>
            </div>
          </div>

          {/* Mode Selector Pills */}
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

        {/* Preset Query Quick Chips */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '14px', flexWrap: 'wrap' }}>
          {presetQueries.map((pq, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(pq)}
              style={{
                padding: '6px 12px',
                fontSize: '0.78rem',
                color: '#818cf8',
                cursor: 'pointer',
                background: 'rgba(99, 102, 241, 0.1)',
                border: '1px solid rgba(99, 102, 241, 0.25)',
                borderRadius: '20px',
                transition: 'all 0.2s ease'
              }}
            >
              💬 "{pq}"
            </button>
          ))}
        </div>

        {/* EXPANDED MESSAGES SCROLL CONTAINER */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            paddingRight: '8px',
            marginBottom: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '18px'
          }}
        >
          {messages.map(msg => (
            <div
              key={msg.id}
              style={{
                alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: msg.sender === 'user' ? '70%' : '88%',
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
                background: msg.sender === 'user' ? 'linear-gradient(135deg, #4f46e5, #6366f1)' : 'rgba(15, 23, 42, 0.8)',
                padding: '16px 20px',
                borderRadius: '14px',
                border: msg.sender === 'user' ? 'none' : '1px solid rgba(255, 255, 255, 0.08)',
                color: '#ffffff',
                boxShadow: '0 4px 20px rgba(0,0,0,0.2)'
              }}>
                <div style={{ fontSize: '0.92rem', whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                  {msg.text}
                </div>

                {/* Evaluation RAG Scores */}
                {msg.eval && (
                  <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid rgba(255, 255, 255, 0.1)', display: 'flex', gap: '18px', flexWrap: 'wrap' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', color: msg.eval.faithfulness_score > 0.8 ? '#34d399' : '#f87171', fontWeight: 600 }}>
                      <BarChart2 size={14} /> Faithfulness: {(msg.eval.faithfulness_score * 100).toFixed(0)}%
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', color: msg.eval.answer_relevance > 0.8 ? '#34d399' : '#f87171', fontWeight: 600 }}>
                      <BarChart2 size={14} /> Answer Relevance: {(msg.eval.answer_relevance * 100).toFixed(0)}%
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', color: msg.eval.context_precision > 0.8 ? '#34d399' : '#f87171', fontWeight: 600 }}>
                      <BarChart2 size={14} /> Context Precision: {(msg.eval.context_precision * 100).toFixed(0)}%
                    </div>
                  </div>
                )}

                {/* Retrieved Source Citations */}
                {msg.sources && msg.sources.length > 0 && (
                  <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
                    <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <FileText size={14} color="#06b6d4" />
                      Retrieved Ground Truth Citations ({msg.sources.length}):
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {msg.sources.map((src, idx) => (
                        <div key={idx} style={{ background: 'rgba(0, 0, 0, 0.35)', padding: '10px 12px', borderRadius: '8px', fontSize: '0.78rem', borderLeft: '3px solid #06b6d4' }}>
                          <div style={{ color: '#38bdf8', fontWeight: 600, marginBottom: '2px' }}>{src.title}</div>
                          <div style={{ color: 'var(--text-muted)' }}>Authors: {src.authors}</div>
                          <div style={{ color: 'var(--text-secondary)', marginTop: '4px', fontStyle: 'italic' }}>"{src.summary_snippet}"</div>
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

          {/* Typing Indicator */}
          {isLoading && (
            <div style={{ alignSelf: 'flex-start', display: 'flex', gap: '12px' }}>
              <div style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', padding: '8px', borderRadius: '10px' }}>
                <Bot size={18} color="#ffffff" />
              </div>
              <div style={{ background: 'rgba(15, 23, 42, 0.8)', padding: '12px 18px', borderRadius: '14px', color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
                🤖 Querying Chroma vector collection and generating answer...
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* INPUT PROMPT FORM AT BOTTOM */}
        <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} style={{ display: 'flex', gap: '12px', borderTop: '1px solid var(--border-card)', paddingTop: '14px' }}>
          <input
            type="text"
            placeholder={`Ask a question against [${activeMode.toUpperCase()}] corpus...`}
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            disabled={isLoading}
            style={{
              flex: 1,
              background: 'rgba(0, 0, 0, 0.4)',
              border: '1px solid var(--border-card)',
              borderRadius: '10px',
              padding: '12px 18px',
              color: '#ffffff',
              fontSize: '0.92rem',
              outline: 'none'
            }}
          />
          <button
            type="submit"
            disabled={isLoading || !inputQuery.trim()}
            style={{
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              border: 'none',
              borderRadius: '10px',
              padding: '0 24px',
              color: '#ffffff',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              opacity: isLoading || !inputQuery.trim() ? 0.6 : 1
            }}
          >
            <Send size={18} /> Send
          </button>
        </form>

      </div>

      {/* Paper Detail Inspection Modal Drawer */}
      {selectedSourceDetail && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000,
          padding: '24px'
        }}>
          <div className="glass-panel" style={{ width: '100%', maxWidth: '750px', maxHeight: '85vh', overflowY: 'auto', padding: '24px', borderRadius: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid var(--border-card)', paddingBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <FileText size={22} color="#34d399" />
                <h3 style={{ fontSize: '1.1rem', color: '#ffffff' }}>Inspect Cleaned Paper Record</h3>
              </div>
              <button
                onClick={() => setSelectedSourceDetail(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>PAPER ID / DOI</div>
                <div className="code-font" style={{ fontSize: '0.85rem', color: '#38bdf8' }}>{selectedSourceDetail.paper_id}</div>
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>TITLE</div>
                <div style={{ fontSize: '1rem', fontWeight: 600, color: '#ffffff' }}>{selectedSourceDetail.title}</div>
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>AUTHORS</div>
                <div style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>{selectedSourceDetail.authors_joined || selectedSourceDetail.authors}</div>
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>ABSTRACT / SUMMARY</div>
                <div style={{ fontSize: '0.85rem', color: '#ffffff', background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', lineHeight: 1.5 }}>
                  {selectedSourceDetail.summary}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>PUBLISHED DATE</div>
                  <div style={{ fontSize: '0.85rem', color: '#ffffff' }}>{selectedSourceDetail.published}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>PRIMARY CATEGORY</div>
                  <div style={{ fontSize: '0.85rem', color: '#ffffff' }}>{selectedSourceDetail.primary_category || 'Crossref'}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
