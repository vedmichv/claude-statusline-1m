#!/usr/bin/env python3
"""
Claude Code Context Monitor
Real-time context usage monitoring with visual indicators and session analytics
"""

import json
import sys
import os
import re
import subprocess
import tempfile
import time

# Daily-cost cache written by a detached `ccusage daily` refresh (see
# read_daily_cost / spawn_daily_refresh). Kept out of ~/.claude/ proper so a
# stale/corrupt cache can never confuse Claude Code's own config loading.
DAILY_CACHE_PATH = os.path.join(
    os.path.expanduser("~"), ".claude", "statusline-daily-cost.json"
)
# session-uuid -> provider, appended to by every statusline render (see
# record_session_provider). The aggregator uses it to bucket each transcript.
PROVIDER_MAP_PATH = os.path.join(
    os.path.expanduser("~"), ".claude", "statusline-session-providers.json"
)
DAILY_CACHE_TTL = 60      # seconds before the value is considered stale
DAILY_REFRESH_LOCK_TTL = 300  # a refresh that hasn't finished in 5min is dead

def _env_float(name, default):
    """Read a numeric env override, falling back on anything unparseable.

    Guarded because this runs at import time: an unparseable value must not
    raise there, or it takes down the statusline before main()'s error handler
    is even reachable.
    """
    try:
        return float(os.environ[name])
    except (KeyError, TypeError, ValueError):
        return float(default)


# Daily-spend colour thresholds in USD. Override with STATUSLINE_DAILY_RED /
# STATUSLINE_DAILY_YELLOW to suit your own budget.
DAILY_RED = _env_float('STATUSLINE_DAILY_RED', 350)
DAILY_YELLOW = _env_float('STATUSLINE_DAILY_YELLOW', 175)

# Short labels for the two billing buckets. Mantle and Bedrock are both AWS
# spend on the same account, so they deliberately share one bucket.
PROVIDER_LABELS = {'aws': 'AWS', 'sub': 'SUB', 'api': 'API', 'unknown': '?'}

def shorten_model_name(model_name, model_id):
    """Shorten model name to be more compact.

    Examples:
        'Claude Sonnet 4.5' + 'xxx[1m]' -> 'Sonnet 4.5 [1M]'
        'Claude Opus 3.5' + 'xxx[200k]' -> 'Opus 3.5 [200K]'
        'global.anthropic.claude-sonnet-4-5-xxx[1m]' -> 'Sonnet 4.5 [1M]'
    """
    # Extract model type (Fable/Mythos first: 'fable' could coexist with legacy names)
    model_type = None
    for t in ['Fable', 'Mythos', 'Sonnet', 'Opus', 'Haiku']:
        if t.lower() in model_name.lower() or t.lower() in model_id.lower():
            model_type = t
            break

    if not model_type:
        # If can't detect, use display name but limit length
        return model_name[:20] if len(model_name) > 20 else model_name

    # Extract version number: two-part ("4.5") or single-digit ("5" in Sonnet 5 / Fable 5)
    # Try model_name first, then model_id
    version = ""
    version_match = re.search(r'(\d+)[.-](\d{1,2})(?!\d)', model_name)
    if not version_match:
        version_match = re.search(r'(\d+)[.-](\d{1,2})(?!\d)', model_id)
    if version_match:
        version = f"{version_match.group(1)}.{version_match.group(2)}"
    else:
        # \d{1,2} keeps dates out: 'claude-3-opus-20240229' must not render
        # as 'Opus 20240229'. re.escape future-proofs the type interpolation.
        mt = re.escape(model_type.lower())
        single_match = re.search(rf'{mt}[ -](\d{{1,2}})\b', model_name.lower()) \
            or re.search(rf'{mt}-(\d{{1,2}})\b', model_id.lower())
        if single_match:
            version = single_match.group(1)

    # Extract context window from model_id
    context_suffix = ""
    context_match = re.search(r'\[(\d+)(m|k)\]', model_id.lower())
    if context_match:
        num = context_match.group(1)
        unit = context_match.group(2).upper()
        context_suffix = f" [{num}{unit}]"

    # Build shortened name
    result = f"{model_type}"
    if version:
        result += f" {version}"
    result += context_suffix

    return result

