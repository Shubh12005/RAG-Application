import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, X, Check, Key, Cpu, Database, Sliders } from 'lucide-react';

export default function SettingsModal({ isOpen, onClose, onSettingsUpdated }) {
  const [topK, setTopK] = useState(5);
  const [chunkSize, setChunkSize] = useState(800);
  const [chunkOverlap, setChunkOverlap] = useState(100);
  const [llmProvider, setLlmProvider] = useState('gemini');
  const [geminiKey, setGeminiKey] = useState('');
  const [openaiKey, setOpenaiKey] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [llmStatus, setLlmStatus] = useState(null);

  useEffect(() => {
    if (isOpen) {
      fetch('/api/settings')
        .then(res => res.json())
        .then(data => {
          if (data.top_k) setTopK(data.top_k);
          if (data.chunk_size) setChunkSize(data.chunk_size);
          if (data.chunk_overlap) setChunkOverlap(data.chunk_overlap);
          if (data.llm_provider) setLlmProvider(data.llm_provider);
          if (data.llm_status) setLlmStatus(data.llm_status);
        })
        .catch(err => console.error("Error loading settings:", err));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSave = async () => {
    setIsSaving(true);
    setSaveSuccess(false);

    const payload = {
      top_k: Number(topK),
      chunk_size: Number(chunkSize),
      chunk_overlap: Number(chunkOverlap),
      llm_provider: llmProvider,
    };

    if (geminiKey.trim()) payload.gemini_api_key = geminiKey.trim();
    if (openaiKey.trim()) payload.openai_api_key = openaiKey.trim();

    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        setSaveSuccess(true);
        setTimeout(() => {
          setIsSaving(false);
          setSaveSuccess(false);
          if (onSettingsUpdated) onSettingsUpdated();
          onClose();
        }, 800);
      } else {
        setIsSaving(false);
      }
    } catch (e) {
      console.error(e);
      setIsSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div className="logo-icon" style={{ width: 36, height: 36 }}>
              <Sliders size={18} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>RAG Configuration</h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Retrieval, Chunks, and LLM Provider Settings</p>
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
            <X size={20} />
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Top-K Setting */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
              <label style={{ fontSize: '0.85rem', fontWeight: 600 }}>Retrieval Top-K Chunks: {topK}</label>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Max context excerpts</span>
            </div>
            <input
              type="range"
              min="1"
              max="15"
              value={topK}
              onChange={e => setTopK(e.target.value)}
              style={{ width: '100%', accentColor: 'var(--accent-primary)' }}
            />
          </div>

          {/* Chunk Size & Overlap */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={{ fontSize: '0.82rem', fontWeight: 600, display: 'block', marginBottom: 4 }}>Chunk Size (chars)</label>
              <input
                type="number"
                value={chunkSize}
                onChange={e => setChunkSize(e.target.value)}
                style={{ width: '100%', padding: '8px 10px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-subtle)', borderRadius: 8, color: '#fff', fontSize: '0.88rem' }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.82rem', fontWeight: 600, display: 'block', marginBottom: 4 }}>Chunk Overlap (chars)</label>
              <input
                type="number"
                value={chunkOverlap}
                onChange={e => setChunkOverlap(e.target.value)}
                style={{ width: '100%', padding: '8px 10px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-subtle)', borderRadius: 8, color: '#fff', fontSize: '0.88rem' }}
              />
            </div>
          </div>

          {/* LLM Provider Selection */}
          <div>
            <label style={{ fontSize: '0.82rem', fontWeight: 600, display: 'block', marginBottom: 4 }}>Preferred LLM Provider</label>
            <select
              value={llmProvider}
              onChange={e => setLlmProvider(e.target.value)}
              style={{ width: '100%', padding: '8px 10px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-subtle)', borderRadius: 8, color: '#fff', fontSize: '0.88rem' }}
            >
              <option value="gemini" style={{ background: '#111622' }}>Google Gemini (Recommended · gemini-1.5-flash)</option>
              <option value="openai" style={{ background: '#111622' }}>OpenAI (gpt-4o-mini)</option>
            </select>
          </div>

          {/* Gemini API Key */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <label style={{ fontSize: '0.82rem', fontWeight: 600 }}>Gemini API Key</label>
              {llmStatus?.has_gemini_key && (
                <span style={{ fontSize: '0.72rem', color: 'var(--accent-teal)' }}>✓ Configured in environment</span>
              )}
            </div>
            <input
              type="password"
              placeholder={llmStatus?.has_gemini_key ? "••••••••••••••••••••••••" : "Paste your GEMINI_API_KEY"}
              value={geminiKey}
              onChange={e => setGeminiKey(e.target.value)}
              style={{ width: '100%', padding: '8px 10px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-subtle)', borderRadius: 8, color: '#fff', fontSize: '0.88rem' }}
            />
          </div>

          {/* Status info box */}
          <div style={{ padding: '10px 12px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-subtle)', borderRadius: 10, fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
            <div><strong>Embeddings:</strong> SentenceTransformers (all-MiniLM-L6-v2)</div>
            <div><strong>Vector DB:</strong> Persistent Chroma on macOS</div>
            <div><strong>Current Active LLM:</strong> {llmStatus?.active_provider || 'Local Inspection Mode'}</div>
          </div>
        </div>

        {/* Modal Buttons */}
        <div style={{ marginTop: 22, display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={handleSave} disabled={isSaving}>
            {saveSuccess ? (
              <>
                <Check size={16} color="#fff" />
                <span>Saved!</span>
              </>
            ) : (
              <span>Save Configuration</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
