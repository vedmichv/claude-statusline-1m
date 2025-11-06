# Claude Code Statusline with 1M Context Support

Dynamic context window detection for Claude Code statusline that automatically adjusts to your model's context window size.

## Features

- 🎯 **Dynamic Context Detection**: Automatically detects `[1m]`, `[200k]`, etc. suffixes
- 📊 **Accurate Percentages**: Shows correct context usage for 1M and 200K models
- 💰 **Session Metrics**: Cost tracking and duration monitoring
- 🎨 **Color-coded Alerts**: Visual warnings at 50%, 75%, 90%, 95% usage

## Installation

### Via NPX (if published to npm)
```bash
npx claude-statusline-1m
```

### Via GitHub
```bash
npx github:YOUR_USERNAME/claude-statusline-1m
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
- ✅ Claude Sonnet 3.5 with 200K context (default)
- ✅ Any future models with `[XM]` or `[Xk]` suffixes

## Requirements

- Python 3.x
- Claude Code CLI

## License

MIT
