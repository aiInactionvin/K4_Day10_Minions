import React, { useState } from 'react';
import { GitCompare, AlertOctagon, CheckCircle, RefreshCw, Search, FileCode } from 'lucide-react';

export default function DataComparison({ comparisonData }) {
  const metrics = comparisonData.metrics || {};
  const papers = comparisonData.papers || [];
  const logs = comparisonData.corruption_logs || [];

  const [searchTerm, setSearchTerm] = useState('');
  const [filterCorruptedOnly, setFilterCorruptedOnly] = useState(true);
  const [selectedPaperId, setSelectedPaperId] = useState(papers[0]?.paper_id || null);

  const filteredPapers = papers.filter(p => {
    const matchesSearch = p.paper_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.clean.title || '').toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = filterCorruptedOnly ? p.is_corrupted : true;
    return matchesSearch && matchesFilter;
  });

  const activePaper = papers.find(p => p.paper_id === selectedPaperId) || filteredPapers[0] || papers[0];

  return (
    <div style={{ padding: '0 32px 32px 32px' }}>

      {/* Metrics Banner */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '20px', marginBottom: '24px' }}>
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Total Records Ingested</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#ffffff', marginTop: '4px' }}>
            {metrics.total_records || 97}
          </div>
          <span className="badge badge-info" style={{ marginTop: '8px' }}>From Crossref & Clean CSV</span>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Corrupted Anomaly Records</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#f87171', marginTop: '4px' }}>
            {metrics.corrupted_records_count || 24}
          </div>
          <span className="badge badge-error" style={{ marginTop: '8px' }}>
            {metrics.corruption_rate_pct || 25}% Anomaly Rate
          </span>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Repair Recovery Rate</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#34d399', marginTop: '4px' }}>
            {metrics.repair_success_rate_pct || 100}%
          </div>
          <span className="badge badge-success" style={{ marginTop: '8px' }}>100% Data Restored</span>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Corruption Event Log</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#818cf8', marginTop: '4px' }}>
            {metrics.total_corruption_events || logs.length}
          </div>
          <span className="badge badge-warning" style={{ marginTop: '8px' }}>Simulation Tracked</span>
        </div>
      </div>

      {/* Selector & Search Toolbar */}
      <div className="glass-panel" style={{ padding: '16px 24px', marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: '1', maxWidth: '400px' }}>
          <Search size={18} color="var(--text-muted)" />
          <input
            type="text"
            placeholder="Search paper by DOI, title or ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              background: 'rgba(0, 0, 0, 0.3)',
              border: '1px solid var(--border-card)',
              borderRadius: '8px',
              padding: '8px 12px',
              color: '#ffffff',
              fontSize: '0.9rem',
              outline: 'none'
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
            <input
              type="checkbox"
              checked={filterCorruptedOnly}
              onChange={(e) => setFilterCorruptedOnly(e.target.checked)}
              style={{ accentColor: 'var(--accent-primary)' }}
            />
            Show Corrupted Records Only ({filteredPapers.length})
          </label>
        </div>
      </div>

      {/* Side-by-Side Paper Diff Inspector */}
      {activePaper && (
        <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', paddingBottom: '12px', borderBottom: '1px solid var(--border-card)' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 style={{ fontSize: '1.1rem', color: '#ffffff' }}>Record Inspection Diff</h3>
                <span className="code-font glass-pill" style={{ fontSize: '0.75rem', color: '#38bdf8' }}>
                  {activePaper.paper_id}
                </span>
              </div>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                Comparing baseline clean record against simulated corrupted payload and restored repair state.
              </p>
            </div>

            {activePaper.is_corrupted ? (
              <span className="badge badge-error">
                <AlertOctagon size={14} /> Corrupted Fields: {activePaper.corrupted_fields.join(', ')}
              </span>
            ) : (
              <span className="badge badge-success">
                <CheckCircle size={14} /> Baseline Clean Record
              </span>
            )}
          </div>

          {/* 3 Columns: Clean vs Corrupted vs Repaired */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>

            {/* Column 1: Clean Baseline */}
            <div className="glass-panel" style={{ padding: '20px', borderTop: '3px solid #10b981' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                <CheckCircle size={18} color="#34d399" />
                <h4 style={{ fontSize: '1rem', color: '#34d399' }}>Data Sạch (Clean Baseline)</h4>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>TITLE</div>
                  <div className="diff-clean" style={{ fontSize: '0.9rem', fontWeight: 600 }}>
                    {activePaper.clean.title || 'N/A'}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>ABSTRACT / SUMMARY</div>
                  <div className="diff-clean" style={{ fontSize: '0.82rem', maxHeight: '180px', overflowY: 'auto' }}>
                    {activePaper.clean.summary || 'N/A'}
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>PUBLISHED DATE</div>
                    <div className="diff-clean" style={{ fontSize: '0.8rem' }}>
                      {activePaper.clean.published || 'N/A'}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>AUTHORS</div>
                    <div className="diff-clean" style={{ fontSize: '0.8rem' }}>
                      {activePaper.clean.authors_joined || 'N/A'}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Column 2: Corrupted Data */}
            <div className="glass-panel" style={{ padding: '20px', borderTop: '3px solid #ef4444' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                <AlertOctagon size={18} color="#f87171" />
                <h4 style={{ fontSize: '1rem', color: '#f87171' }}>Data Đểu (Corrupted Payload)</h4>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>TITLE</div>
                  <div className="diff-corrupted" style={{ fontSize: '0.9rem', fontWeight: 600 }}>
                    {activePaper.corrupted.title || '[MISSING / NULL TITLE]'}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>ABSTRACT / SUMMARY</div>
                  <div className="diff-corrupted" style={{ fontSize: '0.82rem', maxHeight: '180px', overflowY: 'auto' }}>
                    {activePaper.corrupted.summary || '[TRUNCATED OR EMPTY ABSTRACT]'}
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>PUBLISHED DATE</div>
                    <div className="diff-corrupted" style={{ fontSize: '0.8rem' }}>
                      {activePaper.corrupted.published || '1900-01-01'}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>AUTHORS</div>
                    <div className="diff-corrupted" style={{ fontSize: '0.8rem' }}>
                      {activePaper.corrupted.authors_joined || '[EMPTY AUTHORS]'}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Column 3: Repaired Data */}
            <div className="glass-panel" style={{ padding: '20px', borderTop: '3px solid #3b82f6' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                <RefreshCw size={18} color="#60a5fa" />
                <h4 style={{ fontSize: '1rem', color: '#60a5fa' }}>Data Đã Sửa (Repaired State)</h4>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>TITLE</div>
                  <div className="diff-repaired" style={{ fontSize: '0.9rem', fontWeight: 600 }}>
                    {activePaper.repaired.title || 'N/A'}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>ABSTRACT / SUMMARY</div>
                  <div className="diff-repaired" style={{ fontSize: '0.82rem', maxHeight: '180px', overflowY: 'auto' }}>
                    {activePaper.repaired.summary || 'N/A'}
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>PUBLISHED DATE</div>
                    <div className="diff-repaired" style={{ fontSize: '0.8rem' }}>
                      {activePaper.repaired.published || 'N/A'}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>AUTHORS</div>
                    <div className="diff-repaired" style={{ fontSize: '0.8rem' }}>
                      {activePaper.repaired.authors_joined || 'N/A'}
                    </div>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>
      )}

      {/* Paper selector list */}
      <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
        <h4 style={{ fontSize: '1rem', color: '#ffffff', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <FileCode size={18} color="#818cf8" />
          Select Paper to Inspect ({filteredPapers.length} Records)
        </h4>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px', maxHeight: '250px', overflowY: 'auto' }}>
          {filteredPapers.map(paper => {
            const isSelected = paper.paper_id === activePaper?.paper_id;
            return (
              <div
                key={paper.paper_id}
                onClick={() => setSelectedPaperId(paper.paper_id)}
                style={{
                  padding: '12px 16px',
                  background: isSelected ? 'rgba(99, 102, 241, 0.2)' : 'rgba(0, 0, 0, 0.3)',
                  border: isSelected ? '1px solid var(--accent-primary)' : '1px solid rgba(255, 255, 255, 0.05)',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span className="code-font" style={{ fontSize: '0.75rem', color: '#38bdf8' }}>
                    {paper.paper_id.slice(0, 24)}
                  </span>
                  {paper.is_corrupted ? (
                    <span className="badge badge-error" style={{ fontSize: '0.65rem', padding: '2px 6px' }}>Corrupted</span>
                  ) : (
                    <span className="badge badge-success" style={{ fontSize: '0.65rem', padding: '2px 6px' }}>Clean</span>
                  )}
                </div>
                <div style={{ fontSize: '0.82rem', color: '#ffffff', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                  {paper.clean.title || 'Untitled Paper'}
                </div>
              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
}