def get_keyboard_layout():
    """Get current keyboard layout on macOS.

    Returns:
        str: Emoji indicator only for non-English layouts (empty string for EN).
             Non-English: '😱' (screaming face) - "ааа, не та раскладка!"
    """
    if sys.platform != 'darwin':
        return ""  # 'defaults' is macOS-only; skip the subprocess spawn elsewhere

    try:
        # Method: Read keyboard layout from system preferences
        result = subprocess.run(
            ['defaults', 'read', 'com.apple.HIToolbox', 'AppleCurrentKeyboardLayoutInputSourceID'],
            capture_output=True,
            text=True,
            timeout=0.5
        )

        if result.returncode == 0:
            layout = result.stdout.strip().lower()
            # Check for non-English layouts
            # Examples: com.apple.keylayout.Russian, com.apple.keylayout.RussianWin, com.apple.keylayout.ABC

            # Russian/Cyrillic layouts - check FIRST (before US check!)
            if 'russian' in layout or '.ru' in layout or 'cyrillic' in layout:
                return "😱"  # Screaming face - "ааа, русская!"

            # English layouts - no indicator
            if '.abc' in layout or '.us' in layout or 'english' in layout or layout.endswith('abc'):
                return ""  # English - no indicator to save space

            # Any other keyboard layout (non-English)
            if 'keylayout' in layout:
                return "😱"  # Other non-English layout

            return ""

    except Exception:
        pass

    # Default to empty (English is most common)
    return ""

def get_context_window_size(model_id):
    """Extract context window size from model ID.

    Looks for [XM] or [Xk] suffix in model ID to determine context window.
    Examples:
        - model[1m] = 1,000,000 tokens
        - model[200k] = 200,000 tokens
        - Default = 200,000 tokens
    """
    if not model_id:
        return 200000

    # Look for [1m], [200k], etc. in model ID
    match = re.search(r'\[(\d+)(m|k)\]', model_id.lower())
    if match:
        number = int(match.group(1))
        unit = match.group(2)

        size = number * 1000000 if unit == 'm' else number * 1000
        if size > 0:  # "[0m]" would cause ZeroDivisionError downstream
            return size

    # Default to 200k for older models
    return 200000

def parse_context_from_transcript(transcript_path, context_window=200000):
    """Parse context usage from transcript file."""
    if not transcript_path or not os.path.exists(transcript_path):
        return None

    try:
        # Tail-read: transcripts grow to hundreds of MB on 1M-context sessions,
        # and the statusline re-runs constantly — never load the whole file.
        with open(transcript_path, 'rb') as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            start = max(0, size - 262144)  # last 256KB is plenty for 50 lines
            drop_first = False
            if start > 0:
                # Peek at the byte before the window: if it isn't a newline,
                # the window starts mid-record and the first line is partial
                f.seek(start - 1)
                drop_first = f.read(1) != b'\n'
            else:
                f.seek(0)  # pointer is at EOF after tell(); rewind for small files
            tail = f.read().decode('utf-8', errors='replace')

        # split('\n'), not splitlines(): a raw U+2028/NEL inside a JSON string
        # must not split a record; strip() below absorbs any \r
        lines = tail.split('\n')
        if drop_first and lines:
            lines = lines[1:]

        # Scan the last 50 lines: hooks, tool results, and system rows can
        # interleave 15+ non-assistant records after the last usage row
        recent_lines = lines[-50:] if len(lines) > 50 else lines

        for line in reversed(recent_lines):
            try:
                data = json.loads(line.strip())

                # Method 1: Parse usage tokens from assistant messages
                if data.get('type') == 'assistant':
                    message = data.get('message', {})
                    usage = message.get('usage', {})

                    if usage:
                        input_tokens = usage.get('input_tokens', 0)
                        cache_read = usage.get('cache_read_input_tokens', 0)
                        cache_creation = usage.get('cache_creation_input_tokens', 0)

                        # Cache reads/writes ARE input context — excluding them would
                        # undercount massively (typical row: input=2, cache_read=266710)
                        total_tokens = input_tokens + cache_read + cache_creation
                        # Deliberate: skip zero-usage rows (streaming placeholders
                        # would otherwise reset the display to 0%)
                        if total_tokens > 0:
                            percent_used = min(100, (total_tokens / context_window) * 100)
                            return {
                                'percent': percent_used,
                                'tokens': total_tokens,
                                'context_window': context_window,
                                'method': 'usage'
                            }
                
                # Method 2: compaction boundary. Reached only when no assistant
                # usage row follows it (reverse scan) — the context was just
                # compacted, so older usage rows are stale; show that instead
                # of a misleading pre-compact percentage.
                elif data.get('type') == 'system' and data.get('subtype') == 'compact_boundary':
                    meta = data.get('compactMetadata') or {}
                    return {
                        'percent': 0,
                        'tokens': 0,
                        'context_window': context_window,
                        'pre_tokens': meta.get('preTokens', 0),
                        'warning': 'compacted',
                        'method': 'system'
                    }
            
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
        
        return None
        
    except OSError:  # missing file, permissions, path is a directory, ...
        return None

