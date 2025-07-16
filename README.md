# PoeChat Saver

一个用于保存 Poe.com 分享对话的工具，将对话内容转换为 Markdown 格式保存到本地。

## 功能特性

- 🌐 支持解析 Poe.com 分享链接 (`https://poe.com/s/[ID]`)
- 📄 将对话转换为格式化的 Markdown 文档
- 🤖 自动识别 AI 模型名称和对话参与者
- 📊 提取对话元数据（来源、时间、消息统计等）
- 🔄 支持批量处理多个对话链接
- 📁 智能文件命名和去重
- 🎨 代码块和格式化内容的正确处理
- ⚡ 重试机制和错误处理

## 安装

### 方法一：直接安装（推荐）

```bash
# 克隆项目
git clone <repository-url>
cd poechatsaver

# 安装依赖
pip install -r requirements.txt

# 安装工具（可选，用于全局命令）
pip install -e .
```

### 方法二：虚拟环境安装

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 使用方法

### 基础用法

```bash
# 保存单个对话
python -m src.cli "https://poe.com/s/vtYxbVcTZH5pVoi166Lr"

# 指定输出文件名
python -m src.cli "https://poe.com/s/vtYxbVcTZH5pVoi166Lr" -o "我的对话.md"

# 指定输出目录
python -m src.cli "https://poe.com/s/vtYxbVcTZH5pVoi166Lr" -d "./我的对话收藏/"
```

### 批量处理

```bash
# 创建包含多个 URL 的文件
echo "https://poe.com/s/vtYxbVcTZH5pVoi166Lr" > urls.txt
echo "https://poe.com/s/另一个ID" >> urls.txt

# 批量处理
python -m src.cli urls.txt --batch -d "./conversations/"
```

### 高级选项

```bash
# 详细输出模式
python -m src.cli "https://poe.com/s/vtYxbVcTZH5pVoi166Lr" --verbose

# 不包含元数据
python -m src.cli "https://poe.com/s/vtYxbVcTZH5pVoi166Lr" --no-metadata

# 不包含页脚
python -m src.cli "https://poe.com/s/vtYxbVcTZH5pVoi166Lr" --no-footer

# 自定义超时和重试
python -m src.cli "https://poe.com/s/vtYxbVcTZH5pVoi166Lr" --timeout 60 --retries 5 --delay 2.0
```

### URL 验证

```bash
# 验证 URL 有效性（不下载）
python -m src.cli validate "https://poe.com/s/vtYxbVcTZH5pVoi166Lr"
```

## 输出格式

生成的 Markdown 文件包含以下结构：

```markdown
# 对话标题

**来源**: https://poe.com/s/vtYxbVcTZH5pVoi166Lr
**AI模型**: Claude-2-100k-Old
**对话ID**: vtYxbVcTZH5pVoi166Lr
**导出时间**: 2024年1月15日 14:30:25
**消息数量**: 8 (4 用户, 4 AI)

---

## 对话内容

### 👤 用户
用户的问题或消息内容

### 🤖 Claude-2-100k-Old
AI的回复内容，包括：
- 格式化的文本
- 代码块
- 列表和引用

### 👤 用户
后续的用户消息

### 🤖 Claude-2-100k-Old
后续的AI回复

---

*本对话由 PoeChat Saver 工具导出*
*原始链接: https://poe.com/s/vtYxbVcTZH5pVoi166Lr*
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `INPUT_SOURCE` | Poe 分享 URL 或包含 URLs 的文件 | 必需 |
| `-o, --output` | 输出文件路径（单个 URL 时） | 自动生成 |
| `-d, --directory` | 输出目录 | `./conversations` |
| `--batch` | 批量处理模式 | `False` |
| `--verbose, -v` | 详细输出 | `False` |
| `--no-metadata` | 不包含元数据 | `False` |
| `--no-footer` | 不包含页脚 | `False` |
| `--timeout` | 请求超时时间（秒） | `30` |
| `--retries` | 最大重试次数 | `3` |
| `--delay` | 请求间隔（秒） | `1.0` |

## 技术实现

### 项目结构

```
poechatsaver/
├── src/
│   ├── __init__.py         # 包初始化
│   ├── scraper.py          # 网页抓取
│   ├── parser.py           # 内容解析
│   ├── converter.py        # Markdown转换
│   ├── utils.py           # 工具函数
│   └── cli.py             # 命令行接口
├── tests/                  # 测试文件
├── examples/              # 示例输出
├── requirements.txt       # 依赖管理
├── setup.py              # 安装配置
├── DESIGN.md             # 设计文档
└── README.md             # 使用说明
```

### 核心组件

1. **PoePageScraper**: 负责网页抓取和 HTML 获取
2. **ConversationParser**: 解析对话内容和元数据
3. **MarkdownConverter**: 转换为 Markdown 格式
4. **CLI**: 命令行界面和用户交互

## 故障排除

### 常见问题

1. **URL 验证失败**
   - 确保 URL 格式正确：`https://poe.com/s/[ID]`
   - 检查网络连接

2. **抓取失败**
   - 增加超时时间：`--timeout 60`
   - 增加重试次数：`--retries 5`
   - 检查是否被反爬虫机制拦截

3. **解析错误**
   - 使用 `--verbose` 查看详细错误信息
   - 检查 Poe 页面结构是否发生变化

4. **文件保存失败**
   - 检查输出目录权限
   - 确保有足够的磁盘空间

### 调试模式

```bash
# 启用详细日志
python -m src.cli "https://poe.com/s/vtYxbVcTZH5pVoi166Lr" --verbose

# 只验证 URL 而不下载
python -m src.cli validate "https://poe.com/s/vtYxbVcTZH5pVoi166Lr"
```

## 注意事项

1. **合规使用**: 请遵守 Poe.com 的服务条款和使用政策
2. **频率限制**: 工具内置了请求间隔，避免对服务器造成压力
3. **数据准确性**: 解析结果可能受页面结构变化影响
4. **隐私保护**: 仅保存公开分享的对话内容

## 更新日志

### v1.0.0
- 初始版本发布
- 支持基础对话抓取和转换
- 实现批量处理功能
- 添加详细的错误处理

## 贡献指南

欢迎提交 Issue 和 Pull Request 来改进项目！

## 许可证

MIT License

---

**开发状态**: 稳定版本  
**维护状态**: 积极维护  
**Python 版本**: 3.8+
