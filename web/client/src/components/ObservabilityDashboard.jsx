import React from 'react';
import { ShieldCheck, ShieldAlert, AlertTriangle, Info, CheckCircle2, Clock, Activity, Zap } from 'lucide-react';

export default function ObservabilityDashboard({ observabilityData }) {
  const alerts = observabilityData.alerts || [];
  const qualityGates = observabilityData.quality_gates || [];
  const freshness = observabilityData.freshness_summary || {};

  return (
    <div style={{ padding: '0 32px 32px 32px' }}>
      
      {/* Top Banner */}
      <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ fontSize: '1.3rem', color: '#ffffff', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldCheck size={24} color="#10b981" />
              Data Observability & Quality Gates
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              Automated Great Expectations quality assertions, data drift detection, and freshness threshold tracking.
            </p>
          </div>
          <span className="badge badge-warning">
            Active Alerts: {alerts.filter(a => a.status === 'FAILED').length} Failed Checks
          </span>
        </div>
      </div>

      {/* Quality Gates Overview Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '20px', marginBottom: '24px' }}>
        {qualityGates.map((gate, idx) => {
          const isPass = gate.status === 'PASS';
          return (
            <div key={idx} className="glass-panel" style={{ padding: '20px', borderLeft: `4px solid ${isPass ? '#10b981' : '#ef4444'}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span className="code-font" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Gate 0{idx + 1}</span>
                <span className={`badge badge-${isPass ? 'success' : 'error'}`}>{gate.status}</span>
              </div>
              <h4 style={{ fontSize: '1rem', color: '#ffffff', marginBottom: '6px' }}>{gate.name}</h4>
              <div style={{ fontSize: '1.2rem', fontWeight: 700, color: isPass ? '#34d399' : '#f87171', marginBottom: '4px' }}>
                {gate.score}
              </div>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{gate.detail}</p>
            </div>
          );
        })}
      </div>

      {/* Alerts Feed */}
      <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
        <h3 style={{ fontSize: '1.1rem', color: '#ffffff', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldAlert size={20} color="#f59e0b" />
          Active Data Quality & Drift Assertions
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {alerts.map(alert => {
            const isCritical = alert.severity === 'CRITICAL' || alert.severity === 'HIGH';
            const isWarning = alert.severity === 'MEDIUM';
            
            return (
              <div
                key={alert.id}
                style={{
                  padding: '20px',
                  background: isCritical ? 'rgba(239, 68, 68, 0.08)' : isWarning ? 'rgba(245, 158, 11, 0.08)' : 'rgba(59, 130, 246, 0.08)',
                  border: `1px solid ${isCritical ? 'rgba(239, 68, 68, 0.3)' : isWarning ? 'rgba(245, 158, 11, 0.3)' : 'rgba(59, 130, 246, 0.3)'}`,
                  borderRadius: '12px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    {isCritical && <AlertTriangle size={18} color="#f87171" />}
                    {isWarning && <AlertTriangle size={18} color="#fbbf24" />}
                    {!isCritical && !isWarning && <Info size={18} color="#60a5fa" />}

                    <span className="code-font" style={{ fontSize: '0.85rem', fontWeight: 600, color: '#ffffff' }}>
                      {alert.rule}
                    </span>
                  </div>

                  <div style={{ display: 'flex', gap: '8px' }}>
                    <span className={`badge badge-${isCritical ? 'error' : isWarning ? 'warning' : 'info'}`}>
                      {alert.severity}
                    </span>
                    <span className="code-font glass-pill" style={{ fontSize: '0.75rem' }}>
                      {alert.dataset}
                    </span>
                  </div>
                </div>

                <p style={{ fontSize: '0.9rem', color: '#ffffff', marginBottom: '8px' }}>
                  {alert.message}
                </p>

                <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', background: 'rgba(0, 0, 0, 0.3)', padding: '8px 12px', borderRadius: '6px' }}>
                  💡 <strong>Downstream RAG Impact:</strong> {alert.impact}
                </div>
              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
}