def has_long_context_surcharge(model_id):
    """Whether this model bills >200K-token requests at a premium rate.

    Verified July 2026 (Bedrock + Anthropic API pricing pages):
    - Fable 5 / Mythos 5, Opus 4.8/4.7/4.6, Sonnet 5, Sonnet 4.6:
      flat pricing across the full 1M window — NO surcharge.
    - Legacy Sonnet 4 / 4.5 with [1m] context: 2x input / 1.5x output
      above 200K tokens (Bedrock bills these as LCtx line items).
    """
    mid = model_id.lower()
    if 'sonnet' not in mid:
        return False

    # Parse "sonnet-4-5", "sonnet-4.6" (proxy-style dotted), "sonnet-4-20250514"
    # (-> 4.0), "sonnet-5". The \d{1,2} minor cap keeps date fragments out.
    m = re.search(r'sonnet[-.](\d+)(?:[.-](\d{1,2}))?(?=$|[^\d])', mid)
    if not m:
        return False

    major = int(m.group(1))
    # "claude-3-5-sonnet-20241022" puts digits BEFORE the word; the regex then
    # grabs the date as major. Any major > 100 is a date, and 3.x never had a
    # 1M window anyway — no surcharge.
    if major > 100:
        return False
    minor = int(m.group(2)) if m.group(2) else 0
    return (major, minor) < (4, 6)

def format_token_count(tokens):
    """Compact token count: 950 -> '950', 245000 -> '245K', 1200000 -> '1.2M'."""
    if tokens >= 1000000:
        millions = tokens / 1000000
        return f"{millions:.0f}M" if millions == int(millions) else f"{millions:.1f}M"
    if tokens >= 1000:
        k = round(tokens / 1000)
        if k >= 1000:  # 999,500+ rounds to 1000K — promote to M
            return "1M"
        return f"{k}K"
    return str(tokens)

