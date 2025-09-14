"""
Data Import API for 7taps Analytics.

This module handles CSV polls data import and audio file uploads,
integrating with the existing normalized data structure.
"""

import os
import csv
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import pandas as pd
from io import StringIO, BytesIO
import asyncio
from app.importers.manual_importer import import_focus_group_csv_text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Import DataNormalizer only when needed to avoid startup issues
DataNormalizer = None

class PollsDataImport(BaseModel):
    """Model for polls data import request."""
    csv_data: str
    source: str = "polls_import"
    batch_id: Optional[str] = None

class AudioUploadResponse(BaseModel):
    """Response model for audio upload."""
    success: bool
    file_id: str
    transcription: Optional[str] = None
    message: str
    timestamp: datetime = datetime.utcnow()

class ImportStats(BaseModel):
    """Statistics for data import operations."""
    total_imported: int
    polls_imported: int
    audio_imported: int
    errors: int
    timestamp: datetime = datetime.utcnow()

class FocusGroupImportStats(BaseModel):
    """Statistics for focus-group CSV import."""
    imported: int
    skipped: int
    errors: List[str] = []
    timestamp: datetime = datetime.utcnow()

# Global normalizer instance - lazy initialization
normalizer = None

def get_normalizer():
    """Get or create normalizer instance."""
    global normalizer, DataNormalizer
    if DataNormalizer is None:
        from app.data_normalization import DataNormalizer
    if normalizer is None:
        normalizer = DataNormalizer()
    return normalizer

