# Versioning Guidelines

## Current Version: 2.2.5

## Version Format: `MAJOR.MINOR.PATCH`

### Rules

1. **PATCH (last digit)** - Default for all changes
   - Bug fixes
   - Small improvements
   - Documentation updates
   - Performance improvements
   - Example: 2.2.0 → 2.2.1 → 2.2.2

2. **MINOR (middle digit)** - Requires approval
   - New features
   - New functionality
   - Backwards-compatible changes
   - **⚠️ ASK BEFORE BUMPING**
   - Example: 2.2.0 → 2.3.0

3. **MAJOR (first digit)** - Requires explicit approval
   - Breaking changes
   - Major refactoring
   - API changes that break compatibility
   - **🚨 ALWAYS ASK BEFORE BUMPING**
   - Example: 2.2.0 → 3.0.0

## Workflow

### For Most Changes (PATCH)
```bash
# Automatic - just bump patch
npm version patch
git push origin main --tags
npm publish
```

### For New Features (MINOR)
```bash
# Ask user first: "Should I bump MINOR version for this feature?"
# If approved:
npm version minor
git push origin main --tags
npm publish
```

### For Breaking Changes (MAJOR)
```bash
# Always ask: "This is a breaking change. Bump MAJOR version?"
# If approved:
npm version major
git push origin main --tags
npm publish
```

## Examples

### PATCH Changes (Auto-bump)
- Fix: typo in statusline
- Improvement: faster keyboard detection
- Docs: update README
- Refactor: code cleanup without behavior change

### MINOR Changes (Ask First)
- New feature: add GPU usage indicator
- New option: configurable colors
- Enhancement: support for new model types

### MAJOR Changes (Always Ask)
- Breaking: change statusline format
- Breaking: rename config options
- Breaking: remove deprecated features

## Current Version History

- **2.2.5** - 5-agent review fixes: dotted model IDs (proxy-style `sonnet-4.6`) no longer trigger false 💸2x, crash-proof error fallback (ASCII stdout, deleted cwd), exact tail-read boundary detection, 50-line transcript lookback, docs corrections (2026-07-03)
- **2.2.4** - Sonnet 5 / Fable 5 / Opus 4.8 support: name shortening, verified Bedrock pricing (no >200K surcharge on new models), token count display, tail-read for large transcripts (2026-07-03)
- **2.2.3** - Bump after Bedrock 4.6 pricing fix (2026-03-21)
- **2.2.2** - Premium 💸2x indicator restricted to Sonnet models only (2025-12-20)
- **2.2.1** - Keyboard layout indicator fix (2025-11-09)
- **2.2.0** - Compact model names + keyboard layout indicator (2025-11-09)
- **2.1.0** - Automatic installation wizard (2025-11-07)
- **2.0.1** - Fix stdin handling (2025-11-07)
- **2.0.0** - Refactor to self-contained NPX approach (2025-11-07)
