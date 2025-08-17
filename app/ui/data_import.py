"""
Data Import UI for 7taps Analytics.

Simple interface for uploading CSV polls data and audio files.
"""

import json
import os
from typing import Any, Dict

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

# Templates
templates = Jinja2Templates(directory="templates")


@router.get("/data-import", response_class=HTMLResponse)
async def data_import_page(request: Request):
    """Data import interface page."""

    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>7taps Analytics - Data Import</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                padding: 30px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            }
            h1 {
                color: #667eea;
                text-align: center;
                margin-bottom: 30px;
            }
            .section {
                margin-bottom: 40px;
                padding: 20px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
            .section h2 {
                color: #667eea;
                margin-top: 0;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                font-weight: 500;
            }
            input[type="file"], input[type="text"], textarea {
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
            textarea {
                height: 100px;
                resize: vertical;
            }
            .btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 16px;
                font-weight: 500;
                transition: all 0.3s ease;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
            }
            .btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            .result {
                margin-top: 20px;
                padding: 15px;
                border-radius: 6px;
                display: none;
            }
            .success {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .error {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            .template {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 6px;
                margin-top: 10px;
            }
            .template pre {
                margin: 0;
                font-size: 12px;
                overflow-x: auto;
            }
            .stats {
                background: #e3f2fd;
                padding: 15px;
                border-radius: 6px;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Data Import</h1>
            
            <div class="section">
                <h2>📋 CSV Polls Data Import</h2>
                <p>Upload CSV file with polls data in the required format.</p>
                
                <div class="template">
                    <strong>Required CSV Format:</strong>
                    <pre>timestamp,user_id,card_type,question,response,score,metadata
2024-01-15T10:30:00Z,user123,Poll,How satisfied are you?,Very satisfied,100,{"category": "satisfaction"}
2024-01-15T10:35:00Z,user124,Quiz,What is 2+2?,4,100,{"category": "math"}</pre>
                    
                    <strong>📋 xAPI Field Mapping:</strong>
                    <ul style="font-size: 12px; margin-top: 10px;">
                        <li><strong>user_id</strong> → actor.id (https://7taps.com/users/{user_id})</li>
                        <li><strong>timestamp</strong> → statement.timestamp</li>
                        <li><strong>card_type</strong> → context.extensions.card-type</li>
                        <li><strong>question</strong> → object.definition.name.en-US</li>
                        <li><strong>response</strong> → result.response</li>
                        <li><strong>score</strong> → result.score.raw</li>
                        <li><strong>metadata</strong> → object.definition.extensions.poll-metadata</li>
                    </ul>
                </div>
                
                <form id="pollsForm" enctype="multipart/form-data">
                    <div class="form-group">
                        <label for="pollsFile">CSV File:</label>
                        <input type="file" id="pollsFile" name="polls_file" accept=".csv" required>
                    </div>
                    <div class="form-group">
                        <label for="userId">User ID:</label>
                        <input type="text" id="userId" name="user_id" placeholder="user123" required>
                    </div>
                    <div class="form-group">
                        <label for="metadata">Metadata (JSON):</label>
                        <textarea id="metadata" name="metadata" placeholder='{"source": "manual_import", "batch": "batch_001"}'></textarea>
                    </div>
                    <button type="submit" class="btn">Import Polls Data</button>
                </form>
                
                <div id="pollsResult" class="result"></div>
            </div>
            
            <div class="section">
                <h2>🎤 Audio File Upload</h2>
                <p>Upload audio files for transcription and analysis.</p>
                
                <form id="audioForm" enctype="multipart/form-data">
                    <div class="form-group">
                        <label for="audioFile">Audio File:</label>
                        <input type="file" id="audioFile" name="audio_file" accept="audio/*" required>
                    </div>
                    <div class="form-group">
                        <label for="audioUserId">User ID:</label>
                        <input type="text" id="audioUserId" name="user_id" placeholder="user123" required>
                    </div>
                    <div class="form-group">
                        <label for="audioMetadata">Metadata (JSON):</label>
                        <textarea id="audioMetadata" name="metadata" placeholder='{"context": "voice_feedback", "language": "en"}'></textarea>
                    </div>
                    <button type="submit" class="btn">Upload Audio</button>
                </form>
                
                <div id="audioResult" class="result"></div>
            </div>
            
            <div class="section">
                <h2>📈 Import Statistics</h2>
                <div id="stats" class="stats">
                    <p>Loading statistics...</p>
                </div>
                <button onclick="loadStats()" class="btn">Refresh Stats</button>
            </div>
        </div>
        
        <script>
            // Polls form submission
            document.getElementById('pollsForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const formData = new FormData();
                const fileInput = document.getElementById('pollsFile');
                const userId = document.getElementById('userId').value;
                const metadata = document.getElementById('metadata').value || '{}';
                
                formData.append('polls_file', fileInput.files[0]);
                formData.append('user_id', userId);
                formData.append('metadata', metadata);
                
                const resultDiv = document.getElementById('pollsResult');
                resultDiv.style.display = 'block';
                resultDiv.className = 'result';
                resultDiv.innerHTML = 'Importing polls data...';
                
                try {
                    const response = await fetch('/api/import/batch', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        resultDiv.className = 'result success';
                        resultDiv.innerHTML = `
                            <strong>✅ Import Successful!</strong><br>
                            Total imported: ${result.total_imported}<br>
                            Polls imported: ${result.polls_imported}<br>
                            Errors: ${result.errors}
                        `;
                    } else {
                        resultDiv.className = 'result error';
                        resultDiv.innerHTML = `<strong>❌ Import Failed:</strong> ${result.detail || 'Unknown error'}`;
                    }
                } catch (error) {
                    resultDiv.className = 'result error';
                    resultDiv.innerHTML = `<strong>❌ Error:</strong> ${error.message}`;
                }
                
                loadStats();
            });
            
            // Audio form submission
            document.getElementById('audioForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const formData = new FormData();
                const fileInput = document.getElementById('audioFile');
                const userId = document.getElementById('audioUserId').value;
                const metadata = document.getElementById('audioMetadata').value || '{}';
                
                formData.append('file', fileInput.files[0]);
                formData.append('user_id', userId);
                formData.append('metadata', metadata);
                
                const resultDiv = document.getElementById('audioResult');
                resultDiv.style.display = 'block';
                resultDiv.className = 'result';
                resultDiv.innerHTML = 'Uploading and processing audio...';
                
                try {
                    const response = await fetch('/api/import/audio', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        resultDiv.className = 'result success';
                        resultDiv.innerHTML = `
                            <strong>✅ Audio Upload Successful!</strong><br>
                            File ID: ${result.file_id}<br>
                            Transcription: ${result.transcription}<br>
                            Message: ${result.message}
                        `;
                    } else {
                        resultDiv.className = 'result error';
                        resultDiv.innerHTML = `<strong>❌ Upload Failed:</strong> ${result.detail || 'Unknown error'}`;
                    }
                } catch (error) {
                    resultDiv.className = 'result error';
                    resultDiv.innerHTML = `<strong>❌ Error:</strong> ${error.message}`;
                }
                
                loadStats();
            });
            
            // Load statistics
            async function loadStats() {
                const statsDiv = document.getElementById('stats');
                
                try {
                    const response = await fetch('/api/import/stats');
                    const stats = await response.json();
                    
                    statsDiv.innerHTML = `
                        <strong>📊 Current Statistics:</strong><br>
                        Total Statements: ${stats.total_statements}<br>
                        Total Actors: ${stats.total_actors}<br>
                        Total Activities: ${stats.total_activities}<br>
                        Total Verbs: ${stats.total_verbs}<br>
                        <br>
                        <strong>Data Sources:</strong><br>
                        • xAPI Ingestion: Live data from 7taps<br>
                        • Polls Import: CSV data uploads<br>
                        • Audio Upload: Voice recordings<br>
                        <br>
                        Last Updated: ${new Date(stats.last_updated).toLocaleString()}
                    `;
                } catch (error) {
                    statsDiv.innerHTML = `<strong>❌ Error loading stats:</strong> ${error.message}`;
                }
            }
            
            // Load stats on page load
            loadStats();
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)
