#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');

const CLAUDE_DIR = path.join(os.homedir(), '.claude');
const SCRIPTS_DIR = path.join(CLAUDE_DIR, 'scripts');
const SETTINGS_FILE = path.join(CLAUDE_DIR, 'settings.local.json');
const SCRIPT_NAME = 'context-monitor.py';

async function installStatusline() {
  try {
    console.log('🚀 Installing Claude Code statusline with 1M context support...\n');

    // 1. Ensure directories exist
    if (!fs.existsSync(CLAUDE_DIR)) {
      fs.mkdirSync(CLAUDE_DIR, { recursive: true });
      console.log('✓ Created .claude directory');
    }

    if (!fs.existsSync(SCRIPTS_DIR)) {
      fs.mkdirSync(SCRIPTS_DIR, { recursive: true });
      console.log('✓ Created scripts directory');
    }

    // 2. Copy script file
    const sourceScript = path.join(__dirname, 'scripts', SCRIPT_NAME);
    const targetScript = path.join(SCRIPTS_DIR, SCRIPT_NAME);

    fs.copyFileSync(sourceScript, targetScript);
    fs.chmodSync(targetScript, '755');
    console.log('✓ Installed context-monitor.py');

    // 3. Update settings.local.json
    let settings = {};

    if (fs.existsSync(SETTINGS_FILE)) {
      const content = fs.readFileSync(SETTINGS_FILE, 'utf8');
      settings = JSON.parse(content);
      console.log('✓ Loaded existing settings');
    } else {
      console.log('✓ Creating new settings file');
    }

    // Update statusLine configuration
    settings.statusLine = {
      type: 'command',
      command: `python3 .claude/scripts/${SCRIPT_NAME}`
    };

    // Write settings
    fs.writeFileSync(SETTINGS_FILE, JSON.stringify(settings, null, 2));
    console.log('✓ Updated settings.local.json');

    console.log('\n✅ Installation complete!\n');
    console.log('Features:');
    console.log('  • Dynamic context window detection (1M, 200K, etc.)');
    console.log('  • Automatically detects [1m] or [200k] suffix in model ID');
    console.log('  • Real-time context usage percentage');
    console.log('  • Session cost and duration tracking\n');
    console.log('Restart Claude Code to see your new statusline!');

  } catch (error) {
    console.error('❌ Installation failed:', error.message);
    process.exit(1);
  }
}

installStatusline();
