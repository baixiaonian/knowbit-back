#!/bin/bash

# AI写作工具后端启动脚本

echo "==================================="
echo "  AI写作工具后端 - 启动脚本"
echo "==================================="
echo ""

# 激活虚拟环境
source bin/activate

# 检查依赖
echo "检查依赖包..."
if ! python -c "import fastapi" 2>/dev/null; then
    echo "正在安装依赖..."
    pip install -r requirements.txt
fi

echo ""
echo "启动FastAPI应用..."
echo "API文档地址: http://localhost:8000/docs"
echo "ReDoc文档地址: http://localhost:8000/redoc"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

# 启动应用
python main.py

