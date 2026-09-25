import Link from 'next/link';

export default function Home() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '80vh', textAlign: 'center' }}>
      <div className="slide-up" style={{ maxWidth: '800px' }}>
        <h1 style={{ fontSize: '4rem', marginBottom: '24px', background: 'linear-gradient(to right, #fff, #a1a1aa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          Master Your Interview Presence
        </h1>
        <p style={{ fontSize: '1.25rem', color: 'var(--text-secondary)', marginBottom: '48px', lineHeight: '1.8' }}>
          Advanced communication analytics powered by facial landmark geometry and behavioral vision. 
          Get instant, objective feedback on your body language and engagement.
        </p>
        
        <Link href="/interview" className="btn-primary" style={{ padding: '16px 32px', fontSize: '1.125rem', marginBottom: '64px' }}>
          Start Mock Interview
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12h14M12 5l7 7-7 7"/>
          </svg>
        </Link>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '24px', marginBottom: '48px', textAlign: 'left' }}>
          {[
            { title: 'Eye Contact', desc: 'Sustained camera gaze analysis' },
            { title: 'Head Pose', desc: 'Stability and orientation tracking' },
            { title: 'Posture', desc: 'Shoulder alignment and slouch detection' },
            { title: 'Activity', desc: 'Blink rate and mouth movement' }
          ].map((feature, i) => (
            <div key={i} className="glass-panel" style={{ padding: '24px' }}>
              <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--bg-glass)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '16px', color: 'var(--accent-primary)' }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
                </svg>
              </div>
              <h3 style={{ fontSize: '1.125rem', marginBottom: '8px' }}>{feature.title}</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>{feature.desc}</p>
            </div>
          ))}
        </div>
        
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '12px 24px', background: 'rgba(16, 185, 129, 0.1)', borderRadius: '100px', color: 'var(--success)', fontSize: '0.875rem' }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
          </svg>
          Privacy First: Everything runs locally. Your video never leaves your computer.
        </div>
      </div>
    </div>
  );
}
