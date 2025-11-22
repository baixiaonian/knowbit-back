#!/bin/bash
# 测试运行脚本
# 使用方法: ./tests/run_tests.sh [test_file_name]

set -e

# 获取项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 设置 Python 路径（避免重复添加）
if [[ ":$PYTHONPATH:" != *":$PROJECT_ROOT:"* ]]; then
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
fi

echo "=========================================="
echo "项目根目录: $PROJECT_ROOT"
echo "Python 路径: $PYTHONPATH"
echo "=========================================="
echo ""

# 如果指定了测试文件，只运行该文件
if [ -n "$1" ]; then
    # 处理不同的路径格式
    TEST_FILE="$1"
    
    # 如果已经是完整路径（包含 tests/），直接使用
    if [[ "$TEST_FILE" == tests/* ]] || [[ "$TEST_FILE" == ./tests/* ]]; then
        # 移除 ./ 前缀（如果有）
        TEST_FILE="${TEST_FILE#./}"
    # 如果只是文件名，添加 tests/ 前缀
    elif [[ "$TEST_FILE" != */* ]]; then
        TEST_FILE="tests/$TEST_FILE"
    fi
    
    # 检查文件是否存在
    if [ ! -f "$TEST_FILE" ]; then
        echo "错误: 测试文件 $TEST_FILE 不存在"
        echo ""
        echo "可用的测试文件:"
        ls -1 tests/test_*.py 2>/dev/null || echo "  无"
        exit 1
    fi
    
    echo "运行测试: $TEST_FILE"
    echo "=========================================="
    python3 "$TEST_FILE"
else
    # 运行所有测试
    echo "运行所有测试..."
    echo ""
    
    for test_file in tests/test_*.py; do
        if [ -f "$test_file" ]; then
            echo "=========================================="
            echo "运行: $test_file"
            echo "=========================================="
            python3 "$test_file"
            echo ""
        fi
    done
    
    echo "=========================================="
    echo "所有测试完成"
    echo "=========================================="
fi

