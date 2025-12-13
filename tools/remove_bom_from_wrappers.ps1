# Remove UTF-8 BOM from any Calyx* wrapper .bat files in tools\
Get-ChildItem -Path .\tools\Calyx*_wrapper.bat -File -ErrorAction SilentlyContinue | ForEach-Object {
    $p = $_.FullName
    try {
        $bytes = [System.IO.File]::ReadAllBytes($p)
        if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
            Write-Output "Stripping BOM: $p"
            $newBytes = $bytes[3..($bytes.Length - 1)]
            [System.IO.File]::WriteAllBytes($p, $newBytes)
        } else {
            Write-Output "No BOM: $p"
        }
    } catch {
        $m = $_.Exception.Message
        Write-Output ("Failed to process {0}: {1}" -f $p, $m)
    }
}
