$ErrorActionPreference = 'Stop'

$packageName = 'bbc-master'
$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$url = 'https://github.com/Anubis44197/BBC-SON-SURUM/archive/refs/tags/v8.3.0.zip'
$checksum = 'b5fc14ac471171ad59c8a77ea8b4250eccb72d9c5cc7fdfc355c277794eaa70e'

$packageArgs = @{
  packageName    = $packageName
  unzipLocation  = $toolsDir
  url            = $url
  checksum       = $checksum
  checksumType   = 'sha256'
}

Install-ChocolateyZipPackage @packageArgs

$bbcRoot = Join-Path $toolsDir 'BBC-8.3.0'
Write-Host "BBC extracted to: $bbcRoot"
Write-Host 'Run install_global.bat from the extracted folder to complete setup.'
