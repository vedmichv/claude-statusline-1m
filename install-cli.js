#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');
const readline = require('readline');

// Colors for terminal output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  gray: '\x1b[90m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function showBanner() {
  console.clear();
  log('════════════════════════════════════════════════════════════════', 'cyan');
  log('', 'reset');
  log('       🧠 Claude Code Statusline with 1M Context', 'bright');
  log('', 'reset');
  log('       Real-time context monitoring + Premium pricing alerts', 'gray');
  log('', 'reset');
  log('════════════════════════════════════════════════════════════════', 'cyan');
  log('', 'reset');
}

async function promptUser(question, defaultValue = 'y') {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      rl.close();
      resolve(answer.trim().toLowerCase() || defaultValue);
    });
  });
}

async function installStatusline() {
  try {
    showBanner();

    // Check if --yes flag is provided
    const yesFlag = process.argv.includes('--yes') || process.argv.includes('-y');

    log('📦 Claude Code Statusline Installer', 'blue');
    log('', 'reset');

    // Ask for installation location
    let installLocation = 'local';

    if (!yesFlag) {
      log('Where would you like to install the statusline?', 'yellow');
      log('  1. 🏠 Global (~/.claude/settings.json) - All projects', 'reset');
      log('  2. 📁 Project (.claude/settings.json) - Shared with team', 'reset');
      log('  3. ⚙️  Local (.claude/settings.local.json) - Personal [Default]', 'reset');
      log('', 'reset');

      const choice = await promptUser('Enter your choice (1/2/3) [3]: ', '3');

      if (choice === '1') {
        installLocation = 'global';
      } else if (choice === '2') {
        installLocation = 'project';
      } else {
        installLocation = 'local';
      }
    }

    log(`\n📍 Installing to: ${installLocation} settings`, 'cyan');

    // Determine paths based on choice
    let claudeDir, settingsFile;

    if (installLocation === 'global') {
      claudeDir = path.join(os.homedir(), '.claude');
      settingsFile = 'settings.json';
    } else {
      claudeDir = path.join(process.cwd(), '.claude');
      settingsFile = installLocation === 'project' ? 'settings.json' : 'settings.local.json';
    }

    const scriptsDir = path.join(claudeDir, 'scripts');
    const settingsPath = path.join(claudeDir, settingsFile);

    // Create directories
    log('\n🔧 Creating directories...', 'blue');
    if (!fs.existsSync(claudeDir)) {
      fs.mkdirSync(claudeDir, { recursive: true });
      log('  ✓ Created .claude directory', 'green');
    }
    if (!fs.existsSync(scriptsDir)) {
      fs.mkdirSync(scriptsDir, { recursive: true });
      log('  ✓ Created scripts directory', 'green');
    }

    // Copy Python script
    log('\n📄 Installing Python script...', 'blue');
    const sourceScript = path.join(__dirname, 'scripts', 'context-monitor.py');
    const targetScript = path.join(scriptsDir, 'context-monitor.py');

    if (!fs.existsSync(sourceScript)) {
      throw new Error(`Source script not found: ${sourceScript}`);
    }

    fs.copyFileSync(sourceScript, targetScript);
    try {
      fs.chmodSync(targetScript, '755');
    } catch (e) {
      // Ignore chmod errors on Windows
    }
    log('  ✓ Installed context-monitor.py', 'green');

    // Update settings file
    log('\n⚙️  Updating settings file...', 'blue');
    let settings = {};

    if (fs.existsSync(settingsPath)) {
      const content = fs.readFileSync(settingsPath, 'utf8');
      settings = JSON.parse(content);
      log('  ✓ Loaded existing settings', 'green');
    } else {
      log('  ✓ Creating new settings file', 'green');
    }

    // Add statusLine configuration
    // IMPORTANT: Always use absolute paths for reliability (as per CLAUDE.md)
    const pythonPath = installLocation === 'global'
      ? path.join(os.homedir(), '.claude', 'scripts', 'context-monitor.py')
      : path.join(process.cwd(), '.claude', 'scripts', 'context-monitor.py');

    settings.statusLine = {
      type: 'command',
      command: `python3 "${pythonPath}"`
    };

    // Write settings
    fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2) + '\n');
    log('  ✓ Updated settings file', 'green');

    // Success message
    log('\n✅ Installation complete!', 'green');
    log('', 'reset');
    log('📍 Installation Details:', 'cyan');
    log(`  Location: ${installLocation}`, 'reset');
    log(`  Settings: ${settingsPath}`, 'gray');
    log(`  Script: ${targetScript}`, 'gray');
    log('', 'reset');
    log('🎯 Features Enabled:', 'cyan');
    log('  • Dynamic context window detection (1M, 200K)', 'reset');
    log('  • Real-time context usage percentage + token count', 'reset');
    log('  • Session cost and duration tracking', 'reset');
    log('  • Premium pricing alert (💸2x, legacy Sonnet 4/4.5 only)', 'reset');
    log('', 'reset');
    log('🔄 Next Step: Restart Claude Code to see your statusline!', 'yellow');
    log('', 'reset');

  } catch (error) {
    log(`\n❌ Installation failed: ${error.message}`, 'red');
    log('\n💡 Troubleshooting:', 'yellow');
    log('  • Make sure you have write permissions', 'gray');
    log('  • Check that Python 3 is installed: python3 --version', 'gray');
    log('  • For global install, ensure ~/.claude/ is accessible', 'gray');
    process.exit(1);
  }
}

// Show help
if (process.argv.includes('--help') || process.argv.includes('-h')) {
  showBanner();
  log('Usage:', 'yellow');
  log('  npx claude-statusline-1m --install        Interactive installation', 'reset');
  log('  npx claude-statusline-1m --install --yes  Install with defaults (local)', 'reset');
  log('', 'reset');
  log('Options:', 'yellow');
  log('  -y, --yes    Skip prompts, use defaults', 'reset');
  log('  -h, --help   Show this help message', 'reset');
  log('', 'reset');
  process.exit(0);
}

// Run installer
if (process.argv.includes('--install')) {
  installStatusline();
} else {
  // If no --install flag, show help
  showBanner();
  log('Welcome to Claude Code Statusline installer!', 'cyan');
  log('', 'reset');
  log('To install, run:', 'yellow');
  log('  npx claude-statusline-1m --install', 'bright');
  log('', 'reset');
  log('Or for quick install with defaults:', 'yellow');
  log('  npx claude-statusline-1m --install --yes', 'bright');
  log('', 'reset');
  log('For help:', 'yellow');
  log('  npx claude-statusline-1m --help', 'bright');
  log('', 'reset');
}
