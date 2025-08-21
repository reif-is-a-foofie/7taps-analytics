#!/usr/bin/env python3
"""
Fix Duplicate Users Script

This script identifies and fixes duplicate users in the database by:
1. Finding users with similar names but different casing/formatting
2. Merging duplicate user records
3. Normalizing user IDs to a consistent format
4. Updating related tables to use the normalized user IDs
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection"""
    try:
        DATABASE_URL = os.getenv('DATABASE_URL')
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is not set")
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        
        return psycopg2.connect(DATABASE_URL, sslmode=os.getenv('PGSSLMODE', 'require'))
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

def normalize_user_id(user_id):
    """Normalize user ID to consistent format"""
    if not user_id:
        return None
    
    # Convert to lowercase and replace spaces with underscores
    normalized = user_id.lower().replace(' ', '_')
    
    # Handle special cases
    if 'anonymous_learner' in normalized:
        # Extract number and format consistently
        import re
        match = re.search(r'(\d+)', normalized)
        if match:
            return f"anonymous_learner_{match.group(1)}"
    
    return normalized

def find_duplicate_users():
    """Find users with duplicate names but different IDs"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get all users
            cur.execute("SELECT id, user_id, cohort FROM users ORDER BY user_id")
            users = cur.fetchall()
            
            # Group by normalized user_id
            user_groups = {}
            for user in users:
                normalized_id = normalize_user_id(user['user_id'])
                if normalized_id not in user_groups:
                    user_groups[normalized_id] = []
                user_groups[normalized_id].append(user)
            
            # Find duplicates
            duplicates = {k: v for k, v in user_groups.items() if len(v) > 1}
            
            return duplicates
    finally:
        conn.close()

def merge_duplicate_users(duplicates):
    """Merge duplicate user records"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            for normalized_id, users in duplicates.items():
                logger.info(f"Processing duplicates for: {normalized_id}")
                logger.info(f"Found {len(users)} duplicate records")
                
                # Sort by ID to keep the lowest ID as primary
                users.sort(key=lambda x: x['id'])
                primary_user = users[0]
                duplicate_users = users[1:]
                
                logger.info(f"Keeping primary user: ID {primary_user['id']} ({primary_user['user_id']})")
                
                # Update primary user with normalized ID
                cur.execute(
                    "UPDATE users SET user_id = %s WHERE id = %s",
                    (normalized_id, primary_user['id'])
                )
                
                # Update all related tables to use primary user ID
                for duplicate in duplicate_users:
                    logger.info(f"Updating references from user ID {duplicate['id']} to {primary_user['id']}")
                    
                    # Update user_activities
                    cur.execute(
                        "UPDATE user_activities SET user_id = %s WHERE user_id = %s",
                        (primary_user['id'], duplicate['id'])
                    )
                    
                    # Update user_responses
                    cur.execute(
                        "UPDATE user_responses SET user_id = %s WHERE user_id = %s",
                        (primary_user['id'], duplicate['id'])
                    )
                    
                    # Delete duplicate user
                    cur.execute("DELETE FROM users WHERE id = %s", (duplicate['id'],))
                
                logger.info(f"Successfully merged {len(duplicate_users)} duplicate records")
            
            conn.commit()
            logger.info("All duplicate users merged successfully")
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Error merging duplicate users: {e}")
        raise
    finally:
        conn.close()

def verify_unique_users():
    """Verify that users are now unique"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get all users
            cur.execute("SELECT id, user_id, cohort FROM users ORDER BY user_id")
            users = cur.fetchall()
            
            # Check for duplicates
            user_ids = [user['user_id'] for user in users]
            unique_user_ids = set(user_ids)
            
            logger.info(f"Total user records: {len(users)}")
            logger.info(f"Unique user IDs: {len(unique_user_ids)}")
            
            if len(users) == len(unique_user_ids):
                logger.info("✅ All users are now unique!")
                return True
            else:
                logger.warning("⚠️  Still have duplicate users")
                return False
    finally:
        conn.close()

def main():
    """Main function to fix duplicate users"""
    logger.info("🔍 Starting duplicate user cleanup...")
    
    try:
        # Find duplicates
        logger.info("Finding duplicate users...")
        duplicates = find_duplicate_users()
        
        if not duplicates:
            logger.info("✅ No duplicate users found!")
            return
        
        logger.info(f"Found {len(duplicates)} groups of duplicate users:")
        for normalized_id, users in duplicates.items():
            logger.info(f"  {normalized_id}: {len(users)} records")
            for user in users:
                logger.info(f"    - ID {user['id']}: {user['user_id']}")
        
        # Ask for confirmation
        response = input("\nProceed with merging duplicate users? (y/N): ")
        if response.lower() != 'y':
            logger.info("Operation cancelled")
            return
        
        # Merge duplicates
        logger.info("Merging duplicate users...")
        merge_duplicate_users(duplicates)
        
        # Verify results
        logger.info("Verifying results...")
        verify_unique_users()
        
        logger.info("✅ Duplicate user cleanup completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error during duplicate user cleanup: {e}")
        raise

if __name__ == "__main__":
    main()
