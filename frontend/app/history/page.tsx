"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { API_BASE } from '@/lib/api';

interface SessionHistory {
  id: string;
  created_at: string;
  duration_seconds: number | null;
  status: string;
  engagement_score: number | null;
}

export default function HistoryPage() {
  const [sessions, setSessions] = useState<SessionHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    fetch(`${API_BASE}/api/session`)
      .then(r => r.json())
      .then(data => setSessions(data.sessions || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <div style={{ width: '40px', height: '40px', borderRadius: '50%', border: '3px solid var(--border-color)', borderTopColor: 'var(--accent-primary)', animation: 'spin 1s linear infinite' }} />
        <style dangerouslySetInnerHTML={{__html: `@keyframes spin { 100% { transform: rotate(360deg); } }`}} />
      </div>
    );
  }

  return (
    <div className="fade-in" style={{ padding: '40px 0', maxWidth: '800px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '40px' }}>
        <div>
          <h1 style={{ fontSize: '2.5rem', marginBottom: '8px' }}>History</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Your past interview sessions.</p>
        </div>
        <button className="btn-primary" onClick={() => router.push('/interview')}>
          New Interview
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {sessions.length === 0 ? (
          <div className="glass-panel" style={{ padding: '40px', textAlign: 'center' }}>
            <p style={{ color: 'var(--text-secondary)' }}>You haven't recorded any interviews yet.</p>
          </div>
        ) : (
          sessions.map(s => (
            <div key={s.id} className="glass-panel" style={{ padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <p style={{ fontWeight: 600, marginBottom: '4px' }}>
                  {new Date(s.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                </p>
                <div style={{ display: 'flex', gap: '16px', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                  <span>{s.duration_seconds ? `${Math.round(Number(s.duration_seconds))}s` : 'Unknown duration'}</span>
                  <span>
                    Status: <span style={{ color: s.status === 'complete' ? 'var(--success)' : s.status === 'error' ? 'var(--error)' : 'var(--accent-primary)' }}>{s.status}</span>
                  </span>
                </div>
              </div>
              
              <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
                {s.status === 'complete' && s.engagement_score !== null && (
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '1.5rem', fontWeight: 700, color: s.engagement_score >= 80 ? 'var(--success)' : s.engagement_score >= 60 ? '#f59e0b' : 'var(--error)' }}>
                      {Math.round(s.engagement_score)}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Score</div>
                  </div>
                )}
                
                <button 
                  className="btn-secondary" 
                  onClick={() => s.status === 'complete' ? router.push(`/report/${s.id}`) : router.push(`/processing?session=${s.id}`)}
                  disabled={s.status === 'error'}
                >
                  {s.status === 'complete' ? 'View Report' : 'Check Status'}
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
