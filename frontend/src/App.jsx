import React, { useState, useEffect } from 'react';
import { 
  Search, 
  Send, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Sparkles, 
  ShieldCheck, 
  Copy, 
  Check, 
  Database,
  Layers,
  ArrowRight,
  RefreshCw,
  BookOpen
} from 'lucide-react';

import Sidebar from './components/Sidebar';
import UploadModal from './components/UploadModal';
import SettingsModal from './components/SettingsModal';
import SourceCard from './components/SourceCard';

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedDocIds, setSelectedDocIds] = useState([]);
  const [activeDoc, setActiveDoc] = useState(null);
  
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState([]);
  const [lastQuestion, setLastQuestion] = useState('');
  
  const [isLoading, setIsLoading] = useState(false);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  
  const [systemStatus, setSystemStatus] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [copiedAnswer, setCopiedAnswer] = useState(false);

  // Fetch document list and health stats
  const fetchDocuments = async () => {
    try {
      const res = await fetch('/api/documents');
      if (res.ok) {
        const data = await res.json();
        const docs = data.documents || [];
        setDocuments(docs);
        if (docs.length > 0 && !activeDoc) {
          setActiveDoc(docs[0]);
          setSelectedDocIds([docs[0].document_id]);
        }
      }
    } catch (err) {
      console.error("Error fetching documents:", err);
    }
  };

  const fetchHealth = async () => {
    try {
      const res = await fetch('/api/health');
      if (res.ok) {
        const data = await res.json();
        setSystemStatus(data);
      }
    } catch (err) {
      console.error("Error fetching health status:", err);
    }
  };

  useEffect(() => {
    fetchDocuments();
    fetchHealth();
  }, []);

  // Sync activeDoc when documents or selection changes
  const handleToggleSelectDoc = (docId) => {
    if (selectedDocIds.includes(docId)) {
      const updated = selectedDocIds.filter(id => id !== docId);
      setSelectedDocIds(updated);
      const remainingDoc = documents.find(d => d.document_id === updated[0]);
      setActiveDoc(remainingDoc || null);
    } else {
      const updated = [docId]; // single selection or multi
      setSelectedDocIds(updated);
      const clickedDoc = documents.find(d => d.document_id === docId);
      setActiveDoc(clickedDoc || null);
    }
  };

  const handleSelectAllDocs = () => {
    setSelectedDocIds([]);
    setActiveDoc(null);
  };

  const handleDeleteDoc = async (docId) => {
    try {
      const res = await fetch(`/api/documents/${docId}`, { method: 'DELETE' });
      if (res.ok) {
        fetchDocuments();
        fetchHealth();
        if (activeDoc?.document_id === docId) {
          setActiveDoc(null);
          setSelectedDocIds([]);
          setAnswer('');
          setSources([]);
        }
      }
    } catch (err) {
      setErrorMessage(`Failed to delete document: ${err.message}`);
    }
  };

  const handleClearAll = async () => {
    if (!confirm("Are you sure you want to delete ALL documents and clear the vector database?")) return;
    try {
      const res = await fetch('/api/clear-all', { method: 'POST' });
      if (res.ok) {
        setDocuments([]);
        setSelectedDocIds([]);
        setActiveDoc(null);
        setAnswer('');
        setSources([]);
        fetchHealth();
      }
    } catch (err) {
      setErrorMessage(`Failed to clear workspace: ${err.message}`);
    }
  };

  const handleUploadSuccess = (newDoc) => {
    fetchDocuments();
    fetchHealth();
    setActiveDoc(newDoc);
    setSelectedDocIds([newDoc.document_id]);
    setErrorMessage('');
  };

  const handleAsk = async (e) => {
    if (e) e.preventDefault();
    const query = question.trim();
    if (!query) {
      setErrorMessage("Please enter a question about your document.");
      return;
    }

    if (documents.length === 0) {
      setErrorMessage("Please upload a document first.");
      setIsUploadOpen(true);
      return;
    }

    setIsLoading(true);
    setErrorMessage('');
    setLastQuestion(query);

    try {
      const payload = {
        question: query,
        document_ids: selectedDocIds.length > 0 ? selectedDocIds : undefined
      };

      const res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Error querying document");
      }

      setAnswer(data.answer);
      setSources(data.sources || []);
    } catch (err) {
      setErrorMessage(err.message || "Failed to retrieve answer.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyAnswer = () => {
    navigator.clipboard.writeText(answer);
    setCopiedAnswer(true);
    setTimeout(() => setCopiedAnswer(false), 2000);
  };

  // Sample prompt chips
  const samplePrompts = [
    "What is the main objective of this project?",
    "What system architecture or methodology is used?",
    "Summarize the key findings and results",
    "What are the conclusions and next steps?"
  ];

  return (
    <div className="app-container">
      {/* LEFT SIDEBAR */}
      <Sidebar
        documents={documents}
        selectedDocIds={selectedDocIds}
        onToggleSelectDoc={handleToggleSelectDoc}
        onSelectAllDocs={handleSelectAllDocs}
        onDeleteDoc={handleDeleteDoc}
        onClearAll={handleClearAll}
        onOpenUpload={() => setIsUploadOpen(true)}
        onOpenSettings={() => setIsSettingsOpen(true)}
        systemStatus={systemStatus}
      />

      {/* MAIN WORKSPACE AREA */}
      <main className="main-area">
        {/* Top Navbar */}
        <header className="top-navbar">
          <div className="nav-breadcrumbs">
            <span>Workspace</span>
            <span>/</span>
            <span className="nav-active-doc">
              {activeDoc ? activeDoc.filename : (documents.length > 0 ? 'All Documents' : 'No Document Selected')}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {systemStatus?.llm && (
              <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.04)', padding: '4px 10px', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
                LLM: <strong>{systemStatus.llm.active_provider}</strong>
              </span>
            )}
            <button 
              className="btn-secondary" 
              style={{ padding: '6px 10px', fontSize: '0.78rem' }}
              onClick={() => { fetchDocuments(); fetchHealth(); }}
              title="Refresh status"
            >
              <RefreshCw size={13} />
            </button>
          </div>
        </header>

        {/* Central Scrollable Workspace */}
        <div className="workspace-content">
          {/* Global error banner */}
          {errorMessage && (
            <div style={{ padding: '12px 16px', borderRadius: 12, background: 'rgba(244,63,94,0.12)', border: '1px solid rgba(244,63,94,0.3)', color: '#fca5a5', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.86rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <AlertCircle size={18} style={{ flexShrink: 0 }} />
                <span>{errorMessage}</span>
              </div>
              <button 
                onClick={() => setErrorMessage('')} 
                style={{ background: 'transparent', border: 'none', color: '#fca5a5', cursor: 'pointer', fontWeight: 600 }}
              >
                ✕
              </button>
            </div>
          )}

          {/* Welcome Screen if NO documents uploaded yet */}
          {documents.length === 0 ? (
            <div className="hero-card">
              <div className="upload-icon-circle" style={{ margin: '0 auto 16px', width: 64, height: 64 }}>
                <BookOpen size={30} />
              </div>
              <h1 className="hero-title">RAG Research Workspace for macOS</h1>
              <p className="hero-subtitle">
                Accurate, hallucination-free question answering over your research documents, technical specifications, and datasets using local vector retrieval and Apple Silicon embeddings.
              </p>

              <div style={{ display: 'flex', justifyContent: 'center', gap: 12 }}>
                <button className="btn-primary" onClick={() => setIsUploadOpen(true)} style={{ padding: '12px 24px', fontSize: '0.95rem' }}>
                  <Sparkles size={18} />
                  <span>Upload Your First Document</span>
                </button>
              </div>

              {/* Supported formats pills */}
              <div style={{ marginTop: 28, display: 'flex', justifyContent: 'center', gap: 8, flexWrap: 'wrap' }}>
                <span className="source-page-badge">PDF Documents</span>
                <span className="source-page-badge">Word DOCX</span>
                <span className="source-page-badge">Tabular CSV</span>
                <span className="source-page-badge">Markdown .md</span>
                <span className="source-page-badge">Plain Text .txt</span>
              </div>
            </div>
          ) : (
            <>
              {/* Document Info Card */}
              <div className="doc-banner">
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div className="doc-icon-badge" style={{ width: 40, height: 40, background: 'rgba(99,102,241,0.15)', color: '#a5b4fc' }}>
                    <FileText size={22} />
                  </div>
                  <div>
                    <h2 style={{ fontSize: '1.05rem', fontWeight: 700 }}>
                      {activeDoc ? activeDoc.filename : `All Documents (${documents.length})`}
                    </h2>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      {activeDoc ? `Uploaded ${new Date(activeDoc.uploaded_at).toLocaleTimeString()} · ${activeDoc.file_size_formatted}` : 'Multi-document retrieval scope active'}
                    </div>
                  </div>
                </div>

                <div className="doc-banner-stats">
                  <div className="stat-tag">
                    <span>Status:</span>
                    <strong style={{ color: 'var(--accent-teal)' }}>Ready</strong>
                  </div>
                  {activeDoc && (
                    <>
                      <div className="stat-tag">
                        <span>Pages:</span>
                        <strong>{activeDoc.page_count}</strong>
                      </div>
                      <div className="stat-tag">
                        <span>Chunks:</span>
                        <strong>{activeDoc.chunk_count}</strong>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Question Input Box */}
              <form onSubmit={handleAsk} className="question-box">
                <div className="question-input-row">
                  <Search size={20} color="var(--text-muted)" />
                  <input
                    type="text"
                    className="question-input"
                    placeholder="Ask something about your document..."
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    disabled={isLoading}
                  />
                  <button 
                    type="submit" 
                    className="btn-primary" 
                    style={{ padding: '8px 18px' }}
                    disabled={isLoading || !question.trim()}
                  >
                    {isLoading ? (
                      <>
                        <Loader2 size={16} className="spinner" />
                        <span>Searching...</span>
                      </>
                    ) : (
                      <>
                        <span>Ask</span>
                        <Send size={15} />
                      </>
                    )}
                  </button>
                </div>

                {/* Suggestions row */}
                <div className="suggestions-row">
                  {samplePrompts.map((promptText, i) => (
                    <button
                      key={i}
                      type="button"
                      className="suggestion-chip"
                      onClick={() => {
                        setQuestion(promptText);
                      }}
                    >
                      {promptText}
                    </button>
                  ))}
                </div>
              </form>

              {/* Answer Box */}
              {answer && (
                <div className="answer-card">
                  <div className="answer-header">
                    <div className="answer-title-group">
                      <Sparkles size={18} color="#818cf8" />
                      <span>Answer</span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span className="anti-hallucination-badge">
                        <ShieldCheck size={14} />
                        Strict Document Grounding
                      </span>

                      <button 
                        className="btn-secondary"
                        style={{ padding: '3px 8px', fontSize: '0.72rem' }}
                        onClick={handleCopyAnswer}
                        title="Copy answer"
                      >
                        {copiedAnswer ? <Check size={13} color="#10b981" /> : <Copy size={13} />}
                        <span>{copiedAnswer ? 'Copied' : 'Copy'}</span>
                      </button>
                    </div>
                  </div>

                  {lastQuestion && (
                    <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)', borderBottom: '1px solid var(--border-subtle)', paddingBottom: 8 }}>
                      Question: <em>"{lastQuestion}"</em>
                    </div>
                  )}

                  <div className="answer-body">
                    {answer}
                  </div>
                </div>
              )}

              {/* Retrieved Sources Section */}
              {sources.length > 0 && (
                <div className="sources-section">
                  <div className="sources-header">
                    <span>Retrieved Sources ({sources.length} Chunks Used)</span>
                    <span style={{ fontSize: '0.75rem', fontWeight: 500, color: 'var(--text-muted)' }}>
                      Click chunk to inspect full raw excerpt
                    </span>
                  </div>

                  <div className="sources-grid">
                    {sources.map((src, idx) => (
                      <SourceCard key={src.chunk_id || idx} source={src} index={idx} />
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </main>

      {/* Modals */}
      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onSettingsUpdated={() => fetchHealth()}
      />
    </div>
  );
}
