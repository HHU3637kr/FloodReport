@echo off
echo 启动防汛应急报告生成系统...
echo ==============================

REM 加载环境变量
echo 正在加载环境变量...
powershell -ExecutionPolicy Bypass -File .\load_env.ps1

REM 启动后端API服务器
echo 正在启动后端API服务器...
start cmd /k "cd /d %~dp0 && python -m src.ui.run_api"

REM 等待2秒，确保后端已启动
timeout /t 2 /nobreak > nul

REM 启动前端服务
echo 正在启动前端服务...
start cmd /k "cd /d %~dp0/frontend && npm run dev"

echo ==============================
echo 系统启动完成！
echo 前端地址: http://localhost:5173
echo 后端地址: http://localhost:8000
echo ==============================
echo 请使用浏览器访问前端地址进行操作
echo 测试链接: @https://news.qq.com/rain/a/20240918A05GXB00
echo ============================== 