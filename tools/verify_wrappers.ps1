$files = Get-ChildItem -Path .\tools\Calyx*_wrapper.bat -File -ErrorAction SilentlyContinue
foreach ($f in $files) {
    Write-Output "--- $($f.Name) ---"
    Get-Content -Path $f.FullName -Encoding utf8 -TotalCount 5 | ForEach-Object { Write-Output $_ }
    Write-Output ""
}
