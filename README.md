# 微信公众号专辑文章抓取工具

一个用于抓取微信公众号专辑中所有文章并保存为Markdown文件的Python脚本。

## 功能特点

- ✅ 自动抓取微信公众号专辑的所有文章
- ✅ 支持断点续传，可从中断位置继续处理
- ✅ 智能错误处理，失败文章不影响整体进度
- ✅ 随机延时，模拟真实用户行为
- ✅ 进度显示，实时跟踪处理状态
- ✅ 完整的日志记录和错误追踪

## 安装要求

### 系统要求
- Python 3.8+
- Chrome浏览器
- ChromeDriver（与Chrome版本匹配）

### 快速安装（推荐）

#### Windows用户
```bash
# 方法1：一键安装脚本
install.bat

# 方法2：手动安装
pip install -r requirements.txt
```

#### Linux/macOS用户
```bash
# 安装依赖
pip3 install -r requirements.txt

# 安装Chrome和ChromeDriver（Ubuntu/Debian）
sudo apt install chromium-browser chromium-chromedriver

# macOS使用Homebrew
brew install --cask chromedriver
```

### 手动安装

1. **安装Python 3.8+**
   - Windows: https://www.python.org/downloads/
   - Linux: `sudo apt install python3 python3-pip`
   - macOS: `brew install python3`

2. **安装依赖包**
   ```bash
   pip install selenium>=4.15.0 requests>=2.31.0 beautifulsoup4>=4.12.0
   ```

3. **安装ChromeDriver**
   - 下载：https://chromedriver.chromium.org/
   - 确保版本与Chrome浏览器匹配
   - 添加到系统PATH或使用内置的ChromeDriver（新版Selenium支持）

### 验证安装

运行测试脚本验证环境：
```bash
python quick_test.py
```

如果看到 "SUCCESS: All tests passed!" 说明安装成功。

## 使用方法

### 基本用法

```bash
python crawler.py --url "微信公众号专辑链接"
```

### 完整参数

```bash
python crawler.py \
    --url "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=..." \
    --output "./articles" \
    --delay 15 \
    --headless \
    --retry-failed
```

### 参数说明

| 参数 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `--url` | 是 | - | 微信公众号专辑链接 |
| `--output` | 否 | `./articles` | 文章保存目录 |
| `--delay` | 否 | `15` | 请求间隔时间（秒） |
| `--no-resume` | 否 | `True` | 不从断点继续，重新开始 |
| `--retry-failed` | 否 | `False` | 仅重试失败的文章 |
| `--headless` | 否 | `False` | 无头模式运行（不显示浏览器） |

### 使用示例

#### 1. 基本抓取
```bash
python crawler.py --url "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzkyNjQyOTQzOA==&action=getalbum&album_id=3864942002693373954"
```

#### 2. 指定保存目录和延时
```bash
python crawler.py --url "专辑链接" --output "/path/to/articles" --delay 20
```

#### 3. 无头模式运行（后台运行）
```bash
python crawler.py --url "专辑链接" --headless
```

#### 4. 仅重试失败的文章
```bash
python crawler.py --url "专辑链接" --retry-failed
```

#### 5. 重新开始抓取（忽略断点）
```bash
python crawler.py --url "专辑链接" --no-resume
```

## 输出文件

### 状态文件 (wechat_articles.json)
记录所有文章的处理状态，支持断点续传：
```json
{
  "album_title": "专辑名称",
  "album_url": "专辑链接",
  "total_articles": 263,
  "processed_count": 150,
  "failed_count": 2,
  "pending_count": 111,
  "crawl_time": "2025-11-19T12:00:00",
  "articles": [
    {
      "index": 1,
      "title": "文章标题",
      "url": "文章链接",
      "status": "completed",
      "file_path": "./articles/1_文章标题.md",
      "error_message": null,
      "processed_time": "2025-11-19T12:01:00"
    }
  ]
}
```

### 文章文件 (articles/*.md)
每篇文章保存为单独的Markdown文件，只包含正文内容：
```markdown
文章正文纯文本内容，不包含标题、时间等元数据。
```

### 日志文件 (logs/)
- `crawler.log`: 详细操作日志
- `errors.log`: 错误信息日志

## 项目结构

```
wechat_crawler/
├── crawler.py              # 主程序
├── config.py               # 配置文件
├── utils.py                # 工具函数
├── requirements.txt        # 依赖包
├── README.md              # 使用说明
├── wechat_articles.json    # 文章列表和状态文件
├── articles/              # 文章保存目录
│   ├── 1_文章标题1.md
│   ├── 2_文章标题2.md
│   └── ...
└── logs/                  # 日志目录
    ├── crawler.log
    └── errors.log
```

## 断点续传功能

脚本支持断点续传，具有以下特性：

1. **自动恢复**: 程序中断后重新运行，会自动从上次处理位置继续
2. **失败重试**: 失败的文章会被记录，可以使用 `--retry-failed` 参数重试
3. **状态跟踪**: 实时更新每篇文章的处理状态
4. **数据安全**: 状态信息定期保存，防止数据丢失

## 错误处理

- **网络异常**: 自动重试3次
- **页面加载失败**: 自动重试2次
- **内容提取失败**: 记录并跳过
- **文件保存失败**: 记录并继续处理下一篇

## 配置说明

主要配置在 `config.py` 文件中：

```python
# 延时配置
DEFAULT_DELAY = 15  # 默认延时
DELAY_RANGE = (10, 20)  # 随机延时范围

# 重试配置
MAX_RETRY_TIMES = 3  # 最大重试次数
RETRY_DELAY = 5  # 重试间隔

# 文件配置
MAX_TITLE_LENGTH = 100  # 文件名标题最大长度
```

## 常见问题

### 1. ChromeDriver版本不匹配
**问题**: `selenium.common.exceptions.SessionNotCreatedException`
**解决**: 确保ChromeDriver版本与Chrome浏览器版本匹配

### 2. 网络连接问题
**问题**: 频繁的超时错误
**解决**: 增加 `--delay` 参数值，或检查网络连接

### 3. 文章内容为空
**问题**: 某些文章内容提取为空
**解决**: 这是正常的，脚本会记录失败状态，可以使用 `--retry-failed` 重试

### 4. 权限问题
**问题**: 无法创建目录或文件
**解决**: 确保对输出目录有写入权限

## 注意事项

1. **使用频率**: 请合理使用，避免频繁请求对微信服务器造成压力
2. **版权声明**: 抓取的内容仅用于个人学习，请尊重原作者版权
3. **技术限制**: 微信可能有反爬虫机制，如遇到验证码等请稍后重试
4. **资源占用**: 脚本运行时会占用一定的CPU和内存资源

## 更新日志

### v1.0.0 (2025-11-19)
- 初始版本发布
- 支持专辑文章抓取
- 支持断点续传
- 支持错误重试
- 支持进度显示
