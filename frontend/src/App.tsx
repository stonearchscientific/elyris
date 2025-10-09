import React, { useState } from "react";
import UnifiedTimeline from "./components/UnifiedTimeline";
import DocumentUpload from "./components/DocumentUpload";

export default function App(){
  const [activeTab, setActiveTab] = useState<'upload' | 'timeline'>('upload');
  
  return (
    <div style={{padding:20}}>
      <h1>🏥 Elyris — Unified Health Platform</h1>
      
      <div style={{ marginBottom: '20px', borderBottom: '2px solid #ddd' }}>
        <button
          onClick={() => setActiveTab('upload')}
          style={{
            padding: '12px 24px',
            fontSize: '16px',
            marginRight: '8px',
            backgroundColor: activeTab === 'upload' ? '#007bff' : '#f0f0f0',
            color: activeTab === 'upload' ? 'white' : '#333',
            border: 'none',
            borderRadius: '4px 4px 0 0',
            cursor: 'pointer',
            fontWeight: activeTab === 'upload' ? 'bold' : 'normal'
          }}
        >
          📄 Document Upload
        </button>
        <button
          onClick={() => setActiveTab('timeline')}
          style={{
            padding: '12px 24px',
            fontSize: '16px',
            backgroundColor: activeTab === 'timeline' ? '#007bff' : '#f0f0f0',
            color: activeTab === 'timeline' ? 'white' : '#333',
            border: 'none',
            borderRadius: '4px 4px 0 0',
            cursor: 'pointer',
            fontWeight: activeTab === 'timeline' ? 'bold' : 'normal'
          }}
        >
          📊 Timeline View
        </button>
      </div>

      {activeTab === 'upload' && <DocumentUpload />}
      {activeTab === 'timeline' && <UnifiedTimeline personId="" />}
      
      <div style={{ marginTop: '40px', padding: '20px', backgroundColor: '#f0f0f0', borderRadius: '8px' }}>
        <h3>🔗 Quick Links:</h3>
        <ul>
          <li><a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">API Documentation</a></li>
          <li><a href="http://localhost:8000/api/review-queue/pending" target="_blank" rel="noopener noreferrer">Review Queue (API)</a></li>
          <li><a href="http://localhost:8000/api/v1/common/persons" target="_blank" rel="noopener noreferrer">View Persons</a></li>
        </ul>
      </div>
    </div>
  );
}