def parse_polls_csv(csv_data: str) -> List[Dict[str, Any]]:
    """Parse CSV polls data into structured format."""
    try:
        # Read CSV data
        df = pd.read_csv(StringIO(csv_data))
        
        # Expected columns for polls data
        expected_columns = [
            'timestamp', 'user_id', 'card_type', 'question', 
            'response', 'score', 'metadata'
        ]
        
        # Validate columns
        missing_columns = [col for col in expected_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Convert to list of dictionaries
        polls_data = []
        for _, row in df.iterrows():
            poll_record = {
                'timestamp': row['timestamp'],
                'user_id': row['user_id'],
                'card_type': row['card_type'],  # Poll/Form/Quiz/Rate
                'question': row['question'],
                'response': row['response'],
                'score': row['score'] if pd.notna(row['score']) else None,
                'metadata': json.loads(row['metadata']) if pd.notna(row['metadata']) else {}
            }
            polls_data.append(poll_record)
        
        return polls_data
        
    except Exception as e:
        logger.error(f"Error parsing CSV polls data: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid CSV format: {str(e)}")

def convert_poll_to_xapi_statement(poll_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert poll data to xAPI statement format for normalization."""
    
    # Create xAPI statement structure with proper xAPI field mapping
    statement = {
        'id': f"poll_{poll_data['user_id']}_{poll_data['timestamp']}",
        'actor': {
            'objectType': 'Agent',
            'id': f"https://7taps.com/users/{poll_data['user_id']}",  # Proper xAPI actor.id
            'name': f"User {poll_data['user_id']}",
            'account': {
                'name': poll_data['user_id'],
                'homePage': 'https://7taps.com'
            }
        },
        'verb': {
            'id': 'http://adlnet.gov/expapi/verbs/answered',
            'display': {
                'en-US': 'answered'
            }
        },
        'object': {
            'id': f"poll_{poll_data['card_type']}_{hash(poll_data['question'])}",
            'objectType': 'Activity',
            'definition': {
                'name': {
                    'en-US': poll_data['question']
                },
                'description': {
                    'en-US': f"{poll_data['card_type']} question"
                },
                'interactionType': 'choice',
                'extensions': {
                    'https://7taps.com/poll-metadata': poll_data['metadata']
                }
            }
        },
        'result': {
            'success': poll_data['score'] is not None and poll_data['score'] > 0,
            'completion': True,
            'score': {
                'scaled': poll_data['score'] / 100.0 if poll_data['score'] is not None else 0,
                'raw': poll_data['score'] if poll_data['score'] is not None else 0,
                'min': 0,
                'max': 100
            },
            'response': poll_data['response']
        },
        'context': {
            'platform': '7taps',
            'language': 'en-US',
            'extensions': {
                'https://7taps.com/card-type': poll_data['card_type'],
                'https://7taps.com/source': 'polls_import'
            }
        },
        'timestamp': poll_data['timestamp'],
        'version': '1.0.3'
    }
    
    return statement

async def transcribe_audio(audio_file: UploadFile) -> str:
    """Transcribe audio file to text."""
    try:
        # For now, return a placeholder transcription
        # In production, you would integrate with OpenAI Whisper or similar service
        transcription = f"Transcription placeholder for {audio_file.filename}"
        
        logger.info(f"Audio transcription completed for {audio_file.filename}")
        return transcription
        
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        return f"Transcription failed: {str(e)}"

def convert_audio_to_xapi_statement(audio_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert audio data to xAPI statement format."""
    
    statement = {
        'id': f"audio_{audio_data['user_id']}_{audio_data['timestamp']}",
        'actor': {
            'objectType': 'Agent',
            'id': f"https://7taps.com/users/{audio_data['user_id']}",  # Proper xAPI actor.id
            'name': f"User {audio_data['user_id']}",
            'account': {
                'name': audio_data['user_id'],
                'homePage': 'https://7taps.com'
            }
        },
        'verb': {
            'id': 'http://adlnet.gov/expapi/verbs/completed',
            'display': {
                'en-US': 'completed'
            }
        },
        'object': {
            'id': f"audio_recording_{audio_data['file_id']}",
            'objectType': 'Activity',
            'definition': {
                'name': {
                    'en-US': 'Audio Recording'
                },
                'description': {
                    'en-US': 'Voice response recording'
                },
                'interactionType': 'other',
                'extensions': {
                    'https://7taps.com/audio-metadata': {
                        'file_name': audio_data['file_name'],
                        'file_size': audio_data['file_size'],
                        'duration': audio_data.get('duration', 0)
                    }
                }
            }
        },
        'result': {
            'success': True,
            'completion': True,
            'response': audio_data['transcription']
        },
        'context': {
            'platform': '7taps',
            'language': 'en-US',
            'extensions': {
                'https://7taps.com/card-type': 'audio',
                'https://7taps.com/source': 'audio_upload'
            }
        },
        'timestamp': audio_data['timestamp'],
        'version': '1.0.3'
    }
    
    return statement

@router.post("/import/polls", response_model=ImportStats)
async def import_polls_data(request: PollsDataImport):
    """Import polls data from CSV format."""
    try:
        # Parse CSV data
        polls_data = parse_polls_csv(request.csv_data)
        
        # Convert and normalize each poll
        imported_count = 0
        error_count = 0
        
        for poll_data in polls_data:
            try:
                # Convert poll to xAPI statement
                statement = convert_poll_to_xapi_statement(poll_data)
                
                # Normalize using existing system
                await get_normalizer().process_statement_normalization(statement)
                
                imported_count += 1
                logger.info(f"Successfully imported poll: {statement['id']}")
                
            except Exception as e:
                error_count += 1
                logger.error(f"Error importing poll: {e}")
        
        return ImportStats(
            total_imported=imported_count,
            polls_imported=imported_count,
            audio_imported=0,
            errors=error_count
        )
        
    except Exception as e:
        logger.error(f"Error in polls import: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import/audio", response_model=AudioUploadResponse)
async def upload_audio_file(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    card_type: str = Form(default="audio"),
    metadata: str = Form(default="{}")
):
    """Upload and process audio file."""
    try:
        # Validate file type
        if not file.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="File must be an audio file")
        
        # Generate file ID
        file_id = f"audio_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Transcribe audio
        transcription = await transcribe_audio(file)
        
        # Prepare audio data
        audio_data = {
            'file_id': file_id,
            'user_id': user_id,
            'file_name': file.filename,
            'file_size': file.size,
            'card_type': card_type,
            'transcription': transcription,
            'metadata': json.loads(metadata),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Convert to xAPI statement and normalize
        statement = convert_audio_to_xapi_statement(audio_data)
        await get_normalizer().process_statement_normalization(statement)
        
        return AudioUploadResponse(
            success=True,
            file_id=file_id,
            transcription=transcription,
            message=f"Audio file {file.filename} uploaded and processed successfully"
        )
        
    except Exception as e:
        logger.error(f"Error uploading audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import/batch", response_model=ImportStats)
async def batch_import_data(
    polls_file: Optional[UploadFile] = File(None),
    audio_files: List[UploadFile] = File([]),
    user_id: str = Form(...),
    metadata: str = Form(default="{}")
):
    """Batch import polls and audio data."""
    try:
        total_imported = 0
        polls_imported = 0
        audio_imported = 0
        error_count = 0
        
        # Process polls file if provided
        if polls_file:
            try:
                csv_content = await polls_file.read()
                csv_data = csv_content.decode('utf-8')
                
                polls_data = parse_polls_csv(csv_data)
                
                for poll_data in polls_data:
                    try:
                        statement = convert_poll_to_xapi_statement(poll_data)
                        await get_normalizer().process_statement_normalization(statement)
                        polls_imported += 1
                        total_imported += 1
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error importing poll: {e}")
                        
            except Exception as e:
                error_count += 1
                logger.error(f"Error processing polls file: {e}")
        
        # Process audio files
        for audio_file in audio_files:
            try:
                transcription = await transcribe_audio(audio_file)
                
                audio_data = {
                    'file_id': f"audio_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    'user_id': user_id,
                    'file_name': audio_file.filename,
                    'file_size': audio_file.size,
                    'card_type': 'audio',
                    'transcription': transcription,
                    'metadata': json.loads(metadata),
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                statement = convert_audio_to_xapi_statement(audio_data)
                await get_normalizer().process_statement_normalization(statement)
                
                audio_imported += 1
                total_imported += 1
                
            except Exception as e:
                error_count += 1
                logger.error(f"Error processing audio file {audio_file.filename}: {e}")
        
        return ImportStats(
            total_imported=total_imported,
            polls_imported=polls_imported,
            audio_imported=audio_imported,
            errors=error_count
        )
        
    except Exception as e:
        logger.error(f"Error in batch import: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/import/template/polls")
async def get_polls_csv_template():
    """Get CSV template for polls data import."""
    template_data = {
        "columns": [
            "timestamp",
            "user_id", 
            "card_type",
            "question",
            "response",
            "score",
            "metadata"
        ],
        "xapi_field_mapping": {
            "timestamp": "statement.timestamp",
            "user_id": "actor.id (maps to https://7taps.com/users/{user_id})",
            "card_type": "context.extensions.https://7taps.com/card-type",
            "question": "object.definition.name.en-US",
            "response": "result.response",
            "score": "result.score.raw",
            "metadata": "object.definition.extensions.https://7taps.com/poll-metadata"
        },
        "example": [
            "2024-01-15T10:30:00Z",
            "user123",
            "Poll",
            "How satisfied are you with our service?",
            "Very satisfied",
            "100",
            '{"category": "satisfaction", "tags": ["service", "feedback"]}'
        ],
        "card_types": ["Poll", "Form", "Quiz", "Rate"],
        "description": "Upload CSV file with polls data. All columns are required except score (can be null). User ID maps to xAPI actor.id for consistent querying."
    }
    
    return template_data

@router.get("/import/stats")
async def get_import_statistics():
    """Get statistics about imported data."""
    try:
        # Get normalization stats
        norm_stats = await get_normalizer().get_normalization_stats()
        
        return {
            "total_statements": norm_stats.get('statements', 0),
            "total_actors": norm_stats.get('actors', 0),
            "total_activities": norm_stats.get('activities', 0),
            "total_verbs": norm_stats.get('verbs', 0),
            "import_sources": {
                "xapi_ingestion": "Live xAPI data from 7taps",
                "polls_import": "CSV polls data import",
                "audio_upload": "Audio file uploads"
            },
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting import stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import/focus-group-csv", response_model=FocusGroupImportStats)
async def import_focus_group_csv_file(csv_file: UploadFile = File(...), dry_run: bool = Form(False)):
    """Import focus group CSV (normalized form) with idempotency."""
    try:
        content = await csv_file.read()
        text = content.decode('utf-8')
        summary = await import_focus_group_csv_text(text, dry_run=dry_run)
        return FocusGroupImportStats(
            imported=summary.get('imported', 0),
            skipped=summary.get('skipped', 0),
            errors=summary.get('errors', []),
        )
    except Exception as e:
        logger.error(f"Error importing focus group CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))
