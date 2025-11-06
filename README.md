# Claude Code Statusline with 1M Context Support

Dynamic context window detection for Claude Code statusline that automatically adjusts to your model's context window size.

## Features

- 🎯 **Dynamic Context Detection**: Automatically detects `[1m]`, `[200k]`, etc. suffixes
- 📊 **Accurate Percentages**: Shows correct context usage for 1M and 200K models
- 💰 **Session Metrics**: Cost tracking and duration monitoring
- 💸 **Premium Pricing Alert**: Shows "💸2x" indicator when exceeding 200K tokens (2x pricing tier)
- 🎨 **Color-coded Alerts**: Visual warnings at 50%, 75%, 90%, 95% usage

## Installation

### Via NPX (if published to npm)
```bash
npx claude-statusline-1m
```

### Via GitHub
```bash
npx github:vedmichv/claude-statusline-1m
```

### Local Testing
```bash
cd ~/Documents/claude-statusline-1m
node install.js
```

## How It Works

The script detects your model's context window from the model ID:

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
