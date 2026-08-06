import React, { useState } from 'react';
import { ArrowRight, ArrowLeft, ArrowDown, CheckCircle2, AlertTriangle, Clock, FileText, Code, Layers, Sparkles, Loader2 } from 'lucide-react';

export default function PipelineVisualizer({ pipelineData, isAnimating, animatingStep, crawledPaper }) {
  const stages = pipelineData.stages || [];
  const [selectedStage, setSelectedStage] = useState(stages[0] || null);

  const activeStage = isAnimating && animatingStep >= 0 ? stages[animatingStep] : (selectedStage || stages[0]);

  // Row 1: Left-to-Right (Step 0, Step 1, Step 2, Step 3)
  const row1Stages = stages.slice(0, 4);

  // Row 2: Right-to-Left Snake Flow (Step 6 <- Step 5 <- Step 4)
  const row2Stages = [
    { stage: stages[6], stepIndex: 6 },
    { stage: stages[5], stepIndex: 5 },
    { stage: stages[4], stepIndex: 4 }
  ].filter(item => item.stage);

  const renderNode = (stage, idx) => {
    const isCurrentlyActiveStep = isAnimating && animatingStep === idx;
    const isCompletedStep = isAnimating ? idx < animatingStep : true;
    const isSelected = !isAnimating && selectedStage?.id === stage.id;

    return (
      <div
        key={stage.id}
        onClick={() => !isAnimating && setSelectedStage(stage)}
        className={`glass-panel ${isCurrentlyActiveStep ? 'pulse-card' : ''}`}
        style={{
          flex: 1,
          padding: '20px',
          cursor: isAnimating ? 'wait' : 'pointer',
          borderRadius: '14px',
          border: isCurrentlyActiveStep
            ? '2px solid var(--accent-cyan)'
            : isSelected
              ? '2px solid var(--accent-primary)'
              : '1px solid var(--border-card)',
          background: isCurrentlyActiveStep
            ? 'rgba(6, 182, 212, 0.25)'
            : isSelected
              ? 'rgba(99, 102, 241, 0.15)'
              : 'var(--bg-card)',
          transition: 'all 0.3s ease',
          transform: isCurrentlyActiveStep ? 'scale(1.03)' : 'scale(1)',
          minWidth: '220px'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <span className="glass-pill" style={{ fontSize: '0.7rem' }}>
            Step {idx}
          </span>

          {isCurrentlyActiveStep && (
            <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>Processing...</span>
          )}

          {!isCurrentlyActiveStep && isCompletedStep && stage.status === 'SUCCESS' && (
            <CheckCircle2 size={18} color="#34d399" />
          )}
          {!isCurrentlyActiveStep && isCompletedStep && stage.status === 'WARNING' && (
            <AlertTriangle size={18} color="#fbbf24" />
          )}
        </div>

        <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#ffffff', marginBottom: '8px', lineHeight: 1.35, minHeight: '2.7em' }}>
          {stage.name}
        </h3>

        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Code size={12} />
          <span className="code-font" style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
            {stage.module.split('/').pop()}
          </span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)', borderTop: '1px solid rgba(255, 255, 255, 0.05)', paddingTop: '10px' }}>
          <span>{stage.records_processed} Records</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
            <Clock size={12} /> {stage.latency_ms}ms
          </span>
        </div>
      </div>
    );
  };

  return (
    <div style={{ padding: '0 32px 32px 32px' }}>

      {/* Live Animation Status Banner */}
      {isAnimating && (
        <div className="glass-panel pulse-card" style={{ padding: '20px', marginBottom: '24px', background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.2), rgba(99, 102, 241, 0.2))', border: '1px solid var(--accent-cyan)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <Loader2 size={28} className="animate-spin" color="#06b6d4" />
            <div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sparkles size={18} color="#38bdf8" />
                Live Pipeline Execution in Progress... (Stage {animatingStep} of 7)
              </div>
              <div style={{ fontSize: '0.88rem', color: '#93c5fd', marginTop: '2px' }}>
                Ingesting paper: <strong>{crawledPaper?.title || 'New Crossref Document'}</strong>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Top Description Panel */}
      {!isAnimating && (
        <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h2 style={{ fontSize: '1.3rem', color: '#ffffff', marginBottom: '4px' }}>
                Data Pipeline Execution DAG (Snake Flow)
              </h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                End-to-end data ingestion, cleaning, corruption simulation, repair, and RAG evaluation flow. Click any node to inspect details.
              </p>
            </div>
            <span className="badge badge-success">
              Pipeline Health: {pipelineData.overall_status || 'HEALTHY'}
            </span>
          </div>
        </div>
      )}

      {/* Snake/Zigzag Flowchart Nodes Layout */}
      <div className="glass-panel" style={{ padding: '28px', marginBottom: '24px', position: 'relative' }}>

        {/* ROW 1: Left-to-Right (Step 0 ➔ Step 1 ➔ Step 2 ➔ Step 3) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '16px' }}>
          {row1Stages.map((stage, idx) => (
            <React.Fragment key={stage.id}>
              {renderNode(stage, idx)}
              {idx < row1Stages.length - 1 && (
                <div style={{ color: isAnimating && idx < animatingStep ? '#06b6d4' : 'var(--text-muted)' }}>
                  <ArrowRight size={22} />
                </div>
              )}
            </React.Fragment>
          ))}
        </div>

        {/* Right-Side Transition Arrow between Step 3 and Step 4 */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', paddingRight: '120px', margin: '2px 0 14px 0', color: isAnimating && animatingStep >= 3 ? '#06b6d4' : 'var(--text-muted)' }}>
          <ArrowDown size={24} />
        </div>

        {/* ROW 2: Right-to-Left Snake Flow (Step 6 <- Step 5 <- Step 4) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {row2Stages.map((item, idxInRow) => (
            <React.Fragment key={item.stage.id}>
              {renderNode(item.stage, item.stepIndex)}
              {idxInRow < row2Stages.length - 1 && (
                <div style={{ color: isAnimating && item.stepIndex <= animatingStep ? '#06b6d4' : 'var(--text-muted)' }}>
                  <ArrowLeft size={22} />
                </div>
              )}
            </React.Fragment>
          ))}
        </div>

      </div>

      {/* Selected Node Details Drawer */}
      {activeStage && (
        <div className="glass-panel" style={{ padding: '28px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ background: 'rgba(99, 102, 241, 0.2)', padding: '8px', borderRadius: '8px' }}>
                <Layers size={22} color="#818cf8" />
              </div>
              <div>
                <h3 style={{ fontSize: '1.2rem', color: '#ffffff' }}>{activeStage.name}</h3>
                <span className="code-font" style={{ fontSize: '0.85rem', color: '#818cf8' }}>
                  Module: {activeStage.module}
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px' }}>
              <span className={`badge badge-${activeStage.status === 'SUCCESS' ? 'success' : 'warning'}`}>
                Status: {activeStage.status}
              </span>
            </div>
          </div>

          <p style={{ color: 'var(--text-secondary)', marginBottom: '20px', fontSize: '0.95rem', background: 'rgba(255, 255, 255, 0.02)', padding: '16px', borderRadius: '8px', borderLeft: '3px solid var(--accent-primary)' }}>
            {activeStage.details}
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
            <div className="glass-panel" style={{ padding: '16px' }}>
              <h4 style={{ fontSize: '0.9rem', color: 'var(--text-primary)', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileText size={16} color="#06b6d4" />
                Generated Data Artifacts
              </h4>
              <ul style={{ listStyle: 'none' }}>
                {activeStage.output_files.map((file, idx) => (
                  <li key={idx} className="code-font" style={{ fontSize: '0.8rem', padding: '6px 10px', background: 'rgba(0, 0, 0, 0.3)', borderRadius: '6px', marginBottom: '6px', color: '#38bdf8' }}>
                    📄 {file}
                  </li>
                ))}
              </ul>
            </div>

            <div className="glass-panel" style={{ padding: '16px' }}>
              <h4 style={{ fontSize: '0.9rem', color: 'var(--text-primary)', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Clock size={16} color="#f59e0b" />
                Execution Metrics
              </h4>
              <div style={{ display: 'flex', justifyContent: 'space-around', textAlign: 'center', marginTop: '12px' }}>
                <div>
                  <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#34d399' }}>{activeStage.records_processed}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Items Processed</div>
                </div>
                <div>
                  <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#818cf8' }}>{activeStage.latency_ms} ms</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Stage Latency</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
