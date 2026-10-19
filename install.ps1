# Forward to the Python installer, passing through all arguments.
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
& python (Join-Path $here "install.py") @args
exit $LASTEXITCODE
