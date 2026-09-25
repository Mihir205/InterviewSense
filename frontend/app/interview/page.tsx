"use client";

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';

export default function InterviewPage() {
  const router = useRouter();
  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  
  const [isRecording, setIsRecording] = useState(false);
  const [streamActive, setStreamActive] = useState(false);
  const [timeElapsed, setTimeElapsed] = useState(0);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    async function setupCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
          video: { width: 1280, height: 720, facingMode: "user" },
          audio: false // audio not analyzed in this MVP
        });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          setStreamActive(true);
        }
      } catch (err) {
        console.error("Error accessing webcam:", err);
      }
    }
    setupCamera();

    return () => {
      // Cleanup
      if (videoRef.current && videoRef.current.srcObject) {
        const stream = videoRef.current.srcObject as MediaStream;
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isRecording) {
      interval = setInterval(() => {
        setTimeElapsed((prev) => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isRecording]);

  const startRecording = () => {
    if (!videoRef.current || !videoRef.current.srcObject) return;
    
    chunksRef.current = [];
    const stream = videoRef.current.srcObject as MediaStream;
    const mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
    
    mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) {
        chunksRef.current.push(e.data);
      }
    };
    
    mediaRecorder.onstop = async () => {
      setIsUploading(true);
      const blob = new Blob(chunksRef.current, { type: 'video/webm' });
      
      const formData = new FormData();
      formData.append('file', blob, 'recording.webm');
      
      try {
        const res = await fetch('http://localhost:8000/api/session/upload', {
          method: 'POST',
          body: formData,
        });
        const data = await res.json();
        
        if (data.session_id) {
          router.push(`/processing?session=${data.session_id}`);
        } else {
          alert('Upload failed');
          setIsUploading(false);
        }
      } catch (err) {
        console.error(err);
        alert('Upload error');
        setIsUploading(false);
      }
    };
    
    mediaRecorderRef.current = mediaRecorder;
    mediaRecorder.start(1000); // collect 1s chunks
    setIsRecording(true);
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', maxWidth: '1000px', margin: '0 auto', paddingTop: '40px' }}>
      <div className="glass-panel slide-up" style={{ width: '100%', overflow: 'hidden', position: 'relative', borderRadius: '24px', backgroundColor: '#000' }}>
        
        <video 
          ref={videoRef}
          autoPlay 
          playsInline 
          muted 
          style={{ width: '100%', aspectRatio: '16/9', objectFit: 'cover', transform: 'scaleX(-1)' }}
        />
        
        {!streamActive && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
            Requesting camera access...
          </div>
        )}
        
        {isRecording && (
          <div style={{ position: 'absolute', top: '24px', right: '24px', display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(0,0,0,0.6)', padding: '8px 16px', borderRadius: '100px', backdropFilter: 'blur(8px)' }}>
            <div className="pulse-ring" style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'var(--error)' }} />
            <span style={{ fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>{formatTime(timeElapsed)}</span>
          </div>
        )}
      </div>

      <div className="slide-up" style={{ marginTop: '40px', animationDelay: '0.2s' }}>
        {!isRecording ? (
          <button 
            className="btn-primary" 
            onClick={startRecording} 
            disabled={!streamActive || isUploading}
            style={{ padding: '16px 48px', fontSize: '1.25rem' }}
          >
            {isUploading ? 'Uploading...' : 'Begin Interview'}
          </button>
        ) : (
          <button 
            className="btn-danger" 
            onClick={stopRecording}
            style={{ padding: '16px 48px', fontSize: '1.25rem' }}
          >
            Stop & Analyse
          </button>
        )}
      </div>
      
      <p style={{ marginTop: '24px', color: 'var(--text-secondary)', fontSize: '0.875rem' }} className="fade-in">
        Ensure your face and shoulders are clearly visible in the frame.
      </p>
    </div>
  );
}
