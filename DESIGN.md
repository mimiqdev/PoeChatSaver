# Poe对话保存工具 - 设计与开发文档

## 项目概述

**项目名称**: PoeChat Saver  
**目标**: 解析Poe.com分享的对话网页，将对话内容提取并保存为markdown格式  
**版本**: 1.0.0  

## 需求分析

### 核心功能需求

1. **网页解析功能**
   - 支持解析Poe.com分享链接 (格式: `https://poe.com/s/[ID]`)
   - 提取对话参与者信息（用户、AI模型名称）
   - 解析对话内容（包括文本、代码块、格式化内容）
   - 获取对话标题和时间戳（如可用）

2. **内容提取功能**
   - 识别用户消息 vs AI回复
   - 保持消息的时间顺序
   - 处理特殊格式内容（代码块、引用、列表等）
   - 处理多媒体内容引用

3. **Markdown转换功能**
   - 生成结构化的markdown文档
   - 清晰标识发言者
   - 保持原有格式（代码高亮、引用等）
   - 添加元数据信息

4. **文件保存功能**
   - 支持自定义文件名
   - 支持批量处理多个链接
   - 生成唯一文件名避免冲突

### 非功能性需求

1. **易用性**: 简单的命令行界面
2. **稳定性**: 错误处理和异常捕获
3. **扩展性**: 模块化设计，便于后续功能扩展
4. **性能**: 支持并发处理多个链接

## 技术方案

### 技术栈选择

- **语言**: Python 3.8+
- **核心库**:
  - `requests` - HTTP请求
  - `beautifulsoup4` - HTML解析
  - `markdownify` - HTML到Markdown转换
  - `click` - 命令行界面
  - `urllib.parse` - URL处理

### 架构设计

```
poechatsaver/
├── src/
│   ├── __init__.py
│   ├── scraper.py          # 网页抓取和解析
│   ├── parser.py           # 对话内容解析
│   ├── converter.py        # Markdown转换
│   ├── utils.py           # 工具函数
│   └── cli.py             # 命令行界面
├── tests/
│   ├── __init__.py
│   ├── test_scraper.py
│   ├── test_parser.py
│   └── test_converter.py
├── examples/              # 示例输出文件
├── requirements.txt
├── setup.py
├── README.md
└── DESIGN.md
```

### 核心模块设计

#### 1. Scraper模块 (`scraper.py`)
```python
class PoePageScraper:
    def fetch_page(self, url: str) -> str
    def validate_url(self, url: str) -> bool
    def extract_raw_html(self, html: str) -> BeautifulSoup
```

#### 2. Parser模块 (`parser.py`)
```python
class ConversationParser:
    def parse_conversation(self, soup: BeautifulSoup) -> ConversationData
    def extract_messages(self, soup: BeautifulSoup) -> List[Message]
    def extract_metadata(self, soup: BeautifulSoup) -> Dict
    
class Message:
    sender: str          # 发送者（用户名或AI模型名）
    content: str         # 消息内容
    timestamp: str       # 时间戳（如可用）
    message_type: str    # 'user' 或 'bot'
```

#### 3. Converter模块 (`converter.py`)
```python
class MarkdownConverter:
    def convert_conversation(self, conversation: ConversationData) -> str
    def format_message(self, message: Message) -> str
    def add_metadata_header(self, metadata: Dict) -> str
```

## 实现计划

### 第一阶段：核心功能开发（预估3-4天）

1. **Day 1**: 环境搭建 + Scraper模块
   - 项目结构创建
   - 依赖管理设置
   - 基础网页抓取功能
   - URL验证和错误处理

2. **Day 2**: Parser模块开发
   - HTML结构分析
   - 对话内容提取逻辑
   - 消息分类和排序

3. **Day 3**: Converter模块开发
   - Markdown格式化逻辑
   - 特殊内容处理（代码块、引用等）
   - 元数据生成

4. **Day 4**: CLI界面 + 测试
   - 命令行参数设计
   - 基础功能测试
   - 错误处理完善

### 第二阶段：功能完善（预估2-3天）

1. **批量处理功能**
2. **输出格式优化**
3. **性能优化**
4. **文档完善**

## 输出格式设计

### Markdown文件结构

```markdown
# [对话标题]

**来源**: [Poe分享链接]  
**AI模型**: [模型名称]  
**导出时间**: [时间戳]  

---

## 对话内容

### 👤 用户
[用户消息内容]

### 🤖 [AI模型名称]
[AI回复内容]

### 👤 用户
[后续用户消息]

### 🤖 [AI模型名称]
[后续AI回复]

---

*本对话由 PoeChat Saver 工具导出*
```

## 使用方式设计

### 命令行界面

```bash
# 基础用法
poesaver "https://poe.com/s/vtYxbVcTZH5pVoi166Lr"

# 指定输出文件名
poesaver "https://poe.com/s/vtYxbVcTZH5pVoi166Lr" -o "my_conversation.md"

# 批量处理
poesaver urls.txt -d ./conversations/

# 详细输出
poesaver "https://poe.com/s/vtYxbVcTZH5pVoi166Lr" --verbose
```

## 技术挑战与解决方案

### 1. 反爬虫机制
- **挑战**: Poe可能有反爬虫保护
- **解决方案**: 
  - 设置合理的User-Agent
  - 添加请求间隔
  - 实现重试机制

### 2. 动态内容加载
- **挑战**: 页面可能使用JavaScript动态加载内容
- **解决方案**: 
  - 优先尝试静态HTML解析
  - 必要时集成Selenium

### 3. 内容格式复杂性
- **挑战**: 对话可能包含复杂的HTML格式
- **解决方案**: 
  - 详细的HTML结构分析
  - 分类处理不同类型的内容

## 后续扩展计划

1. **GUI界面**: 使用tkinter或PyQt创建图形界面
2. **多格式导出**: 支持导出为PDF、DOCX等格式
3. **云端集成**: 支持直接保存到云盘
4. **对话搜索**: 本地对话内容搜索功能
5. **统计分析**: 对话数据统计和可视化

---

**开发时间预估**: 5-7天  
**维护难度**: 中等（主要受Poe网站结构变化影响）  
**扩展性**: 高（模块化设计便于功能扩展） 