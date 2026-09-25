"use client";

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceDot
} from 'recharts';

interface Summary {
  engagement_score: number;
  eye_contact_pct: number;
  blink_rate: number;
  avg_head_stability: number;
  avg_mouth_activity: number;
  avg_posture_score: number;
}

interface TimelinePoint {
  timestamp_sec: number;
  engagement_score: number;
  is_eye_contact: boolean;
  posture_score: number;
}

interface Moment {
  timestamp_sec: number;
  type: string;
  label: string;
  description: string;
}

export default function ReportPage() {
  const params = useParams();
  const sessionId = params.sessionId as string;
  const router = useRouter();

  const [summary, setSummary] = useState<Summary | null>(null);
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);
  const [moments, setMoments] = useState<Moment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!sessionId) return;
    
    Promise.all([
      fetch(`http://localhost:8000/api/report/${sessionId}/summary`).then(r => r.json()),
      fetch(`http://localhost:8000/api/report/${sessionId}/timeline`).then(r => r.json()),
      fetch(`http://localhost:8000/api/report/${sessionId}/moments`).then(r => r.json())
    ])
    .then(([sumData, timeData, momData]) => {
      if (sumData.detail) throw new Error(sumData.detail);
      setSummary(sumData);
      setTimeline(timeData.timeline);
      setMoments(momData);
    })
    .catch(err => {
      console.error(err);
      alert("Failed to load report data.");
    })
    .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <div style={{ width: '40px', height: '40px', borderRadius: '50%', border: '3px solid var(--border-color)', borderTopColor: 'var(--accent-primary)', animation: 'spin 1s linear infinite' }} />
        <style dangerouslySetInnerHTML={{__html: `@keyframes spin { 100% { transform: rotate(360deg); } }`}} />
      </div>
    );
  }

  if (!summary) return <div>No data available.</div>;

  const scoreColor = summary.engagement_score >= 80 ? 'var(--success)' : 
                     summary.engagement_score >= 60 ? '#f59e0b' : 'var(--error)';

  const MetricCard = ({ title, value, label }: { title: string, value: string | number, label: string }) => (
    <div className="glass-panel slide-up" style={{ padding: '24px', display: 'flex', flexDirection: 'column' }}>
      <span style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '8px' }}>{title}</span>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '8px' }}>
        <span style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text-primary)' }}>{value}</span>
      </div>
      <span style={{ fontSize: '0.875rem', color: 'var(--accent-primary)' }}>{label}</span>
    </div>
  );

  return (
    <div className="fade-in" style={{ padding: '40px 0', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '40px' }}>
        <div>
          <h1 style={{ fontSize: '2.5rem', marginBottom: '8px' }}>Interview Report</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Review your detailed behavioral analysis below.</p>
        </div>
        <button className="btn-secondary" onClick={() => router.push('/')}>
          Done
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 3fr', gap: '24px', marginBottom: '24px' }}>
        {/* Main Score Gauge */}
        <div className="glass-panel slide-up" style={{ padding: '40px 24px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
          <h3 style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>Overall Engagement</h3>
          
          <div style={{ position: 'relative', width: '200px', height: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="200" height="200" viewBox="0 0 100 100" style={{ transform: 'rotate(-90deg)' }}>
              <circle cx="50" cy="50" r="45" fill="transparent" stroke="var(--border-color)" strokeWidth="8" />
              <circle cx="50" cy="50" r="45" fill="transparent" stroke={scoreColor} strokeWidth="8" strokeDasharray={`${summary.engagement_score * 2.827} 282.7`} strokeLinecap="round" style={{ transition: 'all 1s ease-out' }} />
            </svg>
            <div style={{ position: 'absolute', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <span style={{ fontSize: '3.5rem', fontWeight: 700, lineHeight: 1 }}>{Math.round(summary.engagement_score)}</span>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginTop: '4px' }}>/ 100</span>
            </div>
          </div>
          
          <p style={{ marginTop: '24px', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            {summary.engagement_score >= 80 ? "Excellent communication presence." : 
             summary.engagement_score >= 60 ? "Good, but room for improvement." : "Needs significant work."}
          </p>
        </div>

        {/* Metric Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '24px' }}>
          <MetricCard 
            title="Eye Contact" 
            value={`${Math.round(summary.eye_contact_pct)}%`} 
            label={summary.eye_contact_pct > 80 ? "Great connection" : "Look at the camera more"} 
          />
          <MetricCard 
            title="Head Stability" 
            value={`${Math.round(summary.avg_head_stability * 100)}%`} 
            label={summary.avg_head_stability > 0.7 ? "Very stable" : "Avoid excessive movement"} 
          />
          <MetricCard 
            title="Posture Score" 
            value={`${Math.round(summary.avg_posture_score * 100)}%`} 
            label={summary.avg_posture_score > 0.8 ? "Upright & confident" : "Watch out for slouching"} 
          />
          <MetricCard 
            title="Blink Rate" 
            value={`${Math.round(summary.blink_rate)} bpm`} 
            label={summary.blink_rate > 30 ? "Slightly elevated" : summary.blink_rate < 10 ? "A bit low (staring)" : "Normal range"} 
          />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: '24px' }}>
        {/* Chart */}
        <div className="glass-panel slide-up" style={{ padding: '24px', minHeight: '400px' }}>
          <h3 style={{ marginBottom: '24px', fontSize: '1.25rem' }}>Engagement Timeline</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={timeline}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
              <XAxis 
                dataKey="timestamp_sec" 
                stroke="var(--text-secondary)" 
                tickFormatter={(val) => `${Math.floor(val/60)}:${Math.floor(val%60).toString().padStart(2,'0')}`} 
                minTickGap={30}
              />
              <YAxis stroke="var(--text-secondary)" domain={[0, 100]} />
              <Tooltip 
                contentStyle={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: '8px' }}
                labelFormatter={(val) => `Time: ${val}s`}
              />
              <Line 
                type="monotone" 
                dataKey="engagement_score" 
                stroke="var(--accent-primary)" 
                strokeWidth={3} 
                dot={false}
                activeDot={{ r: 8, fill: 'var(--accent-primary)', stroke: 'var(--bg-primary)' }}
              />
              
              {/* Overlay moments as ReferenceDots */}
              {moments.map((m, i) => {
                // Find nearest timeline point for Y value
                const point = timeline.reduce((prev, curr) => 
                  Math.abs(curr.timestamp_sec - m.timestamp_sec) < Math.abs(prev.timestamp_sec - m.timestamp_sec) ? curr : prev
                );
                if (!point) return null;
                
                return (
                  <ReferenceDot 
                    key={i} 
                    x={point.timestamp_sec} 
                    y={point.engagement_score} 
                    r={6} 
                    fill={m.type === 'strong' ? 'var(--success)' : 'var(--error)'} 
                    stroke="var(--bg-primary)"
                    strokeWidth={2}
                  />
                )
              })}
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Moments Panel */}
        <div className="glass-panel slide-up" style={{ padding: '24px', display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ marginBottom: '24px', fontSize: '1.25rem' }}>Key Moments</h3>
          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {moments.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)' }}>No key moments detected.</p>
            ) : (
              moments.map((m, i) => (
                <div key={i} style={{ padding: '16px', borderRadius: '8px', background: 'var(--bg-secondary)', borderLeft: `4px solid ${m.type === 'strong' ? 'var(--success)' : 'var(--error)'}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>{m.label}</span>
                    <span style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', fontVariantNumeric: 'tabular-nums' }}>
                      {Math.floor(m.timestamp_sec/60)}:{Math.floor(m.timestamp_sec%60).toString().padStart(2,'0')}
                    </span>
                  </div>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>{m.description}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
