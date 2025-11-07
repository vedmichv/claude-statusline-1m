#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

// Run the Python script bundled with the package
const scriptPath = path.join(__dirname, 'scripts', 'context-monitor.py');
const python = spawn('python3', [scriptPath]);

// Pass stdin from Claude Code to Python script
process.stdin.pipe(python.stdin);

// Pass stdout from Python script to Claude Code
python.stdout.pipe(process.stdout);
python.stderr.pipe(process.stderr);

python.on('error', (err) => {
  console.error('Failed to run statusline:', err.message);
  process.exit(1);
});

python.on('exit', (code) => {
  process.exit(code);
});
