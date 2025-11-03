@echo off
chcp 65001 > nul
echo ================================================================
echo CGRA 性能对比工具 - 一键打包脚本
echo ================================================================
echo.

REM 设置项目根目录
cd /d %~dp0

echo [1/5] 检查 Python 环境...
python --version > nul 2>&1
if errorlevel 1 (
    echo ✗ 未找到 Python，请先安装 Python 3.8 或更高版本
    pause
    exit /b 1
)
echo ✓ Python 环境正常

echo.
echo [2/5] 安装依赖包...
echo 正在安装项目依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo ✗ 依赖安装失败
    pause
    exit /b 1
)

echo 正在安装 PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo ✗ PyInstaller 安装失败
    pause
    exit /b 1
)
echo ✓ 依赖包安装完成

echo.
echo [3/5] 清理旧的构建文件...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "release" rmdir /s /q "release"
if exist "CGRAPerformanceGUI.spec" del /q "CGRAPerformanceGUI.spec"
echo ✓ 清理完成

echo.
echo [4/5] 开始打包应用程序...
echo 这可能需要几分钟时间，请耐心等待...
echo.

pyinstaller --name=CGRAPerformanceGUI ^
    --windowed ^
    --onedir ^
    --paths=src ^
    --add-data="config;config" ^
    --add-data="data;data" ^
    --add-data="bin;bin" ^
    --hidden-import=matplotlib ^
    --hidden-import=matplotlib.backends.backend_qt5agg ^
    --hidden-import=numpy ^
    --hidden-import=PyQt6 ^
    --hidden-import=PyQt6.QtCore ^
    --hidden-import=PyQt6.QtGui ^
    --hidden-import=PyQt6.QtWidgets ^
    --hidden-import=ui ^
    --hidden-import=ui.xml_highlighter ^
    --hidden-import=ui.styles ^
    --hidden-import=ui.charts ^
    --hidden-import=utils ^
    --hidden-import=validator ^
    --hidden-import=runner ^
    --hidden-import=thread ^
    --hidden-import=resource_path ^
    --exclude-module=tkinter ^
    --exclude-module=unittest ^
    src\gui.py

if errorlevel 1 (
    echo.
    echo ✗ 打包失败！
    pause
    exit /b 1
)

echo ✓ 打包完成

echo.
echo [5/5] 整理发布文件...

REM 创建 release 目录
mkdir release 2>nul

REM 复制打包后的程序
if exist "dist\CGRAPerformanceGUI\" (
    xcopy /E /I /Y "dist\CGRAPerformanceGUI" "release\CGRAPerformanceGUI\"
    echo ✓ 已复制应用程序到 release 目录
) else (
    echo ✗ 未找到打包后的程序
    pause
    exit /b 1
)

REM 创建启动脚本
echo @echo off > "release\启动应用.bat"
echo chcp 65001 ^> nul >> "release\启动应用.bat"
echo cd /d %%~dp0 >> "release\启动应用.bat"
echo cd CGRAPerformanceGUI >> "release\启动应用.bat"
echo start CGRAPerformanceGUI.exe >> "release\启动应用.bat"
echo exit >> "release\启动应用.bat"
echo ✓ 已创建启动脚本

REM 创建 README
echo ================================================================ > "release\使用说明.txt"
echo CGRA 性能对比工具 - 离线安装包 >> "release\使用说明.txt"
echo ================================================================ >> "release\使用说明.txt"
echo. >> "release\使用说明.txt"
echo 使用方法： >> "release\使用说明.txt"
echo 1. 将整个文件夹复制到目标 Windows 服务器 >> "release\使用说明.txt"
echo 2. 双击"启动应用.bat"运行程序 >> "release\使用说明.txt"
echo    或者进入 CGRAPerformanceGUI 文件夹，双击 CGRAPerformanceGUI.exe >> "release\使用说明.txt"
echo. >> "release\使用说明.txt"
echo 系统要求： >> "release\使用说明.txt"
echo - Windows 7/10/11 (64位) >> "release\使用说明.txt"
echo - 无需安装 Python >> "release\使用说明.txt"
echo - 无需联网 >> "release\使用说明.txt"
echo. >> "release\使用说明.txt"
echo 打包日期：%date% %time% >> "release\使用说明.txt"
echo ================================================================ >> "release\使用说明.txt"

echo ✓ 已创建使用说明

echo.
echo ================================================================
echo 打包成功完成！
echo ================================================================
echo.
echo 发布包位置： %cd%\release
echo.
echo 后续步骤：
echo 1. 将 release 文件夹压缩成 zip 文件
echo 2. 复制到 U盘 或通过网络传输到目标服务器
echo 3. 在目标服务器解压后，双击"启动应用.bat"运行
echo.
echo ================================================================

REM 打开 release 目录
explorer release

pause