def get_context_display(context_info, model_id=""):
    """Generate context display with visual indicators."""
    if not context_info:
        return "🔵 ???"

    percent = context_info.get('percent', 0)
    tokens = context_info.get('tokens', 0)
    context_window = context_info.get('context_window', 200000)
    warning = context_info.get('warning')

    # Color and icon based on usage level
    if percent >= 95:
        icon, color = "🚨", "\033[31;1m"  # Blinking red
        alert = "CRIT"
    elif percent >= 90:
        icon, color = "🔴", "\033[31m"    # Red
        alert = "HIGH"
    elif percent >= 75:
        icon, color = "🟠", "\033[91m"   # Light red
        alert = ""
    elif percent >= 50:
        icon, color = "🟡", "\033[33m"   # Yellow
        alert = ""
    else:
        icon, color = "🟢", "\033[32m"   # Green
        alert = ""

    # Create progress bar
    segments = 8
    filled = int((percent / 100) * segments)
    bar = "█" * filled + "▁" * (segments - filled)

    # Just-compacted marker: fresh window, show what it shrank from
    if warning == 'compacted':
        pre = context_info.get('pre_tokens', 0)
        pre_str = f" (was {format_token_count(pre)})" if pre else ""
        alert = f"✨compacted{pre_str}"

    # Premium pricing warning: only legacy Sonnet (< 4.6) bills >200K at 2x on Bedrock
    premium_pricing = ""
    if context_window >= 1000000 and tokens > 200000 and has_long_context_surcharge(model_id):
        premium_pricing = " \033[33m💸2x\033[0m"

    # Token count next to percentage, e.g. "245K/1M" — percent alone hides scale on 1M models
    tokens_str = ""
    if tokens > 0:
        window_str = format_token_count(context_window)
        tokens_str = f" \033[90m{format_token_count(tokens)}/{window_str}\033[0m"

    reset = "\033[0m"
    alert_str = f" {alert}" if alert else ""

    return f"{icon}{color}{bar}{reset} {percent:.0f}%{tokens_str}{alert_str}{premium_pricing}"

def get_directory_display(workspace_data):
    """Get directory display name."""
    current_dir = workspace_data.get('current_dir', '')
    project_dir = workspace_data.get('project_dir', '')
    
    if current_dir and project_dir:
        if current_dir.startswith(project_dir):
            rel_path = current_dir[len(project_dir):].lstrip('/')
            return rel_path or os.path.basename(project_dir)
        else:
            return os.path.basename(current_dir)
    elif project_dir:
        return os.path.basename(project_dir)
    elif current_dir:
        return os.path.basename(current_dir)
    else:
        return "unknown"

def detect_provider():
    """Which account this session bills to, from the env Claude Code was started with.

    The transcript itself carries NO provider information — `message.model` is
    normalised to a bare id (`claude-opus-5`), so the `us.anthropic.` /
    `anthropic.` prefix that would reveal the routing is gone by the time
    anything is written to disk. The environment is the only source of truth,
    and Claude Code reads it once at startup, so it is stable for the session.

    'aws' covers both Bedrock and Mantle: Mantle is an endpoint *within* the
    AWS path (both toggles set together is the documented Mantle setup), and
    both land on the same AWS bill — so splitting them would be a distinction
    without a difference for cost tracking.
    """
    if os.environ.get('CLAUDE_CODE_USE_BEDROCK') or os.environ.get('CLAUDE_CODE_USE_MANTLE'):
        return 'aws'
    if os.environ.get('CLAUDE_CODE_USE_VERTEX'):
        return 'aws'  # another cloud bill rather than subscription usage
    if os.environ.get('ANTHROPIC_BASE_URL') or os.environ.get('ANTHROPIC_API_KEY'):
        return 'api'
    return 'sub'


def session_id_from_transcript(transcript_path):
    """Transcript filenames are '<session-uuid>.jsonl' — that uuid is the key."""
    if not transcript_path:
        return None
    name = os.path.basename(transcript_path)
    return name[:-6] if name.endswith('.jsonl') else None


def record_session_provider(transcript_path, provider):
    """Note this session's provider so the aggregator can bucket its spend.

    Writes only when the value would change, so the steady state is a single
    read — the statusline runs on every render and must not churn the disk.
    """
    session_id = session_id_from_transcript(transcript_path)
    if not session_id:
        return

    try:
        with open(PROVIDER_MAP_PATH) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {}
    except (OSError, json.JSONDecodeError):
        data = {}

    if data.get(session_id) == provider:
        return  # already recorded — the common case

    data[session_id] = provider

    # Bound the file: sessions are never revisited once their day is over, and
    # an unbounded map would grow forever across thousands of sessions.
    if len(data) > 2000:
        data = dict(list(data.items())[-2000:])

    try:
        os.makedirs(os.path.dirname(PROVIDER_MAP_PATH), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(PROVIDER_MAP_PATH))
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f)
            os.replace(tmp, PROVIDER_MAP_PATH)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
    except OSError:
        pass  # a statusline must never fail because it couldn't write a hint file


def read_daily_cost():
    """Read the cached daily spend written by the background refresh.

    Returns (buckets, is_stale) where buckets maps provider -> cost_usd, or
    (None, False) when no usable cache exists. Never spawns anything and never
    blocks — the statusline runs on every render.
    """
    try:
        with open(DAILY_CACHE_PATH) as f:
            cache = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None, False

    # A cache from a previous day is useless, not merely stale: "today" rolled over.
    if cache.get('date') != time.strftime('%Y-%m-%d'):
        return None, False

    age = time.time() - cache.get('updated_at', 0)
    is_stale = age > DAILY_CACHE_TTL

    buckets = cache.get('buckets')
    if isinstance(buckets, dict):
        clean = {k: float(v) for k, v in buckets.items()
                 if isinstance(v, (int, float)) and v > 0}
        return (clean or None), is_stale

    # A v2.3.0 cache had a single 'cost_usd' with no split. Present it as one
    # unattributed bucket so an upgrade doesn't blank the display for a minute.
    cost = cache.get('cost_usd')
    if isinstance(cost, (int, float)):
        return {'all': float(cost)}, is_stale

    return None, False


def spawn_daily_refresh():
    """Fire off a detached `ccusage daily` and write its total to the cache.

    ccusage takes 10-18s cold, so it can never run inline. A lock file keeps
    concurrent statusline invocations (one per render, several panes) from
    stampeding a dozen node processes.

    --no-offline is REQUIRED: ccusage's bundled offline pricing table silently
    prices models it doesn't know at $0. On 2026-07-25 that under-reported a
    $65 day as $11.46 because Opus 5 and Opus 4.8 were both missing from it.
    """
    lock_path = os.path.join(tempfile.gettempdir(), 'statusline-daily-refresh.lock')

    # O_EXCL is the lock: whoever creates the file owns the refresh.
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        os.close(fd)
    except FileExistsError:
        try:
            if time.time() - os.path.getmtime(lock_path) < DAILY_REFRESH_LOCK_TTL:
                return  # a refresh is genuinely in flight
            os.unlink(lock_path)  # previous refresh died; reclaim and retry next render
        except OSError:
            pass
        return
    except OSError:
        return

    # The child runs `this same file --refresh-daily`, so there is no nested
    # shell quoting to get wrong and no second copy of the parsing logic.
    try:
        subprocess.Popen(
            [sys.executable or 'python3', os.path.abspath(__file__),
             '--refresh-daily', lock_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,  # survives the statusline process exiting
        )
    except Exception:
        try:
            os.unlink(lock_path)  # never leave a lock behind for a process that never ran
        except OSError:
            pass


# Relative token prices, as multiples of the input-token price. These ratios are
# uniform across the whole Claude lineup (output 5x, cache write 1.25x, cache
# read 0.1x), which is what makes the provider split below price-table-free:
# only the ratios matter, and they don't change when a new model ships.
TOKEN_WEIGHTS = (
    ('input_tokens', 1.0),
    ('output_tokens', 5.0),
    ('cache_creation_input_tokens', 1.25),
    ('cache_read_input_tokens', 0.1),
)


def _weighted_tokens(usage):
    """Cost of one usage row in 'input-token equivalents' (see TOKEN_WEIGHTS)."""
    return sum(usage.get(field, 0) * mult for field, mult in TOKEN_WEIGHTS)


def scan_weighted_tokens_by_provider(providers):
    """Weighted today-tokens per (model, provider), read straight from transcripts.

    Returns {model: {provider: weighted_tokens}}. Deliberately computes no money:
    ccusage owns the absolute figures, this only establishes the proportions to
    divide them by — so there is no price table here to fall out of date.
    """
    import glob

    today = time.strftime('%Y-%m-%d')
    pattern = os.path.join(os.path.expanduser('~'), '.claude', 'projects',
                           '**', '*.jsonl')
    cutoff = time.time() - 36 * 3600  # a today-row can't live in an older file

    result = {}
    seen = set()
    for path in glob.iglob(pattern, recursive=True):
        try:
            if os.path.getmtime(path) < cutoff:
                continue
            fh = open(path, 'rb')
        except OSError:
            continue

        # Subagent transcripts live under <session>/subagents/ and bill to the
        # parent session, so inherit the provider from the enclosing session dir.
        provider = providers.get(session_id_from_transcript(path) or '')
        if provider is None:
            parts = path.split(os.sep)
            for part in reversed(parts[:-1]):
                if part in providers:
                    provider = providers[part]
                    break
        provider = provider or 'unknown'

        with fh:
            for raw in fh:
                if b'"usage"' not in raw:
                    continue
                try:
                    entry = json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    continue
                if entry.get('type') != 'assistant':
                    continue
                stamp = entry.get('timestamp')
                if not stamp:
                    continue
                try:
                    local = _parse_iso_local(stamp)
                except Exception:
                    continue
                if local != today:
                    continue

                message = entry.get('message') or {}
                # Claude Code writes several rows per API response; the
                # (id, requestId) pair identifies the response, not the row.
                key = (message.get('id'), entry.get('requestId'))
                if key[0]:
                    if key in seen:
                        continue
                    seen.add(key)

                model = message.get('model') or ''
                if not model or model == '<synthetic>':
                    continue
                weighted = _weighted_tokens(message.get('usage') or {})
                if weighted <= 0:
                    continue
                result.setdefault(model, {}).setdefault(provider, 0.0)
                result[model][provider] += weighted

    return result


def _parse_iso_local(stamp):
    """ISO-8601 UTC stamp -> local 'YYYY-MM-DD'."""
    from datetime import datetime
    return datetime.fromisoformat(
        stamp.replace('Z', '+00:00')
    ).astimezone().strftime('%Y-%m-%d')


def read_provider_map():
    try:
        with open(PROVIDER_MAP_PATH) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def refresh_daily_cache(lock_path=None):
    """Run ccusage, split its total by provider, and write the cache. Runs detached.

    Entry point for `context-monitor.py --refresh-daily`; never called inline.

    ccusage stays the single authority on how much money was spent — the
    per-provider split is applied on top by weighting each model's cost by the
    tokens each provider contributed, so the buckets always add up to exactly
    what `ccusage daily` reports.
    """
    try:
        today = time.strftime('%Y%m%d')
        try:
            proc = subprocess.run(
                ['ccusage', 'daily', '--json', '--no-offline', '--breakdown',
                 '--since', today, '--until', today],
                capture_output=True, text=True, timeout=120,
            )
        except FileNotFoundError:
            return  # ccusage not installed — the daily figure just stays hidden
        except subprocess.TimeoutExpired:
            return

        if proc.returncode != 0:
            return

        rows = (json.loads(proc.stdout) or {}).get('daily') or []
        if not rows:
            return

        # Authoritative cost per model, from ccusage.
        model_costs = {}
        for row in rows:
            for item in row.get('modelBreakdowns') or []:
                name = item.get('modelName')
                if name:
                    model_costs[name] = model_costs.get(name, 0.0) + item.get('cost', 0)
        total = sum(r.get('totalCost', 0) for r in rows)

        # Divide each model's cost among providers by their token share.
        shares = scan_weighted_tokens_by_provider(read_provider_map())
        buckets = {}
        attributed = 0.0
        for model, cost in model_costs.items():
            by_provider = shares.get(model)
            if not by_provider:
                continue  # no local evidence for this model; handled below
            weighted_total = sum(by_provider.values())
            if weighted_total <= 0:
                continue
            for provider, weighted in by_provider.items():
                buckets[provider] = buckets.get(provider, 0.0) + cost * weighted / weighted_total
            attributed += cost

        # Anything ccusage counted that the local scan couldn't place (another
        # machine's transcripts, a pruned file) stays visible rather than vanishing.
        remainder = total - attributed
        if remainder > 0.005:
            buckets['unknown'] = buckets.get('unknown', 0.0) + remainder

        payload = {
            'date': time.strftime('%Y-%m-%d'),
            'cost_usd': total,
            'buckets': buckets or {'unknown': total},
            'updated_at': time.time(),
        }
        # Atomic replace: a statusline reading mid-write must never see half a file.
        os.makedirs(os.path.dirname(DAILY_CACHE_PATH), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(DAILY_CACHE_PATH))
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(payload, f)
            os.replace(tmp, DAILY_CACHE_PATH)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
    except Exception:
        pass  # a failed refresh must stay silent; the statusline just shows no daily
    finally:
        if lock_path:
            try:
                os.unlink(lock_path)
            except OSError:
                pass


def format_cost(cost_usd):
    """Compact cost: 0.004 -> '0¢', 1.2 -> '$1.20', 65.434 -> '$65.43'."""
    if cost_usd < 0.01:
        return f"{cost_usd*100:.0f}¢"
    return f"${cost_usd:.2f}"


def daily_cost_color(cost):
    """Colour for a daily amount. Thresholds are budget-scaled, not session-scaled."""
    if cost >= DAILY_RED:
        return "\033[31m"    # Red
    if cost >= DAILY_YELLOW:
        return "\033[33m"    # Yellow
    return "\033[32m"        # Green


def get_daily_cost_display():
    """Render today's spend, split by billing account, refreshing in the background.

    Only buckets that actually spent money are shown: a day with no subscription
    usage shows no SUB figure, and a single-provider day shows one bare total with
    no label at all — the split is only worth the width when there is a split.
    """
    buckets, is_stale = read_daily_cost()

    # Refresh whenever the value is missing or past its TTL. Cheap: lock-guarded.
    if buckets is None or is_stale:
        spawn_daily_refresh()

    if not buckets:
        return ""  # first run — nothing to show until the refresh lands

    total = sum(buckets.values())
    # '~' marks a value served past its TTL while the refresh is still running.
    suffix = "~" if is_stale else ""
    total_str = f"{daily_cost_color(total)}{format_cost(total)}{suffix} today\033[0m"

    # Drop rounding dust so a stray fraction of a cent can't invent a bucket, and
    # ignore slivers below 1% — a rounding artefact of the split isn't a provider
    # worth spending statusline width on.
    floor = max(0.01, total * 0.01)
    shown = {k: v for k, v in buckets.items() if v >= floor}

    # One bucket (or none survived): the label adds nothing over the bare total.
    if len(shown) <= 1:
        return total_str

    # Total first, then the split in parentheses — the number you actually watch
    # stays in the same place regardless of how many providers are in play.
    parts = []
    for provider, cost in sorted(shown.items(), key=lambda kv: -kv[1]):
        label = PROVIDER_LABELS.get(provider, provider.upper())
        parts.append(f"{format_cost(cost)} {label}")

    return f"{total_str} \033[90m({' + '.join(parts)})\033[0m"


def get_session_metrics(cost_data):
    """Get session metrics display."""
    if not cost_data:
        cost_data = {}

    metrics = []

    # Cost: session (from Claude Code) + all-sessions daily total (from ccusage)
    cost_usd = cost_data.get('total_cost_usd', 0)
    daily_display = get_daily_cost_display()

    if cost_usd > 0:
        if cost_usd >= 0.10:
            cost_color = "\033[31m"  # Red for expensive
        elif cost_usd >= 0.05:
            cost_color = "\033[33m"  # Yellow for moderate
        else:
            cost_color = "\033[32m"  # Green for cheap

        cost_str = format_cost(cost_usd)
        session_part = f"{cost_color}{cost_str}\033[0m"
        if daily_display:
            metrics.append(f"💰 {session_part} \033[90m/\033[0m {daily_display}")
        else:
            metrics.append(f"💰 {session_part}")
    elif daily_display:
        # No session cost yet (fresh session) — the daily total is still useful
        metrics.append(f"💰 {daily_display}")

    # Duration
    duration_ms = cost_data.get('total_duration_ms', 0)
    if duration_ms > 0:
        minutes = duration_ms / 60000
        if minutes >= 30:
            duration_color = "\033[33m"  # Yellow for long sessions
        else:
            duration_color = "\033[32m"  # Green
        
        if minutes < 1:
            duration_str = f"{duration_ms//1000}s"
        else:
            duration_str = f"{minutes:.0f}m"
        
        metrics.append(f"{duration_color}⏱ {duration_str}\033[0m")
    
    # Lines changed
    lines_added = cost_data.get('total_lines_added', 0)
    lines_removed = cost_data.get('total_lines_removed', 0)
    if lines_added > 0 or lines_removed > 0:
        net_lines = lines_added - lines_removed
        
        if net_lines > 0:
            lines_color = "\033[32m"  # Green for additions
        elif net_lines < 0:
            lines_color = "\033[31m"  # Red for deletions
        else:
            lines_color = "\033[33m"  # Yellow for neutral
        
        sign = "+" if net_lines >= 0 else ""
        metrics.append(f"{lines_color}📝 {sign}{net_lines}\033[0m")
    
    return f" \033[90m|\033[0m {' '.join(metrics)}" if metrics else ""

def main():
    # Background refresh mode: no stdin, no statusline output. Handled before
    # anything else so a detached child never tries to read Claude Code's JSON.
    if '--refresh-daily' in sys.argv:
        idx = sys.argv.index('--refresh-daily')
        lock = sys.argv[idx + 1] if len(sys.argv) > idx + 1 else None
        refresh_daily_cache(lock)
        return

    # Emoji output crashes on non-UTF-8 stdout (POSIX-locale Linux/CI) —
    # and the emoji-bearing fallback would too, defeating the error handler
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    try:
        # Read JSON input from Claude Code
        data = json.load(sys.stdin)

        # Extract information
        model_data = data.get('model', {})
        model_name = model_data.get('display_name', 'Claude')
        model_id = model_data.get('id', '')
        workspace = data.get('workspace', {})
        transcript_path = data.get('transcript_path', '')
        cost_data = data.get('cost', {})

        # Shorten model name for compact display
        model_name_short = shorten_model_name(model_name, model_id)

        # Which account this session bills to, and note it for the aggregator.
        # Recorded here (not in a hook) because the statusline already receives
        # the transcript path and inherits the session's startup environment.
        provider = detect_provider()
        record_session_provider(transcript_path, provider)

        # Detect context window size from model ID
        context_window = get_context_window_size(model_id)

        # Parse context usage with dynamic context window
        context_info = parse_context_from_transcript(transcript_path, context_window)

        # Build status components
        context_display = get_context_display(context_info, model_id)
        directory = get_directory_display(workspace)
        session_metrics = get_session_metrics(cost_data)
        keyboard_layout = get_keyboard_layout()
        
        # Provider badge next to the model: which account this session bills to.
        # Catches the failure mode where a settings.json model pin silently routes
        # a session to the wrong account — invisible until the invoice arrives.
        provider_badge = f" \033[35m{PROVIDER_LABELS.get(provider, provider.upper())}\033[0m"

        # Model display with context-aware coloring
        if context_info:
            percent = context_info.get('percent', 0)
            if percent >= 90:
                model_color = "\033[31m"  # Red
            elif percent >= 75:
                model_color = "\033[33m"  # Yellow
            else:
                model_color = "\033[32m"  # Green

            model_display = f"{model_color}[{model_name_short}{provider_badge}]\033[0m"
        else:
            model_display = f"\033[94m[{model_name_short}{provider_badge}]\033[0m"

        # Combine all components with keyboard layout indicator (only if non-English)
        layout_indicator = f" {keyboard_layout}" if keyboard_layout else ""
        status_line = f"{model_display} \033[93m📁 {directory}\033[0m 🧠 {context_display}{session_metrics}{layout_indicator}"
        
        print(status_line)
        
    except Exception as e:
        # Fallback display on any error. Must never throw itself:
        # emoji-free (survives ASCII stdout), getcwd guarded (cwd can be deleted)
        try:
            cwd = os.path.basename(os.getcwd())
        except OSError:
            cwd = "?"
        print(f"\033[94m[Claude]\033[0m \033[93m{cwd}\033[0m \033[31m[Error: {str(e)[:30]}]\033[0m")

if __name__ == "__main__":
    main()