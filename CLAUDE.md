# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code statusline extension that provides real-time context usage monitoring with dynamic 1M context window support. It installs a Python-based statusline script that displays:

- Context usage percentage with visual indicators (progress bar + emoji)
- Session cost tracking
- Duration monitoring
- Lines changed tracking
- Premium pricing alerts (💸2x indicator when >200K tokens)

The tool automatically detects the model's context window size from suffixes like `[1m]` or `[200k]` in the model ID.

## Architecture

### Tri-Part System

1. **cli.js** (Smart Entry Point)
   - Main bin entry executed via `npx claude-statusline-1m`
   - Detects execution mode based on context:
     - If stdin has JSON data (piped from Claude Code) → runs as statusline
     - If `--install` flag present → runs as installer
     - Otherwise → shows help/usage information
   - Routes to appropriate module (statusline.js or install-cli.js)

2. **statusline.js** (Statusline Display)
   - Spawns Python subprocess to run `context-monitor.py`
   - Collects all stdin data from Claude Code using event listeners
   - Passes complete JSON to Python script
   - Pipes stdout from Python back to Claude Code
   - Handles signal termination (SIGTERM, SIGINT)

3. **install-cli.js** (Automatic Installer)
   - Interactive installation wizard
   - Asks user where to install (global, project, or local)
   - Copies Python script to appropriate .claude/scripts/ directory
   - Automatically updates settings.json or settings.local.json
   - Shows installation summary and next steps

4. **context-monitor.py** (Python Statusline Script)
   - Reads JSON input from stdin
   - Parses transcript file to extract context usage
   - Extracts context window size from model ID regex (e.g., `[1m]` → 1,000,000)
   - Generates colored, formatted statusline output to stdout

### Key Technical Details

**Context Window Detection** (scripts/context-monitor.py:12-36)
- Uses regex pattern `\[(\d+)(m|k)\]` to extract context size from model ID
- Supports both megabyte (`m`) and kilobyte (`k`) suffixes
- Defaults to 200K tokens if no suffix found

**Context Usage Parsing** (scripts/context-monitor.py:38-105)
- Two methods: parses `usage` tokens from assistant messages, or system context warnings
- Reads last 15 lines of transcript file in reverse
- Calculates percentage based on detected context window size

**Premium Pricing Alert** (scripts/context-monitor.py:145-148)
- Shows `💸2x` indicator when tokens > 200K on 1M models
- Warns users about tiered pricing (2x input rate above 200K tokens)

## Development Commands

### Installation (Automatic)
```bash
# Install with interactive prompts
npx claude-statusline-1m --install

# Install with defaults (local settings)
npx claude-statusline-1m --install --yes
```

### Manual Configuration
Add to `.claude/settings.local.json` (project) or `~/.claude/settings.local.json` (global):
```json
{
  "statusLine": {
    "type": "command",
    "command": "npx -y claude-statusline-1m"
  }
}
```

### Testing
```bash
# Test the CLI (shows help)
node cli.js --help

# Test statusline mode (stdin piping)
echo '{"model":{"id":"test[1m]","display_name":"Claude"},"workspace":{"current_dir":"/tmp"},"transcript_path":""}' | node cli.js

# Test installer
node cli.js --install --yes

# Test Python script directly
echo '{"model":{"id":"test[1m]","display_name":"Claude"},"workspace":{"current_dir":"/tmp"},"transcript_path":""}' | python3 scripts/context-monitor.py
```

## Important Implementation Notes

### When Modifying cli.js
- The `bin` field in package.json points to `cli.js` (main entry point)
- Script must be executable: `chmod +x cli.js`
- Uses `process.stdin.isTTY` to detect if being piped data from Claude Code
- Routes to statusline.js for statusline mode, install-cli.js for installation

### When Modifying statusline.js
- Script must be executable: `chmod +x statusline.js`
- Always use `path.join()` for cross-platform path handling
- Must collect all stdin data before passing to Python (piping directly doesn't work reliably)
- Uses event-driven stdin collection: `process.stdin.on('data')` and `process.stdin.on('end')`
- Must properly pipe stdout from Python back to Claude Code
- Includes signal handlers (SIGTERM, SIGINT) for clean termination

### When Modifying install-cli.js
- Script must be executable: `chmod +x install-cli.js`
- Uses readline for interactive prompts
- Supports `--yes` flag to skip prompts
- Must handle three installation locations: global (~/.claude), project (.claude), local (.claude/settings.local.json)
- Creates directories as needed with `fs.mkdirSync({ recursive: true })`
- Merges with existing settings.json if present
- Always outputs absolute paths in settings for reliability

### When Modifying context-monitor.py
- Script receives JSON via stdin from Claude Code
- Must output single-line formatted string to stdout
- Use ANSI color codes for formatting: `\033[XXm` ... `\033[0m` (reset)
- Error handling critical: fallback display prevents broken statusline
- Transcript parsing must handle malformed JSON lines gracefully

### Statusline JSON Input Schema
```json
{
  "model": {
    "id": "claude-sonnet-4-5-20250929[1m]",
    "display_name": "Claude Sonnet 4.5"
  },
  "workspace": {
    "current_dir": "/path/to/project",
    "project_dir": "/path/to/project"
  },
  "transcript_path": "/path/to/transcript.jsonl",
  "cost": {
    "total_cost_usd": 0.05,
    "total_duration_ms": 120000,
    "total_lines_added": 50,
    "total_lines_removed": 10
  }
}
```

## Pricing Context (Critical for Development)

Both Anthropic API and AWS Bedrock use tiered pricing for 1M context models:
- ≤ 200K tokens: $3/M input, $15/M output (standard)
- > 200K tokens: $6/M input, $22.50/M output (premium - 2x/1.5x)

**Critical**: When exceeding 200K tokens, ALL tokens in that request are charged at the premium rate.

This is why the `💸2x` indicator is shown when `tokens > 200000` on models with `context_window >= 1000000`.
