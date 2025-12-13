# -*- coding: utf-8 -*-
"""
微信公众号专辑文章抓取脚本配置文件
"""

import os
import random

# 基础配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTICLES_DIR = os.path.join(BASE_DIR, "articles")
TOUTIAO_ARTICLES_DIR = os.path.join(BASE_DIR, "toutiao_article")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
JSON_FILE = os.path.join(BASE_DIR, "wechat_articles.json")
TOUTIAO_JSON_FILE = os.path.join(BASE_DIR, "toutiao_articles.json")

# Selenium配置
CHROME_DRIVER_PATH = None  # 如果为None，使用系统PATH中的chromedriver
# HEADLESS = False  # 是否无头模式运行
HEADLESS = True
WINDOW_SIZE = (1280, 720)  # 浏览器窗口大小

# 抓取配置
DEFAULT_DELAY = 5  # 默认延时（秒）
DELAY_RANGE = (2, 5)  # 随机延时范围（秒）
SCROLL_PAUSE_TIME = 2  # 滚动暂停时间（秒）
PAGE_LOAD_TIMEOUT = 30  # 页面加载超时时间（秒）
ELEMENT_WAIT_TIMEOUT = 30  # 元素等待超时时间（秒）

# 重试配置
MAX_RETRY_TIMES = 3  # 最大重试次数
RETRY_DELAY = 5  # 重试间隔时间（秒）

# 文件配置
MAX_TITLE_LENGTH = 100  # 文件名中标题的最大长度
SUPPORTED_EXTENSIONS = ['.md']  # 支持的文件扩展名

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = os.path.join(LOGS_DIR, "crawler.log")
ERROR_LOG_FILE = os.path.join(LOGS_DIR, "errors.log")

# CSS选择器配置
SELECTORS = {
    # 原有页面选择器
    'album_container': '#js_list',
    'album_items': '.album-item',
    'article_link': 'data-link',
    'article_title': '.desc js_content',
    'loading_element': '#js_tag_loading',
    'no_more_element': '#js_tag_no_more_articles',
    'article_content': '#js_content',
    'article_title_full': '#activity-name',

    # 新增新页面的备选选择器
    'alternative': {
        'album_container': '.js_album_list',
        'album_items': '.album__list-item',
        'article_link': '.album__item',
        'article_title': '.album__item-title-wrp a',
        'article_title_text': '.album__item-title-text',  # 新页面中实际的标题文本元素
        'loading_element': '.loading',
        'no_more_element': '.no-more',
        'article_content': '#js_content',
        'article_title_full': '#activity-name'
    },

    # 今日头条选择器
    'toutiao': {
        'user_container': '.profile-tab-feed',
        'article_cards': '.profile-article-card-wrapper',
        'article_link': '.feed-card-article-l .title',
        'article_title': '.feed-card-article-l .title',
        'publish_time': '.feed-card-footer-time-cmp',
        'read_count': '.profile-feed-card-tools-text',
        'article_content': 'article.syl-article-base',
        'article_title_full': 'h1',
        'article_meta': '.article-meta',
        'author_name': '.article-meta .name',
        'loading_more': '.loading-more'  # 加载更多元素
    }
}

# 用户代理配置
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
]

def get_random_user_agent():
    """获取随机用户代理"""
    return random.choice(USER_AGENTS)

def get_random_delay():
    """获取随机延时时间"""
    return random.uniform(DELAY_RANGE[0], DELAY_RANGE[1])

def get_article_file_path(index, title):
    """生成文章文件路径"""
    # 清理文件名中的非法字符
    illegal_chars = ['<', '>', ':', '"', '|', '?', '*', '/', '\\']
    clean_title = title
    for char in illegal_chars:
        clean_title = clean_title.replace(char, '_')

    # 限制标题长度
    if len(clean_title) > MAX_TITLE_LENGTH:
        clean_title = clean_title[:MAX_TITLE_LENGTH]

    filename = f"{index}_{clean_title}.md"
    return os.path.join(ARTICLES_DIR, filename)

def ensure_directories():
    """确保必要的目录存在"""
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    os.makedirs(TOUTIAO_ARTICLES_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)