$src = "C:\xampp\mysql\data"
$out = "C:\xampp\mysql\manifest_before_2026-08-17.csv"

$files = Get-ChildItem $src -Recurse -File -Include *.ibd, *.frm, ibdata1, ib_logfile0, ib_logfile1 -ErrorAction SilentlyContinue
$files += Get-Item "$src\ibdata1", "$src\ib_logfile0", "$src\ib_logfile1" -ErrorAction SilentlyContinue

$files | Sort-Object FullName -Unique | ForEach-Object {
    [pscustomobject]@{
        Path   = $_.FullName.Replace($src, '')
        Bytes  = $_.Length
        Sha256 = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
    }
} | Export-Csv $out -NoTypeInformation

"Manifest written: $out"
"Entries: " + (Import-Csv $out).Count
