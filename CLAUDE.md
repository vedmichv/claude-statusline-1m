# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code statusline extension that provides real-time context usage monitoring with dynamic 1M context window support. It installs a Python-based statusline script that displays:

- Context usage percentage with visual indicators (progress bar + emoji)
- Token count display (e.g. `245K/1M`) next to the percentage
- Session cost tracking
- Duration monitoring
- Lines changed tracking
- Premium pricing alerts (💸2x indicator when >200K tokens on legacy pre-4.6 Sonnet models only; Fable 5, Sonnet 5, Opus 4.x, and Sonnet 4.6 have flat Bedrock pricing)

The tool automatically detects the model's context window size from suffixes like `[1m]` or `[200k]` in the model ID.

## Architecture

### Four-Part System

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

**Context Window Detection** (`get_context_window_size()` in scripts/context-monitor.py)
- Uses regex pattern `\[(\d+)(m|k)\]` to extract context size from model ID
- Supports both megabyte (`m`) and kilobyte (`k`) suffixes
- Defaults to 200K tokens if no suffix found

**Context Usage Parsing** (`parse_context_from_transcript()` in scripts/context-monitor.py)
- Two methods: parses `usage` tokens from assistant messages, or a `compact_boundary`
  system record (type `system`, subtype `compact_boundary`) — the latter renders
  `✨compacted (was NNNk)` until the next assistant response arrives
- Tail-reads the last 256KB of the transcript, then scans the last 50 lines in reverse
- Calculates percentage based on detected context window size

**Premium Pricing Alert** (`has_long_context_surcharge()` in scripts/context-monitor.py)
- Shows `💸2x` indicator ONLY for legacy Sonnet < 4.6 when tokens > 200K on 1M context
- Fable 5, Sonnet 5, Opus 4.6/4.7/4.8, Sonnet 4.6: **flat Bedrock pricing** — no long-context surcharge
- Legacy Sonnet 4 / 4.5 with 1M context still has 2x surcharge above 200K tokens
- Version comparison is numeric (`(major, minor) < (4, 6)`), so future Sonnet versions stay flat automatically

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

## Pricing Context — Bedrock (Critical for Development)

Verified July 2026 against aws.amazon.com/bedrock/pricing and platform.claude.com/docs/en/about-claude/pricing.

**Claude Fable 5 / Mythos 5** (1M context, flat pricing):
- $10/M input, $50/M output, $1/M cache read
- **No long-context surcharge** — full 1M window at standard rates
- Refusals: Fable 5 safety classifiers return `stop_reason: "refusal"`. Server-side fallback is
  NOT available on Bedrock — clients must opt in via SDK middleware; when a fallback runs, the
  Opus 4.8 attempt bills at Opus rates, and a pre-output refusal is not billed at all

**Claude Sonnet 5** (1M context, flat pricing):
- Intro through 2026-08-31: $2/M input, $10/M output, $0.20/M cache read
- From 2026-09-01: $3/M input, $15/M output, $0.30/M cache read
- **No long-context surcharge** — full 1M window at standard rates
- Note: new tokenizer produces ~30% more tokens for the same text vs Sonnet 4.6

**Claude Opus 4.8 / 4.7 / 4.6** (1M context, flat pricing):
- $5/M input, $25/M output, $0.50/M cache read
- **No long-context surcharge**

**Claude Sonnet 4.6** (1M context, flat pricing):
- $3/M input, $15/M output, $0.30/M cache read — no surcharge

**Claude Haiku 4.5** (200K context):
- $1/M input, $5/M output, $0.10/M cache read

**Legacy: Claude Sonnet 4 / 4.5 on the old 1M beta — the ONLY surcharge path, now grandfathered:**
- ≤ 200K tokens: $3/M input, $15/M output (standard)
- > 200K tokens: $6/M input, $22.50/M output (premium — 2x/1.5x; Bedrock billed these as `*_LCtx` line items)
- **Critical**: When exceeding 200K tokens, ALL tokens in that request are charged at the premium rate.
- As of July 2026 this tier is GONE from the current Bedrock pricing page — the Sonnet 4.5 1M beta
  appears retired (Anthropic docs list 4.5 as 200K again). Whether grandfathered accounts still
  sending the old 1M beta header get surcharged is unverified; the indicator stays as a conservative
  alert for exactly that case.

Regional (non-global) Bedrock endpoints (`us.anthropic.*` etc.) cost +10% over global prices.
GovCloud Opus 4.8: $6/$30, $0.60 cache read.

The `💸2x` indicator logic lives in `has_long_context_surcharge()` (scripts/context-monitor.py): it fires
only for Sonnet models with version < 4.6 when `tokens > 200000` on a 1M window — which can only occur
on a grandfathered 1M-beta session. Fable 5, Sonnet 5, Opus 4.x, and Sonnet 4.6 all have flat pricing —
the indicator is suppressed for them.
