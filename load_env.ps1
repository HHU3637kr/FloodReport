# load_env.ps1 - 加载.env文件中的环境变量到终端
Write-Host "正在加载.env文件中的环境变量..." -ForegroundColor Green

$envFile = ".\.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        # 跳过空行和注释
        if ($line -and !$line.StartsWith('#')) {
            $key, $value = $line.Split('=', 2)
            # 设置环境变量
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
            Write-Host "设置环境变量: $key" -ForegroundColor Cyan
        }
    }
    Write-Host "环境变量加载完成!" -ForegroundColor Green
    
    # 显示关键环境变量
    Write-Host "`n关键环境变量:" -ForegroundColor Yellow
    Write-Host "VOLC_ACCESSKEY: $env:VOLC_ACCESSKEY" -ForegroundColor Yellow
    Write-Host "VOLC_SECRETKEY: $env:VOLC_SECRETKEY" -ForegroundColor Yellow
    Write-Host "DASHSCOPE_API_KEY: $env:DASHSCOPE_API_KEY" -ForegroundColor Yellow
} else {
    Write-Host "错误：.env文件不存在" -ForegroundColor Red
} 