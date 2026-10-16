import React, { useState, useRef } from 'react';
import { UploadCloud, X, AlertCircle, CheckCircle2, Loader2, FileText } from 'lucide-react';

export default function UploadModal({ isOpen, onClose, onUploadSuccess }) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [statusText, setStatusText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const fileInputRef = useRef(null);

  if (!isOpen) return null;

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  };

  const handleFileSelected = (file) => {
    setErrorMessage('');
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    const validExts = ['.pdf', '.docx', '.txt', '.csv', '.md', '.markdown'];

    if (!validExts.includes(ext)) {
      setErrorMessage(`Unsupported format '${ext}'. Please upload a PDF, DOCX, TXT, CSV, or Markdown file.`);
      return;
    }

    if (file.size === 0) {
      setErrorMessage('The selected file is empty (0 bytes).');
      return;
    }

    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsLoading(true);
    setErrorMessage('');
    setStatusText('Step 1/3: Uploading and extracting document text...');

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      setTimeout(() => {
        if (isLoading) setStatusText('Step 2/3: Chunking & computing Sentence-Transformer embeddings...');
      }, 1500);

      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Upload failed. Please check the document.');
      }

      setStatusText('Step 3/3: Indexed into Chroma vector database successfully!');
      setTimeout(() => {
        setIsLoading(false);
        setSelectedFile(null);
        onUploadSuccess(data.document);
        onClose();
      }, 700);

    } catch (err) {
      setIsLoading(false);
      setErrorMessage(err.message || 'An error occurred during upload.');
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div className="upload-icon-circle" style={{ width: 38, height: 38 }}>
              <UploadCloud size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Upload Document</h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Index file into local RAG knowledge base</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            disabled={isLoading}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Drag & Drop Area */}
        <div
          className={`upload-dropzone ${isDragging ? 'dragging' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !isLoading && fileInputRef.current?.click()}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".pdf,.docx,.txt,.csv,.md,.markdown"
            style={{ display: 'none' }}
            disabled={isLoading}
          />

          <div className="upload-icon-circle">
            <UploadCloud size={26} />
          </div>

          <div style={{ textAlign: 'center' }}>
            <div className="upload-title">
              {selectedFile ? selectedFile.name : 'Click to select or drag & drop'}
            </div>
            <div className="upload-formats" style={{ marginTop: 4 }}>
              Supports PDF, DOCX, TXT, CSV, and Markdown
            </div>
          </div>

          {selectedFile && (
            <div style={{ fontSize: '0.78rem', color: '#a5b4fc', background: 'rgba(99,102,241,0.12)', padding: '4px 10px', borderRadius: 8 }}>
              Size: {(selectedFile.size / 1024).toFixed(1)} KB
            </div>
          )}
        </div>

        {/* Error notification */}
        {errorMessage && (
          <div style={{ marginTop: 14, padding: '10px 14px', borderRadius: 10, background: 'rgba(244,63,94,0.12)', border: '1px solid rgba(244,63,94,0.3)', color: '#fca5a5', display: 'flex', alignItems: 'center', gap: 10, fontSize: '0.82rem' }}>
            <AlertCircle size={18} style={{ flexShrink: 0 }} />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Loading status progress */}
        {isLoading && (
          <div style={{ marginTop: 14, padding: '12px 14px', borderRadius: 10, background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.3)', color: '#c7d2fe', display: 'flex', alignItems: 'center', gap: 10, fontSize: '0.82rem' }}>
            <Loader2 size={18} className="spinner" style={{ flexShrink: 0, color: 'var(--accent-primary)' }} />
            <span>{statusText}</span>
          </div>
        )}

        {/* Actions */}
        <div style={{ marginTop: 20, display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          <button className="btn-secondary" onClick={onClose} disabled={isLoading}>
            Cancel
          </button>
          <button
            className="btn-primary"
            onClick={handleUpload}
            disabled={!selectedFile || isLoading}
          >
            {isLoading ? 'Processing Pipeline...' : 'Start Indexing'}
          </button>
        </div>
      </div>
    </div>
  );
}
