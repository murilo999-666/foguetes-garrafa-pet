# Painel ao vivo da campanha bit06. Rode e deixe aberto; atualiza sozinho.
# Sair: Ctrl+C
#   -Once  desenha uma vez e sai (para conferir o visual)
param([switch]$Once)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'SilentlyContinue'

$pasta  = 'D:\1-Competicoes\OBAFOG\foguetes\bit06 1,8L'
$status = Join-Path $pasta 'simulacoes\status_pet.json'
$log    = Join-Path $pasta 'log_busca_bit06_pet.txt'
$inicio = $null

function Barra([double]$frac, [int]$larg) {
    if ($frac -lt 0) { $frac = 0 }
    if ($frac -gt 1) { $frac = 1 }
    $cheio = [int][Math]::Round($frac * $larg)
    return ('█' * $cheio) + ('░' * ($larg - $cheio))
}

function Dur([TimeSpan]$t) {
    if ($t.TotalHours -ge 1) { return ('{0}h{1:00}m' -f [int]$t.TotalHours, $t.Minutes) }
    return ('{0}m{1:00}s' -f [int]$t.TotalMinutes, $t.Seconds)
}

while ($true) {
    $s = $null
    try { $s = Get-Content $status -Raw -Encoding UTF8 | ConvertFrom-Json } catch { }

    if (-not $inicio) {
        $linha = Select-String -Path $log -Pattern 'início:' -Encoding UTF8 | Select-Object -First 1
        if ($linha) {
            $txt = $linha.Line -replace '.*início:\s*', ''
            try { $inicio = [datetime]::ParseExact($txt.Trim(), 'yyyy-MM-dd HH:mm:ss', $null) } catch { }
        }
        if (-not $inicio) { $inicio = (Get-Item $log).CreationTime }
    }

    Clear-Host
    Write-Host ''
    Write-Host '  ╔════════════════════════════════════════════════════════════╗' -ForegroundColor DarkCyan
    Write-Host '  ║   bit06 · garrafa reduzida 1,8 L · coifa PET + nota aerodinamica  ║' -ForegroundColor Cyan
    Write-Host '  ╚════════════════════════════════════════════════════════════╝' -ForegroundColor DarkCyan
    Write-Host ''

    if (-not $s) {
        Write-Host '   aguardando o primeiro status...' -ForegroundColor DarkGray
    }
    elseif ("$($s.etapa)" -eq 'concluido') {
        Write-Host ('   ' + (Barra 1 44)) -ForegroundColor Green
        Write-Host ''
        Write-Host '   CAMPANHA CONCLUÍDA' -ForegroundColor Green
        Write-Host ''
        Write-Host ('   simulações .... {0:N0}' -f [int]$s.simulacoes_feitas)
        Write-Host ('   melhor nota ... {0} / 100' -f $s.melhor_nota) -ForegroundColor Yellow
        Write-Host ('   duração ....... {0}' -f $s.duracao)
        Write-Host ''
        Write-Host '   relatório: RELATORIO_bit06_PET_AERO.md' -ForegroundColor DarkGray
    }
    elseif ("$($s.etapa)" -eq '2') {
        $frac = 0.0
        if ($s.finalistas -gt 0) { $frac = [double]$s.finalista / [double]$s.finalistas }
        Write-Host '   ETAPA 2 · nota multicritério dos finalistas' -ForegroundColor Magenta
        Write-Host ''
        Write-Host ('   ' + (Barra $frac 44) + ('  {0:P0}' -f $frac)) -ForegroundColor Magenta
        Write-Host ''
        Write-Host ('   finalista ..... {0} de {1}' -f $s.finalista, $s.finalistas)
        Write-Host ('   aprovados ..... {0}' -f $s.aprovados) -ForegroundColor Green
        Write-Host ('   simulações .... {0:N0}' -f [int]$s.simulacoes_feitas)
    }
    else {
        $frac = 0.0
        if ($s.simulacoes_total -gt 0) {
            $frac = [double]$s.simulacoes_feitas / [double]$s.simulacoes_total
        }
        $cor = 'Cyan'
        if ($frac -gt 0.66) { $cor = 'Green' } elseif ($frac -gt 0.33) { $cor = 'Yellow' }

        Write-Host ('   ETAPA 1 · busca ampla   ·   bloco {0} de {1}' -f $s.bloco, $s.blocos) -ForegroundColor White
        Write-Host ''
        Write-Host ('   ' + (Barra $frac 44) + ('  {0,5:N1}%' -f $s.percentual)) -ForegroundColor $cor
        Write-Host ''
        Write-Host ('   simulações .... {0:N0} de {1:N0}' -f [int]$s.simulacoes_feitas, [int]$s.simulacoes_total)
        Write-Host ('   velocidade .... {0} sims/s' -f $s.sims_por_segundo)
        Write-Host ('   melhor nota ... {0} / 100' -f $s.melhor_nota_etapa1) -ForegroundColor Yellow
        $dec = ''
        if ($inicio) { $dec = Dur ((Get-Date) - $inicio) }
        Write-Host ('   decorrido ..... {0}        resta ~{1}' -f $dec, $s.restante_estimado)
    }

    Write-Host ''
    Write-Host '   ──────────────────────────── log ────────────────────────────' -ForegroundColor DarkGray
    Get-Content $log -Tail 6 -Encoding UTF8 | ForEach-Object {
        $t = $_
        if ($t.Length -gt 74) { $t = $t.Substring(0, 74) }
        Write-Host ('   ' + $t) -ForegroundColor DarkGray
    }
    Write-Host ''
    Write-Host ('   atualizado {0}   ·   Ctrl+C para sair' -f (Get-Date -Format 'HH:mm:ss')) -ForegroundColor DarkGray

    if ($Once) { break }
    Start-Sleep -Seconds 5
}
