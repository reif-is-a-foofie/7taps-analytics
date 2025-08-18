"""
CSV to xAPI Converter for 7taps Analytics

This module transforms focus group CSV data into xAPI statements
that can be ingested through the standard xAPI pipeline.
This ensures all data goes through a single, consistent processing flow.
"""

import os
import json
import logging
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from io import StringIO
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lesson URL mapping for focus group data
LESSON_URL_MAPPING = {
    "1": "https://courses.practiceoflife.com/yjG39Clb0pSm",
    "2": "https://courses.practiceoflife.com/MvkYVHvEN4Hb",
    "3": "https://courses.practiceoflife.com/Zok0kSoRgEIw3", 
    "4": "https://courses.practiceoflife.com/RmxObSV4WnUg",
    "5": "https://courses.practiceoflife.com/vrOAjFjBlyi2",
    "6": "https://courses.practiceoflife.com/JPrMbTY79qFa",
    "7": "https://courses.practiceoflife.com/7VQokTlyontV",
    "8": "https://courses.practiceoflife.com/7VQokTlyontV",
    "9": "https://courses.practiceoflife.com/krpkZuOlYRfZ",
    "10": "https://courses.practiceoflife.com/qaybLiEMwZh0"
}

# Lesson name mapping
LESSON_NAME_MAPPING = {
    "1": "Digital Wellness Foundations",
    "2": "Screen Habits Awareness",
    "3": "Device Relationship",
    "4": "Productivity Focus", 
    "5": "Connection Balance",
    "6": "Digital Mindfulness",
    "7": "Technology Boundaries",
    "8": "Digital Detox",
    "9": "Intentional Tech Use",
    "10": "Digital Wellness Integration"
}

def extract_card_info(card_text: str) -> Dict[str, Any]:
    """Extract structured information from card text."""
    try:
        # Extract card number
        card_number = None
        if 'Card ' in card_text:
            card_match = card_text.split('Card ')[1].split(' ')[0]
            if card_match.isdigit():
                card_number = int(card_match)
        
        # Extract card type
        card_type = None
        if '(' in card_text and ')' in card_text:
            card_type = card_text.split('(')[1].split(')')[0]
        
        # Extract question text
        question_text = card_text
        if ':' in card_text:
            question_text = card_text.split(':', 1)[1].strip()
        
        return {
            'card_number': card_number,
            'card_type': card_type,
            'question_text': question_text,
            'full_card_text': card_text
        }
    except Exception as e:
        logger.warning(f"Error extracting card info from '{card_text}': {e}")
        return {
            'card_number': None,
            'card_type': None,
            'question_text': card_text,
            'full_card_text': card_text
        }

def normalize_actor_id(learner_name: str) -> str:
    """Normalize learner name to actor ID."""
    return learner_name.lower().replace(' ', '_').replace('-', '_')

def create_xapi_statement_from_csv_row(row: Dict[str, Any], base_timestamp: datetime) -> Dict[str, Any]:
    """Convert a CSV row to an xAPI statement."""
    
    # Extract card information
    card_info = extract_card_info(row['Card'])
    
    # Create unique statement ID
    statement_id = str(uuid.uuid4())
    
    # Normalize actor ID
    actor_id = normalize_actor_id(row['Learner'])
    
    # Create activity ID
    activity_id = f"https://7taps.com/activities/focus_group_card_{row['Global Q#']}"
    
    # Add some time variation to avoid all statements having the same timestamp
    timestamp_offset = timedelta(minutes=int(row['Global Q#']) * 2)  # 2 minutes per question
    statement_timestamp = base_timestamp + timestamp_offset
    
    # Build xAPI statement
    xapi_statement = {
        "id": statement_id,
        "actor": {
            "objectType": "Agent",
            "name": row['Learner'],
            "account": {
                "name": actor_id,
                "homePage": "https://7taps.com"
            }
        },
        "verb": {
            "id": "http://adlnet.gov/expapi/verbs/answered",
            "display": {
                "en-US": "answered"
            }
        },
        "object": {
            "objectType": "Activity",
            "id": activity_id,
            "definition": {
                "name": {
                    "en-US": card_info['question_text'] or row['Card']
                },
                "description": {
                    "en-US": f"Focus group {row['Card type']} question from lesson {row['Lesson Number']}"
                },
                "type": f"http://adlnet.gov/expapi/activities/{row['Card type'].lower()}"
            }
        },
        "result": {
            "response": row['Response'],
            "success": True,
            "completion": True
        },
        "context": {
            "platform": "7taps",
            "language": "en-US",
            "extensions": {
                # Preserve all the rich metadata from CSV
                "https://7taps.com/lesson-number": str(row['Lesson Number']),
                "https://7taps.com/lesson-name": LESSON_NAME_MAPPING.get(str(row['Lesson Number']), f"Lesson {row['Lesson Number']}"),
                "https://7taps.com/lesson-url": LESSON_URL_MAPPING.get(str(row['Lesson Number']), ""),
                "https://7taps.com/global-q": str(row['Global Q#']),
                "https://7taps.com/card-number": str(card_info['card_number']) if card_info['card_number'] else "",
                "https://7taps.com/card-type": row['Card type'],
                "https://7taps.com/pdf-page": str(row['PDF Page #']),
                "https://7taps.com/source": "focus_group_csv",
                "https://7taps.com/full-card-text": card_info['full_card_text'],
                "https://7taps.com/question-text": card_info['question_text'] or "",
                "https://7taps.com/cohort": "focus_group_2024"
            }
        },
        "timestamp": statement_timestamp.isoformat() + "Z",
        "version": "1.0.3",
        "stored": statement_timestamp.isoformat() + "Z"
    }
    
    return xapi_statement

