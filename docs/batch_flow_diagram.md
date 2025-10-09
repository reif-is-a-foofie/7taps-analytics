# Improved Batch AI Safety Flow

## Flow Diagram

```
┌─────────────────┐
│   Content Input │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ Local Rules     │
│ Check           │
└─────────┬───────┘
          │
          ▼
    ┌─────────────┐
    │ Obvious Flag?│
    └─────┬───────┘
          │
     ┌────▼────┐    ┌──────────────┐
     │   YES   │    │     NO       │
     └────┬────┘    └──────┬───────┘
          │                │
          ▼                ▼
┌─────────────────┐ ┌─────────────────┐
│ Severity Check  │ │ Add to Batch    │
│                 │ │ Queue           │
└─────────┬───────┘ └─────────────────┘
          │
          ▼
    ┌─────────────┐
    │ Critical/   │
    │ High?       │
    └─────┬───────┘
          │
     ┌────▼────┐    ┌──────────────┐
     │   YES   │    │     NO       │
     └────┬────┘    └──────┬───────┘
          │                │
          ▼                ▼
┌─────────────────┐ ┌─────────────────┐
│ Run AI          │ │ Create Flag     │
│ Immediately     │ │ Post            │
└─────────┬───────┘ └─────────────────┘
          │
          ▼
┌─────────────────┐
│ Create Flag     │
│ Post            │
└─────────────────┘

┌─────────────────┐
│ Batch Queue     │
│ (100k tokens OR │
│  2 hours OR     │
│  50 items)      │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ Run Batch AI    │
│ Analysis        │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ Process Results │
│ - Flag Posts    │
│ - Mark Analyzed │
└─────────────────┘
```

## Decision Logic

### Step 1: Local Rules Check
```python
CRITICAL_PATTERNS = [
    "kill myself", "suicide", "end my life", "end it all",
    "hurt myself", "self harm", "self-harm"
]

HIGH_PATTERNS = [
    "rape", "raped", "abuse", "abused",
    "hurt you", "kill you", "threaten"
]

MEDIUM_PATTERNS = [
    "depressed", "depression", "hopeless", "hopelessness",
    "empty inside", "nothing matters", "pointless"
]
```

### Step 2: Immediate vs Batch Decision
- **Immediate AI**: ANY obvious flags detected (safety first!)
- **Batch Queue**: No obvious flags detected

### Step 3: Batch Triggers
- **100k tokens**: Rough estimate of content length
- **2 hours**: Time-based processing
- **50 items**: Maximum items per batch

## Test Cases

### Case 1: Critical Obvious Flag
**Input**: "I want to kill myself because I can't stop using my phone"

**Flow**:
1. Local Rules Check → CRITICAL pattern detected
2. Severity Check → Critical → YES
3. Run AI Immediately → API call
4. Create Flag Post → Immediate alert

**Expected Result**: 
- Status: "flagged" 
- Severity: "critical"
- Processing: Immediate (2-3 seconds)
- API Cost: 1 call

### Case 2: Medium Obvious Flag  
**Input**: "I feel so depressed and hopeless about everything"

**Flow**:
1. Local Rules Check → MEDIUM pattern detected
2. Run AI Immediately → API call (safety first!)
3. Create Flag Post → Based on AI analysis

**Expected Result**:
- Status: "flagged"
- Severity: Determined by AI
- Processing: Immediate (2-3 seconds)
- API Cost: 1 call

### Case 3: Nuanced Content
**Input**: "I feel empty inside, like nothing matters anymore"

**Flow**:
1. Local Rules Check → No obvious patterns
2. Add to Batch Queue → Queue item
3. Wait for batch trigger
4. Run Batch AI Analysis → API call (multiple items)
5. Process Results → Flag or clear

**Expected Result**:
- Status: "queued" initially
- Processing: Within 2 hours or batch size
- API Cost: 1 call per batch (shared cost)

### Case 4: Normal Content
**Input**: "This lesson is challenging but I'm learning a lot"

**Flow**:
1. Local Rules Check → No patterns
2. Add to Batch Queue → Queue item
3. Wait for batch trigger  
4. Run Batch AI Analysis → API call
5. Process Results → Mark as clear

**Expected Result**:
- Status: "queued" initially
- Final: Not flagged
- Processing: Batch processing
- API Cost: Shared batch cost

### Case 5: Batch Trigger (Time)
**Scenario**: 10 items in queue, 1.8 hours elapsed

**Flow**:
1. Background processor checks every 5 minutes
2. Time trigger activated (2 hours reached)
3. Process batch of 10 items
4. Single API call for all 10 items
5. Process individual results

**Expected Result**:
- Batch size: 10 items
- API calls: 1 (instead of 10 individual calls)
- Cost savings: 90%

### Case 6: Batch Trigger (Size)
**Scenario**: 50 items queued in 30 minutes

**Flow**:
1. 50th item added to queue
2. Size trigger activated (50 items reached)
3. Process batch immediately
4. Single API call for all 50 items

**Expected Result**:
- Batch size: 50 items
- API calls: 1 (instead of 50 individual calls)  
- Cost savings: 98%

## Benefits Analysis

### Cost Efficiency
- **Before**: Every statement = 1 API call
- **After**: Obvious flags = immediate, others = batched
- **Savings**: 80-95% reduction in API calls

### Performance
- **Critical flags**: Immediate processing (2-3 seconds)
- **Obvious flags**: Instant processing (<1 second)
- **Batch items**: Processed within 2 hours max

### Accuracy
- **Immediate AI**: Full context for critical cases
- **Batch AI**: Efficient processing for nuanced cases
- **Local rules**: Fast filtering for obvious cases

## Questions for Clarification

1. **Batch Size**: Is 50 items per batch reasonable, or should it be higher/lower?

2. **Time Window**: Is 2 hours acceptable, or should it be shorter (1 hour) for faster processing?

3. **Token Limit**: Is 100k tokens appropriate, or should we adjust based on typical content length?

4. **Immediate Threshold**: Should we run AI immediately for ALL obvious flags, or only critical/high?

5. **Error Handling**: How should we handle API failures during batch processing?

6. **Storage**: Where should we store the batch results and flag posts?

Does this flow match your vision? Any adjustments needed before implementation?
