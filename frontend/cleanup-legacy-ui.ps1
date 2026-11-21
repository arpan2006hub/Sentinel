$legacyFiles = @(
    'src/pages/SettingsPage.tsx',
    'src/components/Badge.tsx',
    'src/components/Icon.tsx',
    'src/components/MetricCard.tsx',
    'src/components/Modal.tsx',
    'src/utils/format.ts'
)

foreach ($relativePath in $legacyFiles) {
    $target = Join-Path $PSScriptRoot $relativePath
    if (Test-Path -LiteralPath $target -PathType Leaf) {
        Remove-Item -LiteralPath $target -Force
        Write-Host "Removed legacy UI file: $relativePath"
    }
}

Write-Host 'Legacy UI cleanup complete.'
