# Test Case Modeling - Batch AI Safety

## Scenario 1: High-Volume Wellness Course
**Context**: 100 learners, 5 responses each per day = 500 statements/day

### Current Approach (Per Statement):
- 500 API calls/day
- Cost: 500 calls × $0.001 = $0.50/day
- Processing: 500 × 3 seconds = 25 minutes total

### New Batch Approach:

#### Immediate Processing (Critical/High):
- ~5 statements with obvious critical patterns
- 5 immediate API calls
- Processing: 5 × 3 seconds = 15 seconds

#### Direct Flags (Medium Obvious):
- ~10 statements with obvious medium patterns  
- 0 API calls (local rules only)
- Processing: 10 × 0.1 seconds = 1 second

#### Batch Processing (Others):
- ~485 statements queued
- Batch triggers: 10 batches (50 items each) OR 5 batches (2-hour windows)
- API calls: 10 batches × 1 call = 10 calls
- Processing: 10 × 5 seconds = 50 seconds

#### Total New Approach:
- API calls: 15 (5 immediate + 10 batch)
- Cost: 15 calls × $0.001 = $0.015/day (97% savings)
- Processing: 15 + 1 + 50 = 66 seconds total (95% faster)

---

## Scenario 2: Low-Volume Course
**Context**: 20 learners, 2 responses each per day = 40 statements/day

### Current Approach:
- 40 API calls/day
- Cost: $0.04/day

### New Batch Approach:
- Immediate: ~2 statements
- Direct flags: ~3 statements  
- Batch: ~35 statements (1 batch every 2 hours)
- Total API calls: 3 (2 immediate + 1 batch)
- Cost: $0.003/day (92% savings)

---

## Detailed Test Cases

### Test Case 1: Critical Suicide Ideation
```
Input: "I want to kill myself because I can't stop using my phone"
Local Rules: CRITICAL pattern detected ("kill myself")
Decision: Immediate AI analysis
API Call: Yes (1 call)
Processing Time: 2-3 seconds
Result: Flagged as CRITICAL
Actions: Immediate alert, crisis intervention
```

### Test Case 2: Depression Expression
```
Input: "I feel so depressed and hopeless about everything"
Local Rules: MEDIUM pattern detected ("depressed", "hopeless")
Decision: Direct flag (no API needed)
API Call: No (0 calls)
Processing Time: <1 second
Result: Flagged as MEDIUM
Actions: Monitor, mental health resources
```

### Test Case 3: Nuanced Distress
```
Input: "I feel empty inside, like nothing matters anymore"
Local Rules: No obvious patterns
Decision: Add to batch queue
API Call: Later (batch call)
Processing Time: Queued (within 2 hours)
Result: Will be analyzed in batch
Actions: Pending batch analysis
```

### Test Case 4: Normal Learning Content
```
Input: "This lesson is challenging but I'm learning a lot"
Local Rules: No patterns
Decision: Add to batch queue
API Call: Later (batch call)
Processing Time: Queued (within 2 hours)
Result: Will be cleared in batch
Actions: No action needed
```

### Test Case 5: Metaphorical Expression
```
Input: "This assignment is killing me with all the work"
Local Rules: No patterns (metaphor detection)
Decision: Add to batch queue
API Call: Later (batch call)
Processing Time: Queued (within 2 hours)
Result: Will be cleared in batch (metaphor)
Actions: No action needed
```

---

## Batch Processing Examples

### Batch 1: Time-Triggered (2 hours)
```
Queue: 35 items
Trigger: 2 hours elapsed
Batch Size: 35 items
API Call: 1 call for all 35 items
Processing: 5 seconds
Results: 
- 2 flagged (medium severity)
- 33 cleared
Actions: 2 flag posts created, 33 marked as analyzed
```

### Batch 2: Size-Triggered (50 items)
```
Queue: 50 items
Trigger: 50th item added
Batch Size: 50 items
API Call: 1 call for all 50 items
Processing: 5 seconds
Results:
- 5 flagged (various severities)
- 45 cleared
Actions: 5 flag posts created, 45 marked as analyzed
```

### Batch 3: Token-Triggered (100k tokens)
```
Queue: 25 items with long responses
Trigger: 100k tokens estimated
Batch Size: 25 items
API Call: 1 call for all 25 items
Processing: 5 seconds
Results:
- 1 flagged (high severity)
- 24 cleared
Actions: 1 flag post created, 24 marked as analyzed
```

---

## Edge Cases & Error Handling

### Case 1: API Failure During Batch
```
Scenario: Batch of 50 items, API fails
Fallback: 
1. Retry batch with exponential backoff
2. If still fails, process items individually
3. Mark failed items for manual review
Result: System remains operational
```

### Case 2: Queue Overflow
```
Scenario: 1000 items in queue (system overload)
Fallback:
1. Process in smaller batches (25 items each)
2. Prioritize newer items
3. Alert administrators
Result: Graceful degradation
```

### Case 3: Mixed Severity Batch
```
Scenario: Batch contains both critical and normal content
Processing: Single API call handles all severities
Result: Efficient processing with appropriate flagging
```

---

## Performance Metrics

### API Call Reduction:
- **Before**: 100% of statements trigger API calls
- **After**: ~3-5% of statements trigger API calls
- **Savings**: 95-97% reduction

### Processing Speed:
- **Critical flags**: 2-3 seconds (immediate)
- **Obvious flags**: <1 second (instant)
- **Batch items**: Within 2 hours (acceptable delay)

### Accuracy:
- **Critical detection**: 100% (immediate AI)
- **Obvious detection**: 95% (local rules)
- **Nuanced detection**: 90% (batch AI with context)

---

## Implementation Questions

1. **Batch Size**: Should we stick with 50 items, or is this too high/low?

2. **Time Window**: Is 2 hours acceptable for batch processing, or should it be 1 hour?

3. **Priority Handling**: Should critical items in queue be processed immediately regardless of batch size?

4. **Error Recovery**: How many retries should we attempt for failed batches?

5. **Monitoring**: What metrics should we track for batch processing health?

Does this modeling match your expectations? Any adjustments needed?
