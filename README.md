# Claude Code Statusline with 1M Context Support

Dynamic context window detection for Claude Code statusline that automatically adjusts to your model's context window size.

## Features

- 🎯 **Dynamic Context Detection**: Automatically detects `[1m]`, `[200k]`, etc. suffixes
- 📊 **Accurate Percentages**: Shows correct context usage for 1M and 200K models
- 🔢 **Token Count**: Shows absolute usage next to the percentage (e.g. `25% 250K/1M`)
- 💰 **Session Metrics**: Cost tracking and duration monitoring
- 💸 **Premium Pricing Alert**: Shows "💸2x" only for legacy Sonnet 4/4.5 above 200K tokens (current models have flat 1M pricing)
- 🎨 **Color-coded Alerts**: Visual warnings at 50%, 75%, 90%, 95% usage
- 😱 **Keyboard Layout Indicator** (macOS): screaming-face emoji when a non-English layout is active — catches "ааа, не та раскладка!" before you type

## Installation

### 🚀 Automatic Installation (Recommended)

Run the installer - it will set everything up for you:

```bash
npx claude-statusline-1m --install
```

The installer will:
1. Ask where you want to install (global, project, or local)
2. Copy the Python script to the right location
3. Update your settings.json automatically
4. Show you what was installed

**Quick install with defaults** (installs locally without prompts):
```bash
npx claude-statusline-1m --install --yes
```

Then **restart Claude Code** and you're done! 🎉

### 🛠️ Manual Installation (Advanced)

If you prefer to configure manually, add this to your `.claude/settings.json` or `.claude/settings.local.json`:

**For npm version:**
```json
{
  "statusLine": {
    "type": "command",
    "command": "npx -y claude-statusline-1m"
  }
}
```

**For GitHub version:**
```json
{
  "statusLine": {
    "type": "command",
    "command": "npx -y github:vedmichv/claude-statusline-1m"
  }
}
```

Then restart Claude Code.

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

- ✅ Claude Fable 5 / Mythos 5 (`[1m]`)
- ✅ Claude Sonnet 5 (`[1m]`)
- ✅ Claude Opus 4.6 / 4.7 / 4.8 (`[1m]`)
- ✅ Claude Sonnet 4.6 (`[1m]`)
- ✅ Legacy Claude Sonnet 4 / 4.5 with 1M context (`[1m]`) — with 💸2x premium alert
- ✅ Claude Haiku 4.5 (200K)
- ✅ Any future models with `[XM]` or `[Xk]` suffixes

## Pricing Information (Amazon Bedrock, July 2026)

| Model | Input | Output | >200K surcharge |
|-------|-------|--------|-----------------|
| Fable 5 / Mythos 5 | $10/M | $50/M | None (flat 1M) |
| Sonnet 5 | $2/M intro → $3/M | $10/M intro → $15/M | None (flat 1M) |
| Opus 4.8 / 4.7 / 4.6 | $5/M | $25/M | None (flat 1M) |
| Sonnet 4.6 | $3/M | $15/M | None (flat 1M) |
| Haiku 4.5 | $1/M | $5/M | — (200K window) |
| **Legacy Sonnet 4 / 4.5 on the old 1M beta** | $3/M → **$6/M** | $15/M → **$22.50/M** | **2x input / 1.5x output above 200K** (grandfathered only) |

Sonnet 5 introductory pricing ($2/$10) runs through August 31, 2026. Regional (non-global) Bedrock endpoints cost +10% over the prices above.

⚠️ **Legacy note**: the Sonnet 4/4.5 1M-context beta appears retired — the current Bedrock pricing page no longer lists the >200K tier, and Anthropic docs list Sonnet 4.5 as a 200K model again. The surcharge can only still apply to grandfathered sessions that run Sonnet < 4.6 with a `[1m]` model ID. For those, when you exceed 200K tokens, **ALL tokens** in that request are charged at the premium rate, not just the excess.

The statusline displays a **💸2x** indicator only in exactly that case (Sonnet < 4.6 on a 1M window above 200K tokens) — a conservative alert for grandfathered sessions. Current models (Fable 5, Sonnet 5, Opus 4.x, Sonnet 4.6) have flat pricing across the full 1M window, so no indicator is shown.

## Requirements

- Python 3.x
- Claude Code CLI

## License

MIT
