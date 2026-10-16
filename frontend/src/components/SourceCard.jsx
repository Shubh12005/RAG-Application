import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Copy, Check, FileText } from 'lucide-react';

export default function SourceCard({ source, index }) {
  const [isExpanded, setIsExpanded] = useState(index === 0);
  const [copied, setCopied] = useState(false);

  const handleCopy = (e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(source.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const matchPercentage = Math.round((source.similarity_score || 0) * 100);

  return (
    <div className="source-card">
      <div 
        className="source-summary-bar"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="source-meta-left">
          <span className="source-page-badge">
            {source.page ? `Page ${source.page}` : (source.section || `Chunk ${source.chunk_index + 1}`)}
          </span>
          <span style={{ fontSize: '0.86rem', fontWeight: 600, color: '#f1f5f9' }}>
            {source.document}
          </span>
          <span className="source-score-badge">
            {matchPercentage}% relevance
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button 
            className="btn-secondary" 
            style={{ padding: '3px 8px', fontSize: '0.72rem' }}
            onClick={handleCopy}
            title="Copy source chunk text"
          >
            {copied ? <Check size={13} color="#10b981" /> : <Copy size={13} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>

          {isExpanded ? <ChevronUp size={16} color="var(--text-muted)" /> : <ChevronDown size={16} color="var(--text-muted)" />}
        </div>
      </div>

      {isExpanded && (
        <div className="source-content-expanded">
          <div style={{ marginBottom: 6, fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between' }}>
            <span>Chunk ID: <code>{source.chunk_id}</code></span>
            {source.section && <span>Section: {source.section}</span>}
          </div>
          <div>{source.text}</div>
        </div>
      )}
    </div>
  );
}
