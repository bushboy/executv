# Build the ExecuTV images and save them to deployment/images/executv-images.tar.
# Run from anywhere:
#   powershell -ExecutionPolicy Bypass -File deployment/build-and-save.ps1
#
# The visual image bakes https://executv.delegant.online as the API origin.
# Rebuild and save again if that hostname changes.
#
# On the VPS, from the deployment directory:
#   docker load -i images/executv-images.tar
#   cp .env.example .env
#   docker compose up -d

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$DeploymentDir = $PSScriptRoot
$RepoRoot = Split-Path -Parent $DeploymentDir
$ImageDir = Join-Path $DeploymentDir "images"
$TarPath = Join-Path $ImageDir "executv-images.tar"
$PythonImage = "executv-python:hackathon"
$VisualImage = "executv-visual:hackathon"

function Invoke-Docker {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "docker is not on PATH"
}

New-Item -ItemType Directory -Force -Path $ImageDir | Out-Null

Write-Host "Building $PythonImage"
Invoke-Docker @(
    "build",
    "-f", (Join-Path $RepoRoot "docker\Dockerfile.python"),
    "-t", $PythonImage,
    $RepoRoot
)

Write-Host "Building $VisualImage"
Invoke-Docker @(
    "build",
    "-f", (Join-Path $RepoRoot "apps\visual_display_adapter\Dockerfile"),
    "--build-arg", "VITE_CORE_ENGINE_URL=https://executv.delegant.online",
    "--build-arg", "VITE_INGRESS_GATEWAY_URL=https://executv.delegant.online",
    "-t", $VisualImage,
    (Join-Path $RepoRoot "apps\visual_display_adapter")
)

if (Test-Path $TarPath) {
    Remove-Item -Force $TarPath
}

Write-Host "Saving $PythonImage and $VisualImage"
Invoke-Docker @("save", "-o", $TarPath, $PythonImage, $VisualImage)

$SizeMb = [math]::Round((Get-Item $TarPath).Length / 1MB, 1)
Write-Host "Wrote $TarPath ($SizeMb MB)"
Write-Host "Copy the deployment folder to the VPS, then: docker load -i images/executv-images.tar && cp .env.example .env && docker compose up -d"
