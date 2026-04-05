$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "Building NexRag report from: $root"

$miktexBin = Join-Path $env:LOCALAPPDATA "Programs\MiKTeX\miktex\bin\x64"
if ((Test-Path $miktexBin) -and (-not ($env:PATH -split ';' | Where-Object { $_ -eq $miktexBin }))) {
    $env:PATH = "$miktexBin;$env:PATH"
}

if ((Get-Command latexmk -ErrorAction SilentlyContinue) -and (Get-Command perl -ErrorAction SilentlyContinue)) {
    Write-Host "Using latexmk..."
    latexmk -pdf -shell-escape -interaction=nonstopmode -file-line-error main.tex
    exit $LASTEXITCODE
}

if (Get-Command pdflatex -ErrorAction SilentlyContinue) {
    Write-Host "Using pdflatex..."
    pdflatex -shell-escape -interaction=nonstopmode -file-line-error main.tex
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    pdflatex -shell-escape -interaction=nonstopmode -file-line-error main.tex
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    pdflatex -shell-escape -interaction=nonstopmode -file-line-error main.tex
    exit $LASTEXITCODE
}

Write-Error "No LaTeX engine found. Install MiKTeX or TeX Live first."
