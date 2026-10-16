import React from 'react';
import { 
  FileText, 
  Trash2, 
  Settings as SettingsIcon, 
  Plus, 
  Layers, 
  Database,
  CheckCircle2,
  FileSpreadsheet,
  FileType,
  Sparkles
} from 'lucide-react';

export default function Sidebar({
  documents,
  selectedDocIds,
  onToggleSelectDoc,
  onSelectAllDocs,
  onDeleteDoc,
  onClearAll,
  onOpenUpload,
  onOpenSettings,
  systemStatus
}) {
  const getFileIcon = (fileType) => {
    switch (fileType?.toLowerCase()) {
      case 'pdf':
        return <div className="doc-icon-badge pdf"><FileText size={17} /></div>;
      case 'docx':
        return <div className="doc-icon-badge docx"><FileType size={17} /></div>;
      case 'csv':
        return <div className="doc-icon-badge csv"><FileSpreadsheet size={17} /></div>;
      default:
        return <div className="doc-icon-badge txt"><FileText size={17} /></div>;
    }
  };

  const isAllSelected = documents.length > 0 && selectedDocIds.length === 0;

  return (
    <aside className="sidebar">
      {/* macOS Traffic Lights Header */}
      <div className="mac-traffic-lights">
        <div className="traffic-dot traffic-red" />
        <div className="traffic-dot traffic-yellow" />
        <div className="traffic-dot traffic-green" />
      </div>

      {/* App Branding */}
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="logo-icon">
            <Sparkles size={18} />
          </div>
          <div>
            <div className="logo-text">Research RAG</div>
            <div className="macos-badge">macOS Silicon · Chroma</div>
          </div>
        </div>
      </div>

      {/* New Document Button */}
      <button className="btn-primary" onClick={onOpenUpload}>
        <Plus size={18} />
        <span>New Document</span>
      </button>

      {/* Uploaded Documents List */}
      <div className="sidebar-section-title">
        <span>Uploaded Documents ({documents.length})</span>
        {documents.length > 0 && (
          <button 
            className="btn-secondary" 
            style={{ padding: '3px 7px', fontSize: '0.7rem' }}
            onClick={onClearAll}
            title="Clear all documents"
          >
            Clear All
          </button>
        )}
      </div>

      {/* Scope Selector: All Documents */}
      {documents.length > 1 && (
        <div 
          className={`document-item ${isAllSelected ? 'active' : ''}`}
          onClick={onSelectAllDocs}
        >
          <div className="doc-info-group">
            <div className="doc-icon-badge" style={{ color: '#818cf8', background: 'rgba(99,102,241,0.15)' }}>
              <Layers size={17} />
            </div>
            <div>
              <div className="doc-name">All Documents ({documents.length})</div>
              <div className="doc-sub">Query entire knowledge base</div>
            </div>
          </div>
        </div>
      )}

      {/* Document Items */}
      <div className="document-list">
        {documents.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '30px 10px', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
            No documents uploaded yet.<br />Click <strong>New Document</strong> above to begin.
          </div>
        ) : (
          documents.map((doc) => {
            const isSelected = selectedDocIds.includes(doc.document_id);
            return (
              <div
                key={doc.document_id}
                className={`document-item ${isSelected ? 'active' : ''}`}
                onClick={() => onToggleSelectDoc(doc.document_id)}
              >
                <div className="doc-info-group">
                  {getFileIcon(doc.file_type)}
                  <div style={{ overflow: 'hidden' }}>
                    <div className="doc-name" title={doc.filename}>{doc.filename}</div>
                    <div className="doc-sub">
                      {doc.page_count} {doc.page_count === 1 ? 'page' : 'pages'} · {doc.chunk_count} chunks
                    </div>
                  </div>
                </div>

                <button
                  className="doc-delete-btn"
                  title="Delete document"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm(`Delete "${doc.filename}" and its vector embeddings?`)) {
                      onDeleteDoc(doc.document_id);
                    }
                  }}
                >
                  <Trash2 size={15} />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Sidebar Footer */}
      <div className="sidebar-footer">
        <div className="status-pill">
          <div className="status-dot" />
          <span>Local Vector Store: <strong>{systemStatus?.vector_count || 0} chunks</strong></span>
        </div>

        <button className="btn-secondary" style={{ width: '100%', justifyContent: 'center' }} onClick={onOpenSettings}>
          <SettingsIcon size={15} />
          <span>Settings & Config</span>
        </button>
      </div>
    </aside>
  );
}
