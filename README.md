# Claude Code Statusline with 1M Context Support

Dynamic context window detection for Claude Code statusline that automatically adjusts to your model's context window size.

## Features

- 🎯 **Dynamic Context Detection**: Automatically detects `[1m]`, `[200k]`, etc. suffixes
- 📊 **Accurate Percentages**: Shows correct context usage for 1M and 200K models
- 💰 **Session Metrics**: Cost tracking and duration monitoring
- 💸 **Premium Pricing Alert**: Shows "💸2x" indicator when exceeding 200K tokens (2x pricing tier)
- 🎨 **Color-coded Alerts**: Visual warnings at 50%, 75%, 90%, 95% usage

## Installation

### Step 1: Add Configuration

Add this to your `.claude/settings.local.json`:

**Project-level** (recommended - only for current project):
```bash
# Create/edit .claude/settings.local.json in your project directory
```

**Global** (all projects):
```bash
# Create/edit ~/.claude/settings.local.json
```

**Configuration:**
```json
{
  "statusLine": {
    "type": "command",
    "command": "npx -y claude-statusline-1m"
  }
}
```

Or use the GitHub version directly:
```json
{
  "statusLine": {
    "type": "command",
    "command": "npx -y github:vedmichv/claude-statusline-1m"
  }
}
```

### Step 2: Restart Claude Code

**That's it!** Your statusline will now show real-time context usage.

### How It Works

- 🚀 NPX downloads and caches the package automatically
- ⚡ Claude Code runs it on every session
- 📦 No installation script needed - runs directly from cache
- 🌍 Works at project OR global level
- 🔄 Always uses the cached version for fast startup

### Quick Test

Test the statusline before configuring:

```bash
# Test with npm package
echo '{"model":{"id":"test[1m]","display_name":"Claude"},"workspace":{"current_dir":"/tmp"},"transcript_path":""}' | npx -y claude-statusline-1m

# Test with GitHub version
echo '{"model":{"id":"test[1m]","display_name":"Claude"},"workspace":{"current_dir":"/tmp"},"transcript_path":""}' | npx -y github:vedmichv/claude-statusline-1m
```

Expected output: `[Claude] 📁 tmp 🧠 🔵 ???`

## Context Window Detection

The script automatically detects your model's context window from the model ID:

- `model[1m]` → 1,000,000 tokens
- `model[200k]` → 200,000 tokens
- No suffix → 200,000 tokens (default)

## Supported Models

- ✅ Claude Sonnet 4.5 with 1M context (`[1m]`)
- ✅ Claude Sonnet 4 with 1M context (`[1m]`)
- ✅ Any future models with `[XM]` or `[Xk]` suffixes

## Pricing Information

### Both Anthropic API & AWS Bedrock

Claude Sonnet 4/4.5 with 1M context has **tiered pricing**:

| Token Range | Input | Output | Notes |
|-------------|-------|--------|-------|
| ≤ 200K tokens | $3/M | $15/M | Standard rate |
| > 200K tokens | $6/M | $22.50/M | Premium rate (2x input, 1.5x output) |

⚠️ **Critical**: When you exceed 200K tokens, **ALL tokens** in that request are charged at the premium rate, not just the excess.

The statusline displays a **💸2x** indicator when you cross into premium pricing territory (>200K tokens).

## Requirements

- Python 3.x
- Claude Code CLI

## License

MIT
