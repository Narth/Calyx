# Station Calyx — Single bridge pulse

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
$id = ('sched-{0:yyyyMMddTHHmmss}' -f (Get-Date).ToUniversalTime())
$script = Join-Path $root 'tools/bridge_pulse_generator.py'
& python $script --report-id $id
