# Claude Code Statusline with 1M Context Support

Dynamic context window detection for Claude Code statusline that automatically adjusts to your model's context window size.

## Features

- 🎯 **Dynamic Context Detection**: Automatically detects `[1m]`, `[200k]`, etc. suffixes
- 📊 **Accurate Percentages**: Shows correct context usage for 1M and 200K models
- 🔢 **Token Count**: Shows absolute usage next to the percentage (e.g. `25% 250K/1M`)
- 💰 **Session Metrics**: Cost tracking and duration monitoring
- 📅 **Daily Spend Across All Sessions**: `$1.20 / $65.43 today` — session cost next to the day's total from every session, via [ccusage](https://github.com/ryoppippi/ccusage) refreshed in the background (never blocks the statusline)
- 🏷️ **Billing Account Badge**: `AWS` / `SUB` / `API` next to the model — shows which account the session bills to, so a stray model pin can't silently route you to the wrong one
- 🧾 **Spend Split by Account**: `$180.00 today ($120.00 AWS + $60.00 SUB)` — appears only when more than one account was actually used that day
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
- ✅ Claude Opus 5 (`[1m]`)
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
| Opus 5 | $5/M | $25/M | None (flat 1M) |
| Sonnet 5 | $2/M intro → $3/M | $10/M intro → $15/M | None (flat 1M) |
| Opus 4.8 / 4.7 / 4.6 | $5/M | $25/M | None (flat 1M) |
| Sonnet 4.6 | $3/M | $15/M | None (flat 1M) |
| Haiku 4.5 | $1/M | $5/M | — (200K window) |
| **Legacy Sonnet 4 / 4.5 on the old 1M beta** | $3/M → **$6/M** | $15/M → **$22.50/M** | **2x input / 1.5x output above 200K** (grandfathered only) |

Sonnet 5 introductory pricing ($2/$10) runs through August 31, 2026. Regional (non-global) Bedrock endpoints cost +10% over the prices above.

⚠️ **Legacy note**: the Sonnet 4/4.5 1M-context beta appears retired — the current Bedrock pricing page no longer lists the >200K tier, and Anthropic docs list Sonnet 4.5 as a 200K model again. The surcharge can only still apply to grandfathered sessions that run Sonnet < 4.6 with a `[1m]` model ID. For those, when you exceed 200K tokens, **ALL tokens** in that request are charged at the premium rate, not just the excess.

The statusline displays a **💸2x** indicator only in exactly that case (Sonnet < 4.6 on a 1M window above 200K tokens) — a conservative alert for grandfathered sessions. Current models (Fable 5, Opus 5, Sonnet 5, Opus 4.x, Sonnet 4.6) have flat pricing across the full 1M window, so no indicator is shown.

## Daily Spend Tracking

The statusline shows two figures: `💰 $1.20 / $65.43 today`.

- **Session cost** (`$1.20`) comes from Claude Code itself, via the `cost.total_cost_usd` field it passes to the statusline.
- **Daily total** (`$65.43`) is every session's spend for the current local day, computed by [ccusage](https://github.com/ryoppippi/ccusage) and colour-coded green under $175, yellow under $350, red at $350+.

Override the thresholds for your own budget:

```bash
export STATUSLINE_DAILY_YELLOW=50
export STATUSLINE_DAILY_RED=100
```

`ccusage` is optional: without it installed, only the session cost is shown.

### How the refresh works

`ccusage` takes 10–18 seconds on a cold run, so it is never invoked inline — the statusline runs on every render and must stay instant. Instead:

1. The statusline reads a small JSON cache (`~/.claude/statusline-daily-cost.json`) — about 1 ms.
2. If that value is missing or older than 60 s, it spawns a **detached** background refresh and renders immediately with whatever it has.
3. The background process runs `ccusage daily --json --no-offline`, then atomically replaces the cache.

A lock file in the system temp directory prevents concurrent statusline invocations (one per render, several across panes) from spawning a pile of refreshes; a lock older than 5 minutes is treated as a dead process and reclaimed.

A `~` after the amount (`$65.43~ today`) means the value is past its TTL and a refresh is in flight. A cache from a previous day is discarded rather than shown stale.

> ⚠️ **Why `--no-offline` matters.** `ccusage statusline` defaults to `--offline` and prices any model missing from its bundled table at **$0, silently**. On 2026-07-25 that reported `$11.46 today` for a day that actually cost ~$65 — Opus 5 and Opus 4.8 both counted as free. This project always passes `--no-offline`, which requires network access to fetch current pricing.

## Billing Account Split (AWS vs Subscription)

The badge next to the model shows which account the current session bills to, and the daily figure is broken down the same way when more than one account was used:

```
[Opus 5 [1M] AWS] 📁 repo 🧠 🟢██▁▁▁▁▁▁ 24% 245K/1M | 💰 $1.20 / $180.00 today ($120.00 AWS + $60.00 SUB)
```

| Badge | Meaning | Detected from |
|-------|---------|---------------|
| `AWS` | Amazon Bedrock **or** Mantle | `CLAUDE_CODE_USE_BEDROCK` / `CLAUDE_CODE_USE_MANTLE` / `CLAUDE_CODE_USE_VERTEX` |
| `SUB` | Claude subscription | none of the above set |
| `API` | Custom endpoint or direct API key | `ANTHROPIC_BASE_URL` / `ANTHROPIC_API_KEY` |
| `?` | Spend ccusage counted that couldn't be attributed locally | — |

Bedrock and Mantle deliberately share one `AWS` bucket: Mantle is an endpoint *within* the AWS path (both toggles set together is the documented Mantle setup) and both land on the same AWS bill, so splitting them would be a distinction without a difference for cost tracking.

**The display adapts to what you actually used.** A day spent entirely on one account shows a bare total with no labels — the split only appears when it carries information. Buckets under 1% of the day's spend are folded away as rounding artefacts rather than shown as providers.

### How attribution works

The transcript files record **no provider information**: `message.model` is normalised to a bare id (`claude-opus-5`), so the `us.anthropic.` / `anthropic.` prefix that would reveal the routing is gone before anything reaches disk. The environment is the only source of truth, and Claude Code reads it once at startup — so the statusline detects the provider from its own environment and appends `<session-uuid> → provider` to `~/.claude/statusline-session-providers.json` (written only when the value changes, so the steady state is a single read).

The background refresh then splits ccusage's per-model costs across providers by each provider's share of that model's tokens for the day. **ccusage stays the sole authority on how much money was spent** — this layer only establishes the proportions, so the buckets always sum to exactly what `ccusage daily` reports and there is no second price table to fall out of date.

Two consequences worth knowing:

- **Sessions that ran before you upgraded show up as `?`** — they have no recorded provider. The bucket shrinks as new sessions accumulate; it is not an error.
- **The split is proportional, not per-request.** Within a single model on a single day it assumes each provider's cost tracks its token volume, which holds when both accounts pay the same rates. If you need exact per-account figures for accounting, use your AWS bill and Anthropic console — this is a monitoring aid, not an invoice.

## Requirements

- Python 3.x
- Claude Code CLI
- [ccusage](https://github.com/ryoppippi/ccusage) *(optional)* — enables the daily spend figure

## License

MIT
