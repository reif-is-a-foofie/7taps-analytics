#!/usr/bin/env python3
"""
Lesson Name Normalization Script

This script creates a mapping from lesson numbers to actual lesson names
based on the 7taps lesson URLs and creates a normalized lesson lookup.
"""

import json
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LessonInfo:
    """Represents a lesson with its metadata."""
    lesson_number: int
    lesson_name: str
    lesson_url: str
    description: Optional[str] = None

class LessonNormalizer:
    """Handles lesson name normalization and mapping."""
    
    def __init__(self):
        self.lesson_mapping = self._create_lesson_mapping()
    
    def _create_lesson_mapping(self) -> Dict[int, LessonInfo]:
        """Create mapping from lesson numbers to lesson info."""
        return {
            1: LessonInfo(
                lesson_number=1,
                lesson_name="You're Here. Start Strong",
                lesson_url="https://courses.practiceoflife.com/BppNeFkyEYF9",
                description="Beginning your digital wellness journey with awareness and intention"
            ),
            2: LessonInfo(
                lesson_number=2,
                lesson_name="Where is Your Attention Going?",
                lesson_url="https://courses.practiceoflife.com/GOOqyTkVqnIk",
                description="Understanding and directing your attention in the digital age"
            ),
            3: LessonInfo(
                lesson_number=3,
                lesson_name="Own Your Mindset",
                lesson_url="https://courses.practiceoflife.com/VyyZZTDxpncL",
                description="Developing a healthy mindset around technology and productivity"
            ),
            4: LessonInfo(
                lesson_number=4,
                lesson_name="Future Proof Your Health",
                lesson_url="https://courses.practiceoflife.com/krQ47COePqsY",
                description="Building sustainable health habits for long-term wellness"
            ),
            5: LessonInfo(
                lesson_number=5,
                lesson_name="Reclaim Your Rest",
                lesson_url="https://courses.practiceoflife.com/4r2P3hAaMxUd",
                description="Optimizing sleep and recovery for better digital wellness"
            ),
            6: LessonInfo(
                lesson_number=6,
                lesson_name="Focus = Superpower",
                lesson_url="https://courses.practiceoflife.com/5EGM9Sj2n6To",
                description="Harnessing deep focus as your productivity superpower"
            ),
            7: LessonInfo(
                lesson_number=7,
                lesson_name="Social Media + You",
                lesson_url="https://courses.practiceoflife.com/Eqdrni4QVvsa",
                description="Building a healthy relationship with social media"
            ),
            8: LessonInfo(
                lesson_number=8,
                lesson_name="Less Stress. More Calm",
                lesson_url="https://courses.practiceoflife.com/xxVEAHPYYOfn",
                description="Managing stress and finding calm in a connected world"
            ),
            9: LessonInfo(
                lesson_number=9,
                lesson_name="Boost IRL Connection",
                lesson_url="https://courses.practiceoflife.com/BpgMMfkyEWuv",
                description="Strengthening real-life relationships and connections"
            ),
            10: LessonInfo(
                lesson_number=10,
                lesson_name="Celebrate Your Wins",
                lesson_url="https://courses.practiceoflife.com/qaybLiEMwZh0",
                description="Acknowledging progress and building sustainable habits"
            )
        }
    
    def get_lesson_name(self, lesson_number: int) -> str:
        """Get the actual lesson name for a lesson number."""
        lesson_info = self.lesson_mapping.get(lesson_number)
        if lesson_info:
            return lesson_info.lesson_name
        return f"Unknown Lesson {lesson_number}"
    
    def get_lesson_info(self, lesson_number: int) -> Optional[LessonInfo]:
        """Get complete lesson info for a lesson number."""
        return self.lesson_mapping.get(lesson_number)
    
    def get_all_lessons(self) -> Dict[int, LessonInfo]:
        """Get all lesson mappings."""
        return self.lesson_mapping.copy()
    
    def normalize_lesson_data(self, lesson_number: int, fallback_name: str = None) -> Dict[str, any]:
        """Normalize lesson data for API responses."""
        lesson_info = self.get_lesson_info(lesson_number)
        
        if lesson_info:
            return {
                "lesson_number": lesson_info.lesson_number,
                "lesson_name": lesson_info.lesson_name,
                "lesson_url": lesson_info.lesson_url,
                "description": lesson_info.description,
                "display_name": f"{lesson_info.lesson_number}. {lesson_info.lesson_name}"
            }
        else:
            return {
                "lesson_number": lesson_number,
                "lesson_name": fallback_name or f"Unknown Lesson {lesson_number}",
                "lesson_url": None,
                "description": None,
                "display_name": f"{lesson_number}. {fallback_name or f'Unknown Lesson {lesson_number}'}"
            }
    
    def export_lesson_mapping(self, output_file: str = "lesson_mapping.json"):
        """Export lesson mapping to JSON file."""
        mapping_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "lessons": {}
        }
        
        for lesson_num, lesson_info in self.lesson_mapping.items():
            mapping_data["lessons"][str(lesson_num)] = {
                "lesson_number": lesson_info.lesson_number,
                "lesson_name": lesson_info.lesson_name,
                "lesson_url": lesson_info.lesson_url,
                "description": lesson_info.description,
                "display_name": f"{lesson_info.lesson_number}. {lesson_info.lesson_name}"
            }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(mapping_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Lesson mapping exported to {output_file}")
        return mapping_data

def main():
    """Main function to demonstrate lesson normalization."""
    normalizer = LessonNormalizer()
    
    # Export the mapping
    mapping_data = normalizer.export_lesson_mapping()
    
    # Show some examples
    print("\n=== Lesson Name Normalization Examples ===")
    for lesson_num in [1, 2, 3, 4, 5]:
        lesson_info = normalizer.get_lesson_info(lesson_num)
        if lesson_info:
            print(f"Lesson {lesson_num}: {lesson_info.lesson_name}")
            print(f"  URL: {lesson_info.lesson_url}")
            print(f"  Description: {lesson_info.description}")
            print()
    
    # Show normalized data format
    print("=== Normalized Lesson Data Format ===")
    normalized = normalizer.normalize_lesson_data(1)
    print(json.dumps(normalized, indent=2))
    
    print(f"\n✅ Lesson normalization system ready!")
    print(f"📊 Mapped {len(normalizer.get_all_lessons())} lessons")
    print(f"💾 Exported to lesson_mapping.json")

if __name__ == "__main__":
    main()