-- Update lesson URLs with correct URLs
UPDATE lessons SET lesson_url = 'https://courses.practiceoflife.com/BppNeFkyEYF9' WHERE lesson_number = 1;
UPDATE lessons SET lesson_url = 'https://courses.practiceoflife.com/GOOqyTkVqnIk' WHERE lesson_number = 2;
UPDATE lessons SET lesson_url = 'https://courses.practiceoflife.com/VyyZZTDxpncL' WHERE lesson_number = 3;
UPDATE lessons SET lesson_url = 'https://courses.practiceoflife.com/krQ47COePqsY' WHERE lesson_number = 4;
UPDATE lessons SET lesson_url = 'https://courses.practiceoflife.com/4r2P3hAaMxUd' WHERE lesson_number = 5;
UPDATE lessons SET lesson_url = 'https://courses.practiceoflife.com/5EGM9Sj2n6To' WHERE lesson_number = 6;
UPDATE lessons SET lesson_url = 'https://courses.practiceoflife.com/Eqdrni4QVvsa' WHERE lesson_number = 7;
UPDATE lessons SET lesson_url = 'https://courses.practiceoflife.com/xxVEAHPYYOfn' WHERE lesson_number = 8;
UPDATE lessons SET lesson_url = 'https://courses.practiceoflife.com/BpgMMfkyEWuv' WHERE lesson_number = 9;
UPDATE lessons SET lesson_url = 'https://courses.practiceoflife.com/qaybLiEMwZh0' WHERE lesson_number = 10;

-- Update lesson names to match the provided names
UPDATE lessons SET lesson_name = 'You''re Here. Start Strong' WHERE lesson_number = 1;
UPDATE lessons SET lesson_name = 'Where is Your Attention Going?' WHERE lesson_number = 2;
UPDATE lessons SET lesson_name = 'Own Your Mindset' WHERE lesson_number = 3;
UPDATE lessons SET lesson_name = 'Future Proof Your Health' WHERE lesson_number = 4;
UPDATE lessons SET lesson_name = 'Reclaim Your Rest' WHERE lesson_number = 5;
UPDATE lessons SET lesson_name = 'Focus = Superpower' WHERE lesson_number = 6;
UPDATE lessons SET lesson_name = 'Social Media + You' WHERE lesson_number = 7;
UPDATE lessons SET lesson_name = 'Less Stress. More Calm' WHERE lesson_number = 8;
UPDATE lessons SET lesson_name = 'Boost IRL Connection' WHERE lesson_number = 9;
UPDATE lessons SET lesson_name = 'Celebrate Your Wins' WHERE lesson_number = 10;

-- Verify the updates
SELECT lesson_number, lesson_name, lesson_url FROM lessons ORDER BY lesson_number;
