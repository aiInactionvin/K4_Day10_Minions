import React from 'react';
import { Activity, ShieldAlert, GitCompare, MessageSquare, Database, Sparkles } from 'lucide-react';

export default function Header({ activeTab, setActiveTab, healthSummary }) {
  const tabs = [
    { id: 'visualizer', label: 'Pipeline DAG Visualizer', icon: Activity },
    { id: 'comparison', label: 'Data Comparison & Diff', icon: GitCompare },
    { id: 'observability', label: 'Observability & Quality Gates', icon: ShieldAlert },
    { id: 'chatbot', label: 'RAG Chatbot Sandbox', icon: MessageSquare }
  ];

  return (
    <header className="glass-panel" style={{ borderRadius: 0, borderTop: 0, borderLeft: 0, borderRight: 0, padding: '14px 32px', marginBottom: activeTab === 'chatbot' ? '16px' : '24px', flexShrink: 0 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        
        {/* Brand logo & title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            padding: '10px',
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 14px rgba(99, 102, 241, 0.4)'
          }}>
            <Database size={24} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#ffffff' }}>Minions Data Observability</h1>
              <span className="glass-pill" style={{ fontSize: '0.7rem', color: '#8b5cf6', borderColor: 'rgba(139, 92, 246, 0.3)' }}>
                <Sparkles size={12} style={{ display: 'inline', marginRight: '4px' }} />
                Day 10 RAG Lab
              </span>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Data Quality Assurance & Real-time Pipeline Observability Engine
            </p>
          </div>
        </div>

        {/* Live System Health Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div className="glass-panel" style={{ padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Data Health Score</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: healthSummary.health_score_pct > 80 ? '#34d399' : '#f87171' }}>
                {healthSummary.health_score_pct || 75}%
              </div>
            </div>
            <div style={{
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              backgroundColor: healthSummary.health_score_pct > 80 ? '#10b981' : '#f59e0b',
              boxShadow: healthSummary.health_score_pct > 80 ? '0 0 10px #10b981' : '0 0 10px #f59e0b'
            }} />
          </div>

          <div className="glass-panel" style={{ padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <ShieldAlert size={18} color="#f59e0b" />
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Active Anomalies</div>
              <div style={{ fontSize: '1rem', fontWeight: 700, color: '#fbbf24' }}>
                {healthSummary.outdated_papers || 3} Corrupted Fields
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* Navigation Tabs */}
      <nav style={{ display: 'flex', gap: '8px', marginTop: '20px', borderTop: '1px solid rgba(255, 255, 255, 0.05)', paddingTop: '16px' }}>
        {tabs.map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 20px',
                borderRadius: '10px',
                border: 'none',
                background: isActive ? 'linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(139, 92, 246, 0.2))' : 'transparent',
                color: isActive ? '#ffffff' : 'var(--text-secondary)',
                fontWeight: isActive ? 600 : 400,
                fontSize: '0.9rem',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                outline: 'none',
                boxShadow: isActive ? '0 4px 12px rgba(99, 102, 241, 0.2)' : 'none',
                borderBottom: isActive ? '2px solid var(--accent-primary)' : '2px solid transparent'
              }}
            >
              <Icon size={18} color={isActive ? '#818cf8' : '#94a3b8'} />
              {tab.label}
            </button>
          );
        })}
      </nav>
    </header>
  );
}
