# 🤖 Agent Commit Behavior Guidelines

This document defines how AI agents should handle version control during development.

## Core Principle
**Commit and push changes immediately after each logical change, not at the end of large tasks.**

## Automatic Commit Triggers

### ✅ Commit After These Actions:
- **File Creation**: After creating a new file
- **File Modification**: After making logical changes to existing files
- **Bug Fixes**: After fixing any issue
- **Feature Implementation**: After completing a small feature
- **Configuration Changes**: After updating config files
- **Documentation Updates**: After updating docs
- **Test Additions**: After adding or modifying tests

### ⚠️ Do NOT Wait For:
- Completing entire modules
- Finishing all tests
- Perfect code quality
- Large refactoring completion

## Commit Commands for Agents

### Primary Command (Recommended):
```bash
./quick-commit.sh
```
- Stages all changes
- Creates timestamped commit message
- Pushes automatically
- Shows helpful status

### Alternative (Faster):
```bash
git qc
```
- Same functionality, shorter command
- Perfect for rapid iteration

## Commit Message Strategy

### Automatic Messages (Quick Commits):
- `feat: update 3 files - 20251001_070204`
- `fix: update 1 files - 20251001_071230`

### Descriptive Messages (When Important):
- `feat: add user ID hover reveal to data explorer`
- `fix: convert timestamps to Central Time`
- `docs: update commit workflow documentation`

## Workflow Examples for Agents

### Example 1: Adding a New Feature
```bash
# 1. Create new file
touch app/api/new_feature.py

# 2. Write basic implementation
echo "def new_function(): pass" > app/api/new_feature.py

# 3. COMMIT IMMEDIATELY
./quick-commit.sh

# 4. Continue development...
# 5. Make more changes...
# 6. COMMIT AGAIN
git qc
```

### Example 2: Fixing Multiple Files
```bash
# 1. Fix first file
# Edit app/api/file1.py
# COMMIT
./quick-commit.sh

# 2. Fix second file  
# Edit app/api/file2.py
# COMMIT
git qc

# 3. Fix third file
# Edit templates/file3.html
# COMMIT
./quick-commit.sh
```

### Example 3: Large Refactoring
```bash
# 1. Start refactoring
# Make changes to core module
# COMMIT (even if incomplete)
./quick-commit.sh

# 2. Continue refactoring
# Make more changes
# COMMIT
git qc

# 3. Finish refactoring
# Final changes
# COMMIT
./quick-commit.sh
```

## Error Handling

### If Commit Fails:
1. Check git status: `git status`
2. Resolve conflicts if any
3. Retry commit: `./quick-commit.sh`

### If Push Fails:
1. Pull latest changes: `git pull`
2. Resolve conflicts if any
3. Retry: `./quick-commit.sh`

## Benefits for Agents

1. **No Lost Work**: Changes are saved immediately
2. **Real-time Progress**: User can see incremental progress
3. **Easy Rollback**: Can revert specific changes
4. **Collaboration**: Multiple agents can work simultaneously
5. **Debugging**: Easy to find when issues were introduced

## Integration Points

### With Cursor Rules:
- `.cursorrules` already updated with commit frequency reminder
- Agents should follow this guidance automatically

### With Development Workflow:
- Use `./dev-reminder.sh` to check status
- Use `./quick-commit.sh` for commits
- Use `git qc` for fastest commits

## Agent Memory Integration

Agents should remember:
- **Commit frequently** - after each logical change
- **Use quick commands** - `./quick-commit.sh` or `git qc`
- **Don't wait** - for perfect code or complete features
- **Push immediately** - to avoid losing work

---

**Remember**: Small, frequent commits are better than large, infrequent ones! 🎯
