# Download and extract Dependency Walker - https://github.com/OnesoftQwQ/dependency-walker-installer
# Fixed URL: https://dependencywalker.com/depends22_x64.zip
# Target path: Nuitka's cache directory

# Set download URL
$downloadUrl = "https://dependencywalker.com/depends22_x64.zip"

# Set target path using current user's profile
$targetPath = "$env:NUITKA_CACHE_DIR\downloads\depends\x86_64"

# Create target directory if it doesn't exist
Write-Host "Creating target directory: $targetPath"
New-Item -ItemType Directory -Path $targetPath -Force

# Download the file
Write-Host "Downloading Dependency Walker from: $downloadUrl"
$zipFile = "$targetPath\depends22_x64.zip"
try {:
    Invoke-WebRequest -Uri $downloadUrl -OutFile $zipFile
    Write-Host "Download completed successfully"
} catch {
    Write-Error "Failed to download file: $($_.Exception.Message)"
    exit 1
}

# Extract the zip file
Write-Host "Extracting files to: $targetPath"
try {
    Expand-Archive -Path $zipFile -DestinationPath $targetPath -Force
    Write-Host "Extraction completed successfully"
} catch {
    Write-Error "Failed to extract file: $($_.Exception.Message)"
    exit 1
}

# Clean up - remove the zip file
Write-Host "Cleaning up temporary files"
Remove-Item $zipFile -Force

Write-Host "Dependency Walker has been successfully downloaded and extracted to: $targetPath"