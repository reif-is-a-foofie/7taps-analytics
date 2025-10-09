# 🚀 Frequent Commit Workflow

This project uses several tools to ensure frequent commits and pushes, following best practices for version control.

## Quick Commands

### 1. Quick Commit Script
```bash
./quick-commit.sh
```
- Stages all changes
- Creates timestamped commit message
- Pushes to origin automatically

### 2. Git Alias (Even Faster)
```bash
git qc
```
- Same as quick-commit.sh but shorter
- Adds all changes, commits with timestamp, pushes

### 3. Development Reminder
```bash
./dev-reminder.sh
```
- Shows current git status
- Warns about uncommitted changes
- Reminds about best practices

## Best Practices

### ✅ Do This:
- **Commit every logical change** (even small ones)
- **Push at least once per hour** during active development
- **Use descriptive commit messages** when possible
- **Test before committing** (when practical)

### ❌ Avoid This:
- Waiting hours/days between commits
- Massive commits with multiple unrelated changes
- Committing broken code (use feature branches)
- Forgetting to push changes

## Commit Message Format

### Automatic (Quick Commits)
- `feat: update 3 files - 20251001_070204`
- `fix: update 1 files - 20251001_071230`

### Manual (Descriptive)
- `feat: add user ID hover reveal to data explorer`
- `fix: convert timestamps to Central Time`
- `docs: update commit workflow documentation`

## Workflow Examples

### During Active Development:
```bash
# Make a small change
echo "// TODO: optimize query" >> app/api/analytics.py

# Quick commit
./quick-commit.sh

# Continue coding...
```

### Before Taking a Break:
```bash
# Check status
./dev-reminder.sh

# Quick commit if needed
git qc

# Safe to step away!
```

### End of Day:
```bash
# Final commit
./quick-commit.sh

# Verify everything is pushed
git status
```

## Git Hooks

The project includes a pre-commit hook that:
- ✅ Validates staged changes
- 💡 Reminds about commit best practices
- ⚠️ Warns about empty commits

## Benefits

1. **Safety**: Never lose work due to crashes
2. **Collaboration**: Others can see progress in real-time
3. **Debugging**: Easy to find when bugs were introduced
4. **Rollback**: Simple to revert specific changes
5. **History**: Clear timeline of development decisions

## Integration with Cursor

The `.cursorrules` file has been updated to remind about frequent commits:
> "Commit changes frequently - after each logical change, using conventional commit messages referencing the module. Use `./quick-commit.sh` or `git qc` for rapid commits."

---

**Remember**: Small, frequent commits are better than large, infrequent ones! 🎯
