# deploy/deploy_azure.ps1
# Deploys DocSense to Azure Container Apps.
#   - Builds nothing in the cloud: pushes the locally built image (docsense:latest) to ACR
#     (ACR cloud builds are often blocked on free-trial subscriptions).
#   - API keys are read from .env and stored as Container App SECRETS, never baked into the image.
#   - Scale to zero (min 0) and max 1 replica: near-zero idle cost, and a hard ceiling on load.
# Re-runnable: first run creates everything; later runs push a new image tag and update the app.
#
# Usage (from repo root, after `docker build -t docsense:latest .` and `az login`):
#   powershell -ExecutionPolicy Bypass -File deploy\deploy_azure.ps1
param(
    [string]$Location = "uaenorth",
    [string]$ResourceGroup = "docsense-rg",
    [string]$AppName = "docsense",
    [string]$EnvName = "docsense-env"
)
$ErrorActionPreference = "Stop"

function Find-Exe($name, $fallback) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    if (Test-Path $fallback) { return $fallback }
    throw "$name not found"
}
$az = Find-Exe "az" "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
$docker = Find-Exe "docker" "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe"

function Az { & $az @args --only-show-errors; if ($LASTEXITCODE -ne 0) { throw "az $($args[0..1] -join ' ') failed" } }

# ── Read .env (values never printed) ─────────────────────
$envVars = @{}
Get-Content (Join-Path $PSScriptRoot "..\.env") | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
        $k, $v = $line.Split("=", 2)
        $envVars[$k.Trim()] = $v.Trim().Trim('"').Trim("'")
    }
}
foreach ($k in "OPENAI_API_KEY", "COHERE_API_KEY", "PINECONE_API_KEY", "PINECONE_INDEX_NAME") {
    if (-not $envVars[$k]) { throw "$k missing from .env" }
}

# ── Resource group + registry ────────────────────────────
Write-Host "Resource group $ResourceGroup ($Location)..."
Az group create -n $ResourceGroup -l $Location -o none

$acr = (& $az acr list -g $ResourceGroup --query "[0].name" -o tsv --only-show-errors)
if (-not $acr) {
    $acr = "docsense" + (-join ((97..122) | Get-Random -Count 6 | ForEach-Object { [char]$_ }))
    Write-Host "Creating container registry $acr..."
    Az acr create -g $ResourceGroup -n $acr --sku Basic --admin-enabled true -o none
}
$server = "$acr.azurecr.io"
$tag = Get-Date -Format "yyyyMMdd-HHmmss"
$image = "$server/docsense:$tag"

Write-Host "Pushing $image..."
Az acr login -n $acr
& $docker tag docsense:latest $image
& $docker push $image
if ($LASTEXITCODE -ne 0) { throw "docker push failed" }

# ── Container Apps environment ───────────────────────────
$envExists = (& $az containerapp env list -g $ResourceGroup --query "[?name=='$EnvName'].name" -o tsv --only-show-errors)
if (-not $envExists) {
    Write-Host "Creating Container Apps environment $EnvName (takes a few minutes)..."
    Az containerapp env create -n $EnvName -g $ResourceGroup -l $Location -o none
}

# ── Secrets + env vars ───────────────────────────────────
$secrets = @(
    "openai-key=$($envVars['OPENAI_API_KEY'])",
    "cohere-key=$($envVars['COHERE_API_KEY'])",
    "pinecone-key=$($envVars['PINECONE_API_KEY'])"
)
$appEnv = @(
    "OPENAI_API_KEY=secretref:openai-key",
    "COHERE_API_KEY=secretref:cohere-key",
    "PINECONE_API_KEY=secretref:pinecone-key",
    "PINECONE_INDEX_NAME=$($envVars['PINECONE_INDEX_NAME'])",
    "USE_PINECONE=true"
)
if ($envVars['LANGSMITH_API_KEY']) {
    $secrets += "langsmith-key=$($envVars['LANGSMITH_API_KEY'])"
    $appEnv += "LANGSMITH_API_KEY=secretref:langsmith-key", "LANGSMITH_TRACING=true",
               "LANGSMITH_ENDPOINT=https://api.smith.langchain.com",
               "LANGSMITH_PROJECT=$(if ($envVars['LANGSMITH_PROJECT']) { $envVars['LANGSMITH_PROJECT'] } else { 'docsense' })"
}

# ── Create or update the app ─────────────────────────────
$appExists = (& $az containerapp list -g $ResourceGroup --query "[?name=='$AppName'].name" -o tsv --only-show-errors)
if (-not $appExists) {
    Write-Host "Creating container app $AppName..."
    $pw = (& $az acr credential show -n $acr --query "passwords[0].value" -o tsv --only-show-errors)
    Az containerapp create -n $AppName -g $ResourceGroup --environment $EnvName `
        --image $image --registry-server $server --registry-username $acr --registry-password $pw `
        --target-port 8501 --ingress external `
        --min-replicas 0 --max-replicas 1 --cpu 1.0 --memory 2.0Gi `
        --secrets @secrets --env-vars @appEnv -o none
} else {
    Write-Host "Updating container app $AppName..."
    Az containerapp secret set -n $AppName -g $ResourceGroup --secrets @secrets -o none
    Az containerapp update -n $AppName -g $ResourceGroup --image $image --set-env-vars @appEnv -o none
}

$fqdn = (& $az containerapp show -n $AppName -g $ResourceGroup --query "properties.configuration.ingress.fqdn" -o tsv --only-show-errors)
Write-Host ""
Write-Host "Deployed: https://$fqdn"
