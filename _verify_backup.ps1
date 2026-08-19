$src = "C:\xampp\mysql\data"
$bak = "C:\xampp\mysql\data_backup_2026-08-17"

$sd = Get-ChildItem $src -Directory | Select-Object -ExpandProperty Name
$bd = Get-ChildItem $bak -Directory | Select-Object -ExpandProperty Name

$rows = foreach ($d in $sd) {
    $sc = (Get-ChildItem "$src\$d" -File -ErrorAction SilentlyContinue).Count
    $bc = (Get-ChildItem "$bak\$d" -File -ErrorAction SilentlyContinue).Count
    [pscustomobject]@{
        DB       = $d
        InBackup = ($bd -contains $d)
        SrcFiles = $sc
        BakFiles = $bc
        Match    = ($sc -eq $bc)
    }
}
$rows | Format-Table -AutoSize

"MISSING FOLDERS: " + (($sd | Where-Object { $bd -notcontains $_ }) -join ', ')
"FOLDERS WITH COUNT MISMATCH: " + (($rows | Where-Object { -not $_.Match } | Select-Object -ExpandProperty DB) -join ', ')

"=== REQUIRED DB CHECK ==="
'china_store_db','yan_zhen_peptide','kayhomes','knotique_db' | ForEach-Object {
    [pscustomobject]@{ Required = $_; PresentInBackup = (Test-Path "$bak\$_") }
} | Format-Table -AutoSize
