# Phase 0 spike instrumentation (single-purpose, throwaway).
# Reads PostToolUse hook stdin (JSON), writes verbatim to docs/evidence/hook-payloads/{tool}-{timestamp}.json
# After spike completes, this file + the .claude/settings.json hook entry get removed.

$ErrorActionPreference = 'Continue'

$repoRoot = Split-Path -Parent $PSScriptRoot
$evidenceDir = Join-Path $repoRoot 'docs\evidence\hook-payloads'

if (-not (Test-Path $evidenceDir)) {
    New-Item -ItemType Directory -Path $evidenceDir -Force | Out-Null
}

# Read raw stdin
$raw = [Console]::In.ReadToEnd()

# Parse just enough to name the file by tool_name; fall back to "unknown" on parse failure
$toolName = 'unknown'
try {
    $obj = $raw | ConvertFrom-Json
    if ($obj.tool_name) { $toolName = $obj.tool_name }
} catch {
    # parse failed — still save raw so we can inspect what arrived
}

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$outFile = Join-Path $evidenceDir "$toolName-$timestamp.json"

# Save raw stdin so we see exactly what Claude Code sent (no re-serialization losses)
[System.IO.File]::WriteAllText($outFile, $raw, [System.Text.Encoding]::UTF8)

# Exit 0: PostToolUse hooks should never block; we only observe.
exit 0
