"""
Cloud Function main entry point for xAPI ingestion.
This file serves as the entry point for Google Cloud Functions.
"""

import os
import sys
import json
from flask import Flask, request, jsonify

# Import the cloud function directly since we're in the same directory
from cloud_function_ingestion import cloud_ingest_xapi, get_cloud_function_status

# Create Flask app
app = Flask(__name__)

@app.route('/', methods=['POST', 'PUT', 'OPTIONS'])
def ingest_xapi():
    """Main xAPI ingestion endpoint supporting both POST and PUT methods."""
    try:
        # Convert Flask request to the format expected by cloud_ingest_xapi
        class MockRequest:
            def __init__(self, flask_request):
                self.method = flask_request.method
                self.data = flask_request.get_data()
                self._json = None
                
            def get_json(self):
                if self._json is None:
                    try:
                        self._json = json.loads(self.data.decode('utf-8'))
                    except:
                        self._json = {}
                return self._json
        
        mock_request = MockRequest(request)
        response_json, status_code = cloud_ingest_xapi(mock_request)
        
        return response_json, status_code, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, PUT, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Content-Type': 'application/json'
        }
    
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/status', methods=['GET'])
def status():
    """Health check endpoint."""
    try:
        response_json, status_code = get_cloud_function_status()
        return response_json, status_code, {
            'Content-Type': 'application/json'
        }
    except Exception as e:
        return jsonify({
            'error': 'Status check failed',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
