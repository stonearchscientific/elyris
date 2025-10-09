import React, { useState } from 'react';

interface UploadResult {
  success: boolean;
  document_id: string;
  document_parse_id: string;
  matched_entities: {
    sender_location_id: string | null;
    recipient_person_id: string | null;
  };
  pending_reviews: number;
  parsed_data: {
    sender: Record<string, any>;
    recipient: Record<string, any>;
    body_preview: string;
  };
}

export default function DocumentUpload() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [docType, setDocType] = useState('benefits_change');
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // Manual entry toggle
  const [useManualEntry, setUseManualEntry] = useState(false);
  
  // Manual Sender (Location) fields
  const [senderName, setSenderName] = useState('');
  const [senderAddress, setSenderAddress] = useState('');
  const [senderCity, setSenderCity] = useState('');
  const [senderState, setSenderState] = useState('');
  const [senderZip, setSenderZip] = useState('');
  
  // Manual Recipient (Person) fields
  const [recipientFirstName, setRecipientFirstName] = useState('');
  const [recipientLastName, setRecipientLastName] = useState('');
  const [recipientDOB, setRecipientDOB] = useState('');

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setError(null);
      setResult(null);

      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    setUploading(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('doc_type', docType);
      
      // Add manual entry data if enabled
      if (useManualEntry) {
        const manualData: any = {};
        
        // Sender data
        if (senderName || senderAddress || senderCity || senderState || senderZip) {
          manualData.sender = {
            organization_name: senderName,
            address: senderAddress,
            city: senderCity,
            state: senderState,
            zip: senderZip,
          };
        }
        
        // Recipient data
        if (recipientFirstName || recipientLastName || recipientDOB) {
          manualData.recipient = {
            first_name: recipientFirstName,
            last_name: recipientLastName,
            dob: recipientDOB || undefined,
          };
        }
        
        if (Object.keys(manualData).length > 0) {
          formData.append('manual_data', JSON.stringify(manualData));
        }
      }

      const response = await fetch('http://localhost:8000/api/documents/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const data: UploadResult = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{ 
      maxWidth: '800px', 
      margin: '0 auto', 
      padding: '20px',
      border: '1px solid #ddd',
      borderRadius: '8px',
      backgroundColor: '#f9f9f9'
    }}>
      <h2>📄 Document Upload</h2>
      <p>Upload a scanned document (image or PDF) for processing</p>

      <div style={{ marginBottom: '20px' }}>
        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
          Document Type:
        </label>
        <select 
          value={docType} 
          onChange={(e) => setDocType(e.target.value)}
          style={{ 
            width: '100%', 
            padding: '8px', 
            fontSize: '14px',
            borderRadius: '4px',
            border: '1px solid #ccc'
          }}
        >
          <option value="benefits_change">Benefits Change Form</option>
          <option value="medical_record">Medical Record</option>
          <option value="iep_document">IEP Document</option>
          <option value="general">General Document</option>
        </select>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
          Select File:
        </label>
        <input 
          type="file" 
          accept="image/*,.pdf"
          onChange={handleFileSelect}
          style={{ 
            width: '100%', 
            padding: '8px',
            fontSize: '14px',
            borderRadius: '4px',
            border: '1px solid #ccc'
          }}
        />
      </div>

      <div style={{ marginBottom: '20px', padding: '12px', backgroundColor: '#f0f8ff', borderRadius: '4px' }}>
        <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
          <input 
            type="checkbox" 
            checked={useManualEntry}
            onChange={(e) => setUseManualEntry(e.target.checked)}
            style={{ marginRight: '8px', width: '18px', height: '18px' }}
          />
          <span style={{ fontWeight: 'bold' }}>📝 Manually enter sender & recipient information</span>
        </label>
      </div>

      {useManualEntry && (
        <div style={{ marginBottom: '20px', padding: '16px', backgroundColor: '#f9f9f9', borderRadius: '4px', border: '1px solid #ddd' }}>
          <h3 style={{ marginTop: 0, marginBottom: '16px' }}>📍 Sender (Location) Information</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px' }}>Organization Name:</label>
              <input 
                type="text"
                value={senderName}
                onChange={(e) => setSenderName(e.target.value)}
                placeholder="e.g., State Benefits Office"
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px' }}>Address:</label>
              <input 
                type="text"
                value={senderAddress}
                onChange={(e) => setSenderAddress(e.target.value)}
                placeholder="e.g., 123 Main St"
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px' }}>City:</label>
              <input 
                type="text"
                value={senderCity}
                onChange={(e) => setSenderCity(e.target.value)}
                placeholder="e.g., Springfield"
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
              />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '8px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px' }}>State:</label>
                <input 
                  type="text"
                  value={senderState}
                  onChange={(e) => setSenderState(e.target.value)}
                  placeholder="IL"
                  maxLength={2}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc', textTransform: 'uppercase' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px' }}>ZIP Code:</label>
                <input 
                  type="text"
                  value={senderZip}
                  onChange={(e) => setSenderZip(e.target.value)}
                  placeholder="62701"
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
                />
              </div>
            </div>
          </div>

          <h3 style={{ marginTop: '16px', marginBottom: '16px' }}>👤 Recipient (Person) Information</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px' }}>First Name:</label>
              <input 
                type="text"
                value={recipientFirstName}
                onChange={(e) => setRecipientFirstName(e.target.value)}
                placeholder="e.g., Spencer"
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px' }}>Last Name:</label>
              <input 
                type="text"
                value={recipientLastName}
                onChange={(e) => setRecipientLastName(e.target.value)}
                placeholder="e.g., Kennedy"
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px' }}>Date of Birth:</label>
              <input 
                type="date"
                value={recipientDOB}
                onChange={(e) => setRecipientDOB(e.target.value)}
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
              />
            </div>
          </div>
        </div>
      )}

      {preview && (
        <div style={{ marginBottom: '20px' }}>
          <p style={{ fontWeight: 'bold', marginBottom: '8px' }}>Preview:</p>
          <img 
            src={preview} 
            alt="Document preview" 
            style={{ 
              maxWidth: '100%', 
              maxHeight: '400px', 
              border: '1px solid #ccc',
              borderRadius: '4px'
            }} 
          />
        </div>
      )}

      <button
        onClick={handleUpload}
        disabled={!selectedFile || uploading}
        style={{
          width: '100%',
          padding: '12px',
          fontSize: '16px',
          fontWeight: 'bold',
          backgroundColor: uploading ? '#ccc' : '#007bff',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: uploading || !selectedFile ? 'not-allowed' : 'pointer'
        }}
      >
        {uploading ? '⏳ Processing...' : '🚀 Upload & Process Document'}
      </button>

      {error && (
        <div style={{ 
          marginTop: '20px', 
          padding: '12px', 
          backgroundColor: '#ffebee',
          border: '1px solid #f44336',
          borderRadius: '4px',
          color: '#c62828'
        }}>
          <strong>❌ Error:</strong> {error}
          <p style={{ fontSize: '12px', marginTop: '8px' }}>
            Note: OCR libraries may not be installed. Check the backend console for details.
          </p>
        </div>
      )}

      {result && (
        <div style={{ marginTop: '20px' }}>
          <div style={{ 
            padding: '12px', 
            backgroundColor: '#e8f5e9',
            border: '1px solid #4caf50',
            borderRadius: '4px',
            marginBottom: '20px'
          }}>
            <strong>✅ Upload Successful!</strong>
            <p>Document ID: <code>{result.document_id}</code></p>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <h3>📊 Processing Results:</h3>
            
            <div style={{ marginBottom: '12px' }}>
              <strong>Matched Entities:</strong>
              <ul style={{ marginLeft: '20px' }}>
                <li>
                  Sender Location: {
                    result.matched_entities.sender_location_id 
                      ? <span style={{ color: 'green' }}>✓ Matched ({result.matched_entities.sender_location_id})</span>
                      : <span style={{ color: 'orange' }}>⚠️ Needs Review</span>
                  }
                </li>
                <li>
                  Recipient Person: {
                    result.matched_entities.recipient_person_id 
                      ? <span style={{ color: 'green' }}>✓ Matched ({result.matched_entities.recipient_person_id})</span>
                      : <span style={{ color: 'orange' }}>⚠️ Needs Review</span>
                  }
                </li>
              </ul>
            </div>

            {result.pending_reviews > 0 && (
              <div style={{ 
                padding: '12px', 
                backgroundColor: '#fff3cd',
                border: '1px solid #ffc107',
                borderRadius: '4px',
                marginBottom: '12px'
              }}>
                <strong>⚠️ {result.pending_reviews} item(s) need manual review</strong>
                <p>Visit the Review Queue to resolve ambiguous matches.</p>
              </div>
            )}

            <details style={{ marginTop: '16px' }}>
              <summary style={{ cursor: 'pointer', fontWeight: 'bold' }}>
                📋 View Parsed Data
              </summary>
              <div style={{ 
                marginTop: '12px', 
                padding: '12px', 
                backgroundColor: '#f5f5f5',
                borderRadius: '4px',
                fontSize: '12px'
              }}>
                <div style={{ marginBottom: '12px' }}>
                  <strong>Sender:</strong>
                  <pre style={{ backgroundColor: 'white', padding: '8px', borderRadius: '4px', overflow: 'auto' }}>
                    {JSON.stringify(result.parsed_data.sender, null, 2)}
                  </pre>
                </div>
                <div style={{ marginBottom: '12px' }}>
                  <strong>Recipient:</strong>
                  <pre style={{ backgroundColor: 'white', padding: '8px', borderRadius: '4px', overflow: 'auto' }}>
                    {JSON.stringify(result.parsed_data.recipient, null, 2)}
                  </pre>
                </div>
                <div>
                  <strong>Body Preview:</strong>
                  <p style={{ backgroundColor: 'white', padding: '8px', borderRadius: '4px' }}>
                    {result.parsed_data.body_preview}
                  </p>
                </div>
              </div>
            </details>
          </div>
        </div>
      )}
    </div>
  );
}

