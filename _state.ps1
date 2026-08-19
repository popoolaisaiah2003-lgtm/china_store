$src = "C:\xampp\mysql\data\mysql"
$bak = "C:\xampp\mysql\data_backup_2026-08-17\mysql"

$names = 'columns_priv','db','global_priv','help_topic','tables_priv','proc','procs_priv','roles_mapping','table_stats','index_stats','column_stats','user'

"=== AFFECTED TABLE FILE STATE (current vs backup) ==="
foreach ($n in $names) {
    foreach ($ext in 'MAI','MAD','frm') {
        $c = Get-Item "$src\$n.$ext" -ErrorAction SilentlyContinue
        $b = Get-Item "$bak\$n.$ext" -ErrorAction SilentlyContinue
        if ($c -or $b) {
            [pscustomobject]@{
                File      = "$n.$ext"
                NowBytes  = $(if ($c) { $c.Length } else { 'MISSING' })
                BakBytes  = $(if ($b) { $b.Length } else { 'MISSING' })
                DataSame  = $(if ($c -and $b) { $c.Length -eq $b.Length } else { $false })
            }
        }
    }
}