def convert_csv_to_xapi_statements(csv_data: str, base_timestamp: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Convert CSV data to xAPI statements."""
    
    if base_timestamp is None:
        base_timestamp = datetime.utcnow() - timedelta(days=30)  # Default to 30 days ago
    
    try:
        # Parse CSV data
        df = pd.read_csv(StringIO(csv_data))
        
        # Expected columns
        expected_columns = [
            'Learner', 'Card', 'Card type', 'Lesson Number', 
            'Global Q#', 'PDF Page #', 'Response'
        ]
        
        # Validate columns
        missing_columns = [col for col in expected_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Convert each row to xAPI statement
        xapi_statements = []
        for _, row in df.iterrows():
            try:
                xapi_statement = create_xapi_statement_from_csv_row(row, base_timestamp)
                xapi_statements.append(xapi_statement)
            except Exception as e:
                logger.error(f"Error converting row {row.get('Learner', 'unknown')}: {e}")
                continue
        
        logger.info(f"Successfully converted {len(xapi_statements)} CSV rows to xAPI statements")
        return xapi_statements
        
    except Exception as e:
        logger.error(f"Error converting CSV to xAPI statements: {e}")
        raise

def get_conversion_stats(xapi_statements: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Get statistics about the converted xAPI statements."""
    
    if not xapi_statements:
        return {"error": "No statements to analyze"}
    
    # Extract statistics
    unique_learners = set()
    lesson_numbers = set()
    card_types = set()
    total_responses = len(xapi_statements)
    
    for statement in xapi_statements:
        # Count unique learners
        actor_name = statement.get('actor', {}).get('name', 'unknown')
        unique_learners.add(actor_name)
        
        # Count lesson numbers
        lesson_num = statement.get('context', {}).get('extensions', {}).get('https://7taps.com/lesson-number', 'unknown')
        lesson_numbers.add(lesson_num)
        
        # Count card types
        card_type = statement.get('context', {}).get('extensions', {}).get('https://7taps.com/card-type', 'unknown')
        card_types.add(card_type)
    
    return {
        "total_statements": total_responses,
        "unique_learners": len(unique_learners),
        "lessons_covered": len(lesson_numbers),
        "card_types": list(card_types),
        "lesson_numbers": sorted(list(lesson_numbers)),
        "conversion_success": True
    }

def validate_xapi_statements(xapi_statements: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate the converted xAPI statements."""
    
    validation_results = {
        "valid": 0,
        "invalid": 0,
        "errors": []
    }
    
    for i, statement in enumerate(xapi_statements):
        try:
            # Check required fields
            required_fields = ['id', 'actor', 'verb', 'object', 'timestamp']
            for field in required_fields:
                if field not in statement:
                    raise ValueError(f"Missing required field: {field}")
            
            # Check actor structure
            actor = statement.get('actor', {})
            if not actor.get('name') or not actor.get('account', {}).get('name'):
                raise ValueError("Invalid actor structure")
            
            # Check verb structure
            verb = statement.get('verb', {})
            if not verb.get('id'):
                raise ValueError("Invalid verb structure")
            
            # Check object structure
            obj = statement.get('object', {})
            if not obj.get('id') or not obj.get('definition', {}).get('name'):
                raise ValueError("Invalid object structure")
            
            validation_results["valid"] += 1
            
        except Exception as e:
            validation_results["invalid"] += 1
            validation_results["errors"].append(f"Statement {i}: {str(e)}")
    
    return validation_results
