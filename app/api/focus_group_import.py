"""
Focus Group CSV Import API for 7taps Analytics.

This module handles the specific CSV format from focus group data
and transforms it into xAPI statements with cohort support.
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
from io import StringIO
import asyncio

from app.data_normalization import DataNormalizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class FocusGroupImportRequest(BaseModel):
    """Request model for focus group data import."""
    csv_data: str
    cohort_name: str = "focus_group_2024"
    lesson_mapping: Optional[Dict[str, str]] = None

class ImportResult(BaseModel):
    """Result model for import operations."""
    success: bool
    imported_count: int
    error_count: int
    cohort_id: str
    message: str
    timestamp: datetime = datetime.utcnow()

class CohortAnalytics(BaseModel):
    """Cohort analytics data."""
    cohort_id: str
    total_learners: int
    total_responses: int
    card_types: Dict[str, int]
    lesson_distribution: Dict[str, int]
    response_patterns: Dict[str, Any]

# Global normalizer instance - lazy initialization
normalizer = None

def get_normalizer():
    """Get or create normalizer instance."""
    global normalizer
    if normalizer is None:
        normalizer = DataNormalizer()
    return normalizer

# Lesson URL mapping for focus group data
LESSON_URL_MAPPING = {
    "1": "https://7taps.com/lessons/digital-wellness-foundations",
    "2": "https://7taps.com/lessons/screen-habits-awareness", 
    "3": "https://7taps.com/lessons/device-relationship",
    "4": "https://7taps.com/lessons/productivity-focus",
    "5": "https://7taps.com/lessons/connection-balance"
}

def parse_focus_group_csv(csv_data: str) -> List[Dict[str, Any]]:
    """Parse focus group CSV data into structured format."""
    try:
        # Read CSV data
        df = pd.read_csv(StringIO(csv_data))
        
        # Expected columns for focus group data
        expected_columns = [
            'Learner', 'Card', 'Card type', 'Lesson Number', 
            'Global Q#', 'PDF Page #', 'Response'
        ]
        
        # Validate columns
        missing_columns = [col for col in expected_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Convert to list of dictionaries
        focus_group_data = []
        for _, row in df.iterrows():
            record = {
                'learner': row['Learner'],
                'card': row['Card'],
                'card_type': row['Card type'],
                'lesson_number': row['Lesson Number'],
                'global_q': row['Global Q#'],
                'pdf_page': row['PDF Page #'],
                'response': row['Response']
            }
            focus_group_data.append(record)
        
        return focus_group_data
        
    except Exception as e:
        logger.error(f"Error parsing focus group CSV data: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid CSV format: {str(e)}")

def extract_card_info(card_text: str) -> Dict[str, Any]:
    """Extract structured information from card text."""
    card_info = {
        'card_number': None,
        'card_type': None,
        'question': None,
        'description': None
    }
    
    try:
        # Extract card number and type
        if '(' in card_text and ')' in card_text:
            # Format: "Card 6 (Form): 🧠 Quick pulse check..."
            parts = card_text.split('(', 1)
            if len(parts) >= 2:
                card_number_part = parts[0].strip()
                card_info['card_number'] = card_number_part.replace('Card', '').strip()
                
                type_part = parts[1].split(')', 1)[0].strip()
                card_info['card_type'] = type_part
                
                # Extract question after the colon
                if ':' in card_text:
                    question_part = card_text.split(':', 1)[1].strip()
                    card_info['question'] = question_part
    except Exception as e:
        logger.warning(f"Error extracting card info from '{card_text}': {e}")
    
    return card_info

def convert_focus_group_to_xapi_statement(record: Dict[str, Any], cohort_id: str) -> Dict[str, Any]:
    """Convert focus group record to xAPI statement format."""
    
    # Extract card information
    card_info = extract_card_info(record['card'])
    
    # Create unique statement ID
    statement_id = f"focus_group_{cohort_id}_{record['learner'].replace(' ', '_')}_{record['lesson_number']}_{record['global_q']}"
    
    # Create xAPI statement structure with proper field mapping
    statement = {
        'id': statement_id,
        'actor': {
            'objectType': 'Agent',
            'id': f"https://7taps.com/users/{record['learner'].replace(' ', '_')}",  # Proper xAPI actor.id
            'name': record['learner'],
            'account': {
                'name': record['learner'].replace(' ', '_'),
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
            'id': f"https://7taps.com/activities/focus_group_card_{card_info.get('card_number', record['global_q'])}",
            'objectType': 'Activity',
            'definition': {
                'name': {
                    'en-US': card_info.get('question', record['card'])
                },
                'description': {
                    'en-US': f"Focus group {record['card_type']} question from lesson {record['lesson_number']}"
                },
                'interactionType': 'choice',
                'extensions': {
                    'https://7taps.com/card-type': record['card_type'],
                    'https://7taps.com/card-number': card_info.get('card_number'),
                    'https://7taps.com/lesson-number': str(record['lesson_number']),
                    'https://7taps.com/global-q': str(record['global_q']),
                    'https://7taps.com/pdf-page': str(record['pdf_page']),
                    'https://7taps.com/cohort': cohort_id
                }
            }
        },
        'result': {
            'success': True,
            'completion': True,
            'response': record['response'],
            'extensions': {
                'https://7taps.com/response-length': len(record['response']) if record['response'] else 0
            }
        },
        'context': {
            'platform': '7taps',
            'language': 'en-US',
            'registration': cohort_id,
            'extensions': {
                'https://7taps.com/cohort-id': cohort_id,
                'https://7taps.com/lesson-url': LESSON_URL_MAPPING.get(str(record['lesson_number']), ''),
                'https://7taps.com/source': 'focus_group_import'
            }
        },
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.3'
    }
    
    return statement

async def import_focus_group_data(request: FocusGroupImportRequest) -> ImportResult:
    """Import focus group data from CSV format."""
    try:
        # Parse CSV data
        focus_group_data = parse_focus_group_csv(request.csv_data)
        
        # Generate cohort ID
        cohort_id = f"cohort_{request.cohort_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Convert and normalize each record
        imported_count = 0
        error_count = 0
        
        for record in focus_group_data:
            try:
                # Convert to xAPI statement
                statement = convert_focus_group_to_xapi_statement(record, cohort_id)
                
                # Normalize using existing system
                await get_normalizer().process_statement_normalization(statement)
                
                imported_count += 1
                logger.info(f"Successfully imported focus group record: {statement['id']}")
                
            except Exception as e:
                error_count += 1
                logger.error(f"Error importing focus group record: {e}")
        
        return ImportResult(
            success=True,
            imported_count=imported_count,
            error_count=error_count,
            cohort_id=cohort_id,
            message=f"Successfully imported {imported_count} focus group records to cohort {cohort_id}"
        )
        
    except Exception as e:
        logger.error(f"Error in focus group import: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import/focus-group", response_model=ImportResult)
async def import_focus_group_csv(request: FocusGroupImportRequest):
    """Import focus group CSV data."""
    return await import_focus_group_data(request)

@router.post("/import/focus-group/file")
async def import_focus_group_file(
    file: UploadFile = File(...),
    cohort_name: str = Form(default="focus_group_2024")
):
    """Import focus group data from uploaded CSV file."""
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV file")
        
        # Read file content
        csv_content = await file.read()
        csv_data = csv_content.decode('utf-8')
        
        # Create import request
        request = FocusGroupImportRequest(
            csv_data=csv_data,
            cohort_name=cohort_name
        )
        
        # Import data
        return await import_focus_group_data(request)
        
    except Exception as e:
        logger.error(f"Error importing focus group file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/import/focus-group/template")
async def get_focus_group_template():
    """Get CSV template for focus group data import."""
    template_data = {
        "columns": [
            "Learner",
            "Card", 
            "Card type",
            "Lesson Number",
            "Global Q#",
            "PDF Page #",
            "Response"
        ],
        "xapi_field_mapping": {
            "Learner": "actor.id (maps to https://7taps.com/users/{learner_name})",
            "Card": "object.definition.name.en-US",
            "Card type": "object.definition.extensions.card-type",
            "Lesson Number": "object.definition.extensions.lesson-number",
            "Global Q#": "object.definition.extensions.global-q",
            "PDF Page #": "object.definition.extensions.pdf-page",
            "Response": "result.response"
        },
        "example": [
            "Audrey Todd",
            "Card 6 (Form): 🧠 Quick pulse check...",
            "Form",
            "1",
            "1",
            "6",
            "Screen time Productivity Stress management Sleep Real life connection"
        ],
        "card_types": ["Form", "Poll", "Quiz", "Submit media"],
        "description": "Upload CSV file with focus group data. All columns are required. Learner names will be converted to unique user IDs for xAPI compatibility."
    }
    
    return template_data

@router.get("/analytics/cohorts")
async def get_cohort_analytics():
    """Get analytics for all cohorts."""
    try:
        # Get cohort data from normalized tables
        async with get_normalizer().get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Get unique cohorts
                cursor.execute("""
                    SELECT DISTINCT context_registration as cohort_id
                    FROM statements_normalized 
                    WHERE context_registration IS NOT NULL
                    AND context_registration LIKE 'cohort_%'
                """)
                cohorts = [row[0] for row in cursor.fetchall()]
                
                cohort_analytics = []
                for cohort_id in cohorts:
                    # Get cohort statistics
                    cursor.execute("""
                        SELECT 
                            COUNT(DISTINCT actor_id) as total_learners,
                            COUNT(*) as total_responses,
                            COUNT(DISTINCT object_id) as unique_activities
                        FROM statements_normalized 
                        WHERE context_registration = %s
                    """, (cohort_id,))
                    
                    stats = cursor.fetchone()
                    
                    # Get card type distribution
                    cursor.execute("""
                        SELECT 
                            raw_statement->'object'->'definition'->'extensions'->>'https://7taps.com/card-type' as card_type,
                            COUNT(*) as count
                        FROM statements_normalized 
                        WHERE context_registration = %s
                        GROUP BY card_type
                    """, (cohort_id,))
                    
                    card_types = {row[0]: row[1] for row in cursor.fetchall() if row[0]}
                    
                    cohort_analytics.append({
                        'cohort_id': cohort_id,
                        'total_learners': stats[0],
                        'total_responses': stats[1],
                        'unique_activities': stats[2],
                        'card_types': card_types
                    })
                
                return {
                    'cohorts': cohort_analytics,
                    'total_cohorts': len(cohorts),
                    'last_updated': datetime.utcnow().isoformat()
                }
                
    except Exception as e:
        logger.error(f"Error getting cohort analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/cohorts/{cohort_id}")
async def get_cohort_detail(cohort_id: str):
    """Get detailed analytics for a specific cohort."""
    try:
        async with get_normalizer().get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Get cohort statistics
                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT actor_id) as total_learners,
                        COUNT(*) as total_responses,
                        COUNT(DISTINCT object_id) as unique_activities,
                        MIN(timestamp) as first_response,
                        MAX(timestamp) as last_response
                    FROM statements_normalized 
                    WHERE context_registration = %s
                """, (cohort_id,))
                
                stats = cursor.fetchone()
                
                # Get learner responses
                cursor.execute("""
                    SELECT 
                        actor_id,
                        COUNT(*) as response_count,
                        MIN(timestamp) as first_response,
                        MAX(timestamp) as last_response
                    FROM statements_normalized 
                    WHERE context_registration = %s
                    GROUP BY actor_id
                    ORDER BY response_count DESC
                """, (cohort_id,))
                
                learners = [
                    {
                        'learner_id': row[0],
                        'response_count': row[1],
                        'first_response': row[2].isoformat() if row[2] else None,
                        'last_response': row[3].isoformat() if row[3] else None
                    }
                    for row in cursor.fetchall()
                ]
                
                # Get response patterns
                cursor.execute("""
                    SELECT 
                        raw_statement->'object'->'definition'->'extensions'->>'https://7taps.com/card-type' as card_type,
                        raw_statement->'object'->'definition'->'extensions'->>'https://7taps.com/lesson-number' as lesson_number,
                        COUNT(*) as response_count
                    FROM statements_normalized 
                    WHERE context_registration = %s
                    GROUP BY card_type, lesson_number
                    ORDER BY lesson_number, card_type
                """, (cohort_id,))
                
                response_patterns = [
                    {
                        'card_type': row[0],
                        'lesson_number': row[1],
                        'response_count': row[2]
                    }
                    for row in cursor.fetchall()
                ]
                
                return {
                    'cohort_id': cohort_id,
                    'statistics': {
                        'total_learners': stats[0],
                        'total_responses': stats[1],
                        'unique_activities': stats[2],
                        'first_response': stats[3].isoformat() if stats[3] else None,
                        'last_response': stats[4].isoformat() if stats[4] else None
                    },
                    'learners': learners,
                    'response_patterns': response_patterns
                }
                
    except Exception as e:
        logger.error(f"Error getting cohort detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))
