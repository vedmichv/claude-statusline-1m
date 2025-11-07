#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

// Run the Python script bundled with the package
const scriptPath = path.join(__dirname, 'scripts', 'context-monitor.py');
const python = spawn('python3', [scriptPath], {
  stdio: ['pipe', 'pipe', 'pipe']
});

// Set stdin encoding
process.stdin.setEncoding('utf8');

// Collect all input from stdin
let inputData = '';

process.stdin.on('data', (chunk) => {
  inputData += chunk;
});

process.stdin.on('end', () => {
  // Write collected input to Python script
  python.stdin.write(inputData);
  python.stdin.end();
});

// Pass stdout from Python script to Claude Code
python.stdout.pipe(process.stdout);
python.stderr.pipe(process.stderr);

python.on('error', (err) => {
  console.error('Failed to run statusline:', err.message);
  process.exit(1);
});

python.on('exit', (code) => {
  process.exit(code || 0);
});

// Handle process termination
process.on('SIGTERM', () => {
  python.kill('SIGTERM');
  process.exit(0);
});

process.on('SIGINT', () => {
  python.kill('SIGINT');
  process.exit(0);
});
