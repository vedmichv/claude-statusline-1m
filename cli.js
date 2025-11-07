#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');

// Check if being run as statusline (stdin has data from Claude Code)
// or as installer (user running with --install flag)

const hasInstallFlag = process.argv.includes('--install');
const hasHelpFlag = process.argv.includes('--help') || process.argv.includes('-h');

// If stdin is a TTY (terminal), user is running it interactively
// If stdin is NOT a TTY, Claude Code is piping JSON to it
const isStatuslineMode = !process.stdin.isTTY && !hasInstallFlag && !hasHelpFlag;

if (isStatuslineMode) {
  // Run as statusline - delegate to statusline.js
  require('./statusline.js');
} else if (hasInstallFlag) {
  // Run as installer - delegate to install-cli.js
  require('./install-cli.js');
} else if (hasHelpFlag) {
  // Show help
  console.log(`
Claude Code Statusline with 1M Context Support
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 INSTALLATION

  Automatic installation:
    npx claude-statusline-1m --install

  Quick install (with defaults):
    npx claude-statusline-1m --install --yes

⚙️  OPTIONS

  --install       Install statusline to Claude Code
  --yes, -y       Skip prompts (use with --install)
  --help, -h      Show this help message

🎯 FEATURES

  • Dynamic context window detection (1M, 200K)
  • Real-time context usage percentage
  • Session cost and duration tracking
  • Premium pricing alert (💸2x when >200K tokens)
  • Color-coded visual indicators

📖 DOCUMENTATION

  GitHub: https://github.com/vedmichv/claude-statusline-1m
  npm: https://npmjs.com/package/claude-statusline-1m

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`);
} else {
  // Show quick start message
  console.log(`
🧠 Claude Code Statusline with 1M Context

To install, run:
  npx claude-statusline-1m --install

For help:
  npx claude-statusline-1m --help
`);
}
