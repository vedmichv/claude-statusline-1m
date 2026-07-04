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

def get_session_metrics(cost_data):
    """Get session metrics display."""
    if not cost_data:
        return ""
    
    metrics = []
    
    # Cost
    cost_usd = cost_data.get('total_cost_usd', 0)
    if cost_usd > 0:
        if cost_usd >= 0.10:
            cost_color = "\033[31m"  # Red for expensive
        elif cost_usd >= 0.05:
            cost_color = "\033[33m"  # Yellow for moderate
        else:
            cost_color = "\033[32m"  # Green for cheap
        
        cost_str = f"{cost_usd*100:.0f}¢" if cost_usd < 0.01 else f"${cost_usd:.3f}"
        metrics.append(f"{cost_color}💰 {cost_str}\033[0m")
    
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

        # Detect context window size from model ID
        context_window = get_context_window_size(model_id)

        # Parse context usage with dynamic context window
        context_info = parse_context_from_transcript(transcript_path, context_window)

        # Build status components
        context_display = get_context_display(context_info, model_id)
        directory = get_directory_display(workspace)
        session_metrics = get_session_metrics(cost_data)
        keyboard_layout = get_keyboard_layout()
        
        # Model display with context-aware coloring
        if context_info:
            percent = context_info.get('percent', 0)
            if percent >= 90:
                model_color = "\033[31m"  # Red
            elif percent >= 75:
                model_color = "\033[33m"  # Yellow
            else:
                model_color = "\033[32m"  # Green

            model_display = f"{model_color}[{model_name_short}]\033[0m"
        else:
            model_display = f"\033[94m[{model_name_short}]\033[0m"

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