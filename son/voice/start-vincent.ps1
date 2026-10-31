$ErrorActionPreference = 'Stop'
$voiceRepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$voiceDrive = $voiceRepoRoot.Substring(0,1).ToLowerInvariant()
$voiceLinuxRoot = '/mnt/' + $voiceDrive + $voiceRepoRoot.Substring(2).Replace('\','/')
$voiceRuntime = $voiceLinuxRoot + '/work/vincent-runtime-7c78ec4'
$voiceLauncher = $voiceLinuxRoot + '/son/voice/evals/start_vincent_private.py'
& wsl -d Ubuntu-24.04 --cd $voiceRuntime -- .venv/bin/python $voiceLauncher
exit $LASTEXITCODE
