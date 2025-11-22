# 测试文件说明

本目录包含所有测试文件。

## 测试文件列表

### test_memory.py
测试记忆模块功能，包括：
- 基本记忆操作（保存、加载消息）
- 记忆持久化（跨实例）
- LangChain save_context 方法
- 消息元数据
- 清空记忆
- 会话隔离
- 消息顺序

**运行方式：**
```bash
python3 tests/test_memory.py
```

### test_document_tools.py
测试文档工具功能，包括：
- 文档读取工具
- 文档分析工具
- 段落编辑工具

**运行方式：**
```bash
python3 tests/test_document_tools.py
```

### test_ai_chat.py
测试 AI 聊天功能。

**运行方式：**
```bash
python3 tests/test_ai_chat.py
```

### test_task_tools.py
测试任务工具功能，包括：
- 任务创建、更新、查询
- 任务状态验证
- 任务优先级排序
- 任务统计
- 会话隔离
- 事件推送

**运行方式：**
```bash
python3 tests/test_task_tools.py
```

### test_knowledge_tools.py
测试知识检索工具功能，包括：
- 基本文档搜索
- 指定文档ID的重点搜索
- 事件推送功能
- 网络搜索功能
- 工具创建函数

**运行方式：**
```bash
python3 tests/test_knowledge_tools.py
```

### test_agent_api.py
测试智能体API服务完整流程，包括：
- 调用智能体执行接口
- WebSocket事件监听
- 所有事件类型的验证
- 文档编辑、知识检索等场景测试

**运行方式：**
```bash
# 确保服务已启动
python3 tests/test_agent_api.py
```

**前置要求：**
- 后端服务运行在 `http://localhost:8000`
- 用户已配置LLM API Key
- 安装依赖：`pip install httpx websockets`

## 运行测试

### 方式1：使用测试脚本（推荐）

```bash
# 运行所有测试
./tests/run_tests.sh

# 运行指定测试（支持多种路径格式）
./tests/run_tests.sh test_memory.py
./tests/run_tests.sh test_task_tools.py
./tests/run_tests.sh tests/test_task_tools.py
./tests/run_tests.sh ./tests/test_task_tools.py
```

### 方式2：手动运行

**重要：所有测试必须在项目根目录运行！**

```bash
# 确保在项目根目录
cd /home/devbox/project

# 设置 Python 路径
export PYTHONPATH=/home/devbox/project:$PYTHONPATH

# 运行单个测试
python3 tests/test_memory.py
python3 tests/test_document_tools.py
python3 tests/test_ai_chat.py

# 批量运行所有测试
for test in tests/test_*.py; do
    echo "=========================================="
    echo "运行 $test"
    echo "=========================================="
    python3 "$test"
    echo ""
done
```

### 方式3：使用 pytest（如果已安装）

```bash
cd /home/devbox/project
export PYTHONPATH=/home/devbox/project:$PYTHONPATH
pytest tests/ -v
```

## 注意事项

1. **必须在项目根目录运行**：测试文件使用相对导入（`from app.xxx import ...`），需要在项目根目录执行
2. **数据库连接**：部分测试会创建和清理测试数据，确保数据库连接正常
3. **测试环境**：测试会使用真实的数据库，建议在测试环境中运行
4. **Python 路径**：如果遇到 `ModuleNotFoundError: No module named 'app'`，请确保：
   - 在项目根目录运行
   - 或者设置 `PYTHONPATH=/home/devbox/project:$PYTHONPATH`

