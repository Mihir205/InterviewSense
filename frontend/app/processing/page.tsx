"use client";

import { useEffect, useState, useRef, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { API_BASE } from '@/lib/api';

function ProcessingContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionId = searchParams.get('session');
  
  const [status, setStatus] = useState<string>('initializing');
  const [progress, setProgress] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  
  const hasTriggered = useRef(false);

  useEffect(() => {
    if (!sessionId) {
      setError("No session ID provided.");
      return;
    }
    
    const initAnalysis = async () => {
      try {
        // M8 fix: check status first to avoid re-triggering on reload
        const res = await fetch(`${API_BASE}/api/session/${sessionId}/status`);
        if (res.ok) {
          const data = await res.json();
          if (data.status === 'queued') {
            if (!hasTriggered.current) {
              hasTriggered.current = true;
              triggerAnalysis(sessionId);
            }
          } else {
            setStatus(data.status);
            if (data.progress_pct !== undefined) setProgress(data.progress_pct);
            if (data.status === 'complete') {
              router.push(`/report/${sessionId}`);
            }
          }
        }
      } catch (err) {
        console.error(err);
      }
    };

    initAnalysis();
    
    // Setup polling
    const interval = setInterval(() => checkStatus(sessionId), 3000);
    return () => clearInterval(interval);
  }, [sessionId, router]);
  
  const triggerAnalysis = async (id: string) => {
    try {
      setStatus('starting analysis...');
      await fetch(`${API_BASE}/api/session/${id}/analyze`, {
        method: 'POST'
      });
    } catch (err) {
      console.error(err);
      setError("Failed to start analysis. Is the backend running?");
    }
  };
  
  const checkStatus = async (id: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/session/${id}/status`);
      if (res.ok) {
        const data = await res.json();
        setStatus(data.status);
        if (data.progress_pct !== undefined) setProgress(data.progress_pct);
        
        if (data.status === 'complete') {
          router.push(`/report/${id}`);
        } else if (data.status === 'error') {
          setError("Analysis failed on the server.");
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  if (error) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', textAlign: 'center' }}>
        <div style={{ color: 'var(--error)', marginBottom: '24px' }}>
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
        </div>
        <h2 style={{ marginBottom: '16px' }}>Processing Error</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '32px' }}>{error}</p>
        <button className="btn-secondary" onClick={() => router.push('/interview')}>
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      {/* Animated Rings */}
      <div style={{ position: 'relative', width: '120px', height: '120px', marginBottom: '40px' }}>
        <div style={{ position: 'absolute', inset: 0, border: '4px solid var(--border-color)', borderRadius: '50%' }}></div>
        <div style={{ 
          position: 'absolute', 
          inset: 0, 
          border: '4px solid transparent', 
          borderTopColor: 'var(--accent-primary)',
          borderRightColor: 'var(--accent-primary)',
          borderRadius: '50%',
          animation: 'spin 1.5s linear infinite'
        }}></div>
        <div style={{ 
          position: 'absolute', 
          inset: '16px', 
          border: '4px solid transparent', 
          borderBottomColor: 'var(--success)',
          borderLeftColor: 'var(--success)',
          borderRadius: '50%',
          animation: 'spin 2s linear infinite reverse'
        }}></div>
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
            <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
            <line x1="12" y1="22.08" x2="12" y2="12"></line>
          </svg>
        </div>
      </div>
      
      <h2 style={{ fontSize: '1.5rem', marginBottom: '8px' }}>Analysing your interview</h2>
      <p style={{ color: 'var(--text-secondary)' }}>Extracting facial landmarks and posture data...</p>
      
      {/* Progress Bar */}
      <div style={{ width: '100%', maxWidth: '300px', height: '6px', backgroundColor: 'var(--bg-glass)', borderRadius: '3px', marginTop: '24px', overflow: 'hidden' }}>
        <div style={{ height: '100%', backgroundColor: 'var(--accent-primary)', width: `${progress}%`, transition: 'width 0.3s ease-out' }}></div>
      </div>
      <p style={{ marginTop: '8px', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>{Math.round(progress)}%</p>

      <p style={{ color: 'var(--accent-primary)', marginTop: '16px', fontSize: '0.875rem', textTransform: 'uppercase', letterSpacing: '2px' }}>
        {status}
      </p>
    </div>
  );
}

export default function ProcessingPage() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', textAlign: 'center' }}>
      <Suspense fallback={<div>Loading...</div>}>
        <ProcessingContent />
      </Suspense>
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes spin { 100% { transform: rotate(360deg); } }
      `}} />
    </div>
  );
}
