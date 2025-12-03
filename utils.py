# -*- coding: utf-8 -*-
"""
微信公众号专辑文章抓取脚本工具函数
"""

import os
import json
import re
import time
import logging
import hashlib
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from config import (get_random_user_agent, get_random_delay, SELECTORS,
                   PAGE_LOAD_TIMEOUT, ELEMENT_WAIT_TIMEOUT, MAX_RETRY_TIMES,
                   RETRY_DELAY, get_article_file_path)

def setup_driver(headless=False, window_size=(1280, 720)):
    """设置浏览器驱动（优先Chrome，失败时使用Edge）"""
    import time
    driver = None
    last_error = None

    # 记录开始时间
    start_time = time.time()
    logging.info("=" * 50)
    logging.info("开始设置浏览器驱动...")

    # 首先尝试 Chrome 浏览器
    try:
        logging.info("尝试创建 Chrome 驱动...")
        chrome_start = time.time()
        driver = _setup_chrome_driver(headless, window_size)
        chrome_elapsed = time.time() - chrome_start
        logging.info(f"Chrome 驱动创建成功 (耗时: {chrome_elapsed:.1f}秒)")
        return driver

    except Exception as chrome_error:
        chrome_elapsed = time.time() - start_time
        last_error = chrome_error
        logging.warning(f"Chrome 驱动创建失败 (耗时: {chrome_elapsed:.1f}秒): {chrome_error}")

        # Chrome 失败时，尝试 Edge 浏览器作为备选
        try:
            logging.info("尝试创建 Edge 驱动作为备选...")
            edge_start = time.time()
            driver = _setup_edge_driver(headless, window_size)
            edge_elapsed = time.time() - edge_start
            logging.info(f"Edge 驱动创建成功（作为 Chrome 的备选方案） (耗时: {edge_elapsed:.1f}秒)")
            return driver

        except Exception as edge_error:
            total_elapsed = time.time() - start_time
            last_error = edge_error
            logging.error(f"Edge 驱动也创建失败 (总耗时: {total_elapsed:.1f}秒): {edge_error}")

            # 提供详细的错误信息和解决方案
            logging.error("=" * 50)
            logging.error("浏览器驱动创建失败，请尝试以下解决方案:")
            logging.error("1. 确保 Chrome 或 Edge 浏览器已正确安装")
            logging.error("2. 检查系统是否支持图形界面（headless模式可能需要X11）")
            logging.error("3. 更新 Selenium 和 webdriver-manager:")
            logging.error("   pip install --upgrade selenium webdriver-manager")
            logging.error("4. 手动下载 ChromeDriver: https://chromedriver.chromium.org/")
            logging.error("5. 将 ChromeDriver.exe 放到系统 PATH 或当前目录")
            logging.error("6. 如果在网络受限环境中，确保网络连接正常")
            logging.error("=" * 50)

            raise last_error

def _setup_chrome_driver(headless=False, window_size=(1280, 720)):
    """设置Chrome浏览器驱动"""
    from selenium.webdriver.chrome.service import Service
    import threading
    import queue

    chrome_options = Options()

    # 基础配置
    chrome_options.add_argument(f'user-agent={get_random_user_agent()}')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--allow-running-insecure-content')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # 优化Chrome启动性能的额外参数
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-plugins')
    chrome_options.add_argument('--disable-default-apps')
    chrome_options.add_argument('--disable-translate')
    chrome_options.add_argument('--disable-sync')
    chrome_options.add_argument('--no-first-run')
    chrome_options.add_argument('--disable-background-timer-throttling')
    chrome_options.add_argument('--disable-backgrounding-occluded-windows')
    chrome_options.add_argument('--disable-renderer-backgrounding')
    chrome_options.add_argument('--disable-features=TranslateUI')
    chrome_options.add_argument('--disable-ipc-flooding-protection')
    chrome_options.add_argument('--password-store=basic')

    if headless:
        chrome_options.add_argument('--headless=new')  # 使用新的 headless 模式

    # 设置窗口大小
    chrome_options.add_argument(f'--window-size={window_size[0]},{window_size[1]}')

    # 禁用图片加载以提高速度（可选）
    prefs = {
        'profile.managed_default_content_settings.images': 2,
        'profile.managed_default_content_settings.javascript': 1
    }
    chrome_options.add_experimental_option('prefs', prefs)

    # 检查Chrome浏览器路径
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ]

    chrome_path = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_path = path
            break

    if chrome_path:
        chrome_options.binary_location = chrome_path
        logging.info(f"使用 Chrome 路径: {chrome_path}")
    else:
        raise Exception(f"未找到Chrome浏览器，请检查以下路径:\n{chr(10).join(chrome_paths)}")

    # 尝试多种方式创建驱动（带超时控制）
    driver = None
    last_error = None

    # 方法1: 使用 Selenium 4.38.0 的内置驱动管理（带超时）
    def create_driver_with_selenium():
        return webdriver.Chrome(options=chrome_options)

    try:
        logging.info("尝试创建 Chrome 驱动（Selenium 内置）...")
        # 使用线程和队列来实现超时控制
        result_queue = queue.Queue()
        worker_thread = threading.Thread(
            target=lambda: result_queue.put(('success', create_driver_with_selenium())),
            daemon=True
        )
        worker_thread.start()
        worker_thread.join(timeout=15)  # 15秒超时

        if worker_thread.is_alive():
            raise Exception("Chrome驱动创建超时（15秒）")

        try:
            status, result = result_queue.get_nowait()
            if status == 'success':
                driver = result
                logging.info("Chrome 方法1: Selenium 内置驱动管理成功")
        except queue.Empty:
            raise Exception("Chrome驱动创建失败")

    except Exception as e1:
        last_error = e1
        logging.warning(f"Chrome 方法1失败: {e1}")

        # 方法2: 尝试使用 webdriver-manager（仅当模块存在时）
        try:
            from webdriver_manager.chrome import ChromeDriverManager
        except ImportError:
            logging.info("webdriver-manager 模块未安装，跳过方法2")
        else:
            def create_driver_with_manager():
                service = Service(ChromeDriverManager().install())
                return webdriver.Chrome(service=service, options=chrome_options)

            try:
                logging.info("尝试 webdriver-manager 方式...")
                result_queue = queue.Queue()
                worker_thread = threading.Thread(
                    target=lambda: result_queue.put(('success', create_driver_with_manager())),
                    daemon=True
                )
                worker_thread.start()
                worker_thread.join(timeout=30)  # 30秒超时（webdriver-manager需要下载时间）

                if worker_thread.is_alive():
                    raise Exception("webdriver-manager 超时（30秒）")

                try:
                    status, result = result_queue.get_nowait()
                    if status == 'success':
                        driver = result
                        logging.info("Chrome 方法2: webdriver-manager 成功")
                except queue.Empty:
                    raise Exception("webdriver-manager 创建失败")

            except Exception as e2:
                logging.warning(f"Chrome 方法2失败: {e2}")
                last_error = e2

    # 如果所有方法都失败，抛出最后的错误
    if driver is None:
        raise last_error if last_error else Exception("无法创建Chrome驱动")

    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

    # 移除 navigator.webdriver 属性以避免被检测
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver

def _setup_edge_driver(headless=False, window_size=(1280, 720)):
    """设置Edge浏览器驱动（备选方案）"""
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.edge.service import Service

    edge_options = EdgeOptions()

    # 基础配置
    edge_options.add_argument('--no-sandbox')
    edge_options.add_argument('--disable-dev-shm-usage')
    edge_options.add_argument('--disable-gpu')
    edge_options.add_argument('--disable-web-security')
    edge_options.add_argument('--allow-running-insecure-content')
    edge_options.add_argument('--disable-blink-features=AutomationControlled')
    edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    edge_options.add_experimental_option('useAutomationExtension', False)

    if headless:
        edge_options.add_argument('--headless')

    # 设置窗口大小
    edge_options.add_argument(f'--window-size={window_size[0]},{window_size[1]}')

    # 禁用图片加载以提高速度（可选）
    prefs = {
        'profile.managed_default_content_settings.images': 2,
        'profile.managed_default_content_settings.javascript': 1
    }
    edge_options.add_experimental_option('prefs', prefs)

    # 创建 Edge 驱动（使用内置驱动管理）
    driver = webdriver.Edge(options=edge_options)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

    # 移除 navigator.webdriver 属性以避免被检测
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver

def wait_for_element(driver, selector, timeout=ELEMENT_WAIT_TIMEOUT):
    """等待元素出现"""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        return element
    except TimeoutException:
        logging.warning(f"等待元素超时: {selector}")
        return None

def scroll_to_bottom(driver, pause_time=2):
    """滚动到页面底部"""
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        # 滚动到底部
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # 等待页面加载
        time.sleep(pause_time)

        # 计算新的滚动高度
        new_height = driver.execute_script("return document.body.scrollHeight")

        # 如果页面高度没有变化，说明已经到底了
        if new_height == last_height:
            break

        last_height = new_height

def clean_filename(filename):
    """清理文件名，移除非法字符"""
    # 移除或替换非法字符
    illegal_chars = ['<', '>', ':', '"', '|', '?', '*', '/', '\\']
    clean_name = filename

    for char in illegal_chars:
        clean_name = clean_name.replace(char, '_')

    # 移除多余的空格和下划线
    clean_name = re.sub(r'[_\s]+', '_', clean_name)
    clean_name = clean_name.strip('_')

    # 限制长度
    if len(clean_name) > 100:
        clean_name = clean_name[:100]

    return clean_name

def extract_title_from_preview(preview_text):
    """从预览文本中提取标题"""
    if not preview_text:
        return "未知标题"

    # 取前30个字符作为标题
    title = preview_text[:30].strip()

    # 移除换行符和多余空格
    title = re.sub(r'[\n\r]+', ' ', title)
    title = re.sub(r'\s+', ' ', title)

    # 如果标题以数字开头，可能是序号，保留
    if re.match(r'^\d+[、\s.]', title):
        pass

    return title if title else "未知标题"

def save_article_content(index, title, content, output_dir, album_title=None):
    """保存文章内容到markdown文件"""
    try:
        # 清理标题和专辑名称作为文件名
        clean_title = clean_filename(title)

        # 如果提供了专辑标题，使用专辑名称+编号+标题格式
        if album_title:
            clean_album_title = clean_filename(album_title)
            filename = f"{clean_album_title}_{index:03d}_{clean_title}.md"
        else:
            filename = f"{index}_{clean_title}.md"

        file_path = os.path.join(output_dir, filename)

        # 确保目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 保存内容（只保存正文，不包含标题等元数据）
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content.strip())

        logging.info(f"文章保存成功: {filename}")
        return file_path

    except Exception as e:
        logging.error(f"保存文章失败: {title}, 错误: {e}")
        return None

def load_json_state(json_file):
    """加载JSON状态文件"""
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"加载JSON文件失败: {e}")
            return None
    return None

def load_date_counter(output_dir, album_title):
    """
    加载或创建日期计数器文件

    Args:
        output_dir (str): 输出目录
        album_title (str): 专辑标题

    Returns:
        dict: 日期计数器字典 {日期: 计数}
    """
    counter_file = os.path.join(output_dir, f"{clean_filename(album_title)}_date_counter.json")

    if os.path.exists(counter_file):
        try:
            with open(counter_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass

    return {}

def save_date_counter(output_dir, album_title, counter_data):
    """
    保存日期计数器文件

    Args:
        output_dir (str): 输出目录
        album_title (str): 专辑标题
        counter_data (dict): 日期计数器字典
    """
    counter_file = os.path.join(output_dir, f"{clean_filename(album_title)}_date_counter.json")

    try:
        with open(counter_file, 'w', encoding='utf-8') as f:
            json.dump(counter_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.warning(f"保存日期计数器失败: {e}")

def increment_date_counter(counter_data, publish_date):
    """
    递增日期计数器并返回应使用的编号

    Args:
        counter_data (dict): 日期计数器字典
        publish_date (str): 发布日期，格式如 "2024-01-15"

    Returns:
        tuple: (计数, 是否需要编号, 编号数字)
    """
    count = counter_data.get(publish_date, 0)
    count += 1
    counter_data[publish_date] = count

    # 第1篇文章不需要编号，第2篇开始需要编号
    need_suffix = count > 1
    suffix_number = count if need_suffix else None

    return count, need_suffix, suffix_number

def save_json_state(data, json_file):
    """保存JSON状态文件"""
    try:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logging.info(f"JSON状态文件保存成功: {json_file}")
    except Exception as e:
        logging.error(f"保存JSON文件失败: {e}")

def retry_operation(func, max_retries=MAX_RETRY_TIMES, delay=RETRY_DELAY):
    """重试装饰器"""
    def wrapper(*args, **kwargs):
        last_exception = None

        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logging.warning(f"操作失败，第{attempt + 1}次重试: {e}")
                    time.sleep(delay)
                else:
                    logging.error(f"操作失败，已达到最大重试次数: {e}")

        raise last_exception

    return wrapper

def setup_logging(log_level='INFO', log_file=None, error_log_file=None):
    """设置日志配置"""
    # 创建logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))

    # 清除已有的handlers
    logger.handlers.clear()

    # 设置格式
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 控制台handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件handler
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # 错误日志handler
    if error_log_file:
        os.makedirs(os.path.dirname(error_log_file), exist_ok=True)
        error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)

def validate_url(url):
    """验证URL格式"""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None

def get_article_status(status='pending'):
    """获取文章状态字典"""
    return {
        'status': status,
        'file_path': None,
        'error_message': None,
        'processed_time': None,
        'retry_count': 0
    }

def update_article_status(articles_data, index, status=None, file_path=None, error_message=None):
    """更新文章状态"""
    if index < len(articles_data['articles']):
        article = articles_data['articles'][index]

        if status:
            article['status'] = status
        if file_path:
            article['file_path'] = file_path
        if error_message:
            article['error_message'] = error_message

        article['processed_time'] = datetime.now().isoformat()

        # 更新统计信息
        completed_count = sum(1 for a in articles_data['articles'] if a['status'] == 'completed')
        failed_count = sum(1 for a in articles_data['articles'] if a['status'] == 'failed')
        pending_count = sum(1 for a in articles_data['articles'] if a['status'] == 'pending')

        articles_data['processed_count'] = completed_count
        articles_data['failed_count'] = failed_count
        articles_data['pending_count'] = pending_count

def format_progress_bar(current, total, prefix='', suffix='', length=50):
    """格式化进度条"""
    percent = ("{0:.1f}").format(100 * (current / float(total)))
    filled_length = int(length * current // total)
    bar = '█' * filled_length + '-' * (length - filled_length)
    return f'{prefix} |{bar}| {percent}% {suffix}'

def extract_url_hash(url):
    """从URL提取唯一标识"""
    if not url:
        return ""

    # 提取URL中的关键部分（去除参数和hash）
    import re
    url_pattern = r'https?://mp\.weixin\.qq\.com/s\?.*?(sn=[^&#]+)'
    match = re.search(url_pattern, url)

    if match:
        key_part = match.group(1)  # 使用sn参数作为唯一标识
    else:
        # 如果没有sn参数，使用整个URL的MD5哈希
        key_part = hashlib.md5(url.encode()).hexdigest()[:8]

    return key_part

def extract_publish_time_from_article(driver):
    """
    从微信文章页面提取发布时间

    Args:
        driver: Selenium WebDriver实例

    Returns:
        str: 发布时间字符串，格式如 "2024-01-15 10:30:00" 或 None
    """
    try:
        # 微信文章发布时间的常见选择器
        time_selectors = [
            '#publish_time',           # 常见的发布时间元素
            '.rich_media_meta.rich_media_meta_text', # 包含时间的元信息区域
            '#js_content .rich_media_meta', # 内容区域的时间信息
            '.rich_media_meta_list',   # 时间列表
            'span[id*="publish_time"]',  # 包含publish_time的span元素
            'em[id*="publish_time"]',     # 包含publish_time的em元素
        ]

        for selector in time_selectors:
            try:
                time_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in time_elements:
                    text = element.text.strip()
                    if text and any(char in text for char in ['年', '月', '日', '-', ':']):
                        # 尝试解析时间文本
                        parsed_time = parse_wechat_time_text(text)
                        if parsed_time:
                            return parsed_time
            except:
                continue

        # 如果上述方法都失败，尝试从页面源码中查找时间信息
        page_source = driver.page_source
        import re

        # 查找常见的时间格式
        time_patterns = [
            r'(\d{4}年\d{1,2}月\d{1,2}日\s*\d{1,2}:\d{2})',
            r'(\d{4}-\d{1,2}-\d{1,2}\s*\d{1,2}:\d{2})',
            r'"ct":"(\d+)"',  # 微信文章中的时间戳
            r'time.*?(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})',
        ]

        for pattern in time_patterns:
            match = re.search(pattern, page_source)
            if match:
                time_text = match.group(1)
                parsed_time = parse_wechat_time_text(time_text)
                if parsed_time:
                    return parsed_time

        return None

    except Exception as e:
        logging.warning(f"提取发布时间失败: {e}")
        return None

def parse_wechat_time_text(time_text):
    """
    解析微信文章的时间文本为标准格式

    Args:
        time_text (str): 时间文本

    Returns:
        str: 标准格式的时间字符串，如 "2024-01-15 10:30:00"
    """
    import re
    from datetime import datetime

    # 清理时间文本
    time_text = time_text.strip()

    # 多种时间格式的正则表达式
    patterns = [
        # 2024年1月15日 10:30
        r'(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{2})',
        # 2024-01-15 10:30
        r'(\d{4})-(\d{1,2})-(\d{1,2})\s*(\d{1,2}):(\d{2})',
        # 时间戳格式
        r'^(\d{10,13})$'
    ]

    for pattern in patterns:
        match = re.search(pattern, time_text)
        if match:
            try:
                if pattern == patterns[2]:  # 时间戳
                    timestamp = int(match.group(1))
                    if timestamp > 10**12:  # 毫秒时间戳
                        timestamp = timestamp // 1000
                    dt = datetime.fromtimestamp(timestamp)
                else:  # 标准日期格式
                    year, month, day, hour, minute = map(int, match.groups())
                    dt = datetime(year, month, day, hour, minute)

                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                continue

    return None

def generate_smart_filename(url, title, index, album_title=None, publish_time=None,
                          counter_data=None):
    """
    生成智能文件名，使用发布时间日期时间戳 + 自增编号

    Args:
        url (str): 文章URL
        title (str): 文章标题
        index (int): 文章序号
        album_title (str): 专辑标题
        publish_time (str): 发布时间，格式如 "2024-01-15 10:30:00"
        counter_data (dict): 日期计数器字典

    Returns:
        tuple: (文件名, 更新后的计数器数据)
    """
    # 清理专辑标题
    clean_album = clean_filename(album_title) if album_title else "unknown_album"

    # 使用发布时间生成日期时间戳
    if publish_time:
        try:
            from datetime import datetime
            dt = datetime.strptime(publish_time, '%Y-%m-%d %H:%M:%S')
            date_timestamp = dt.strftime('%Y%m%d')  # 20240115格式
            publish_date = dt.strftime('%Y-%m-%d')  # 2024-01-15格式
        except:
            # 如果解析失败，使用当前时间
            from datetime import datetime
            now = datetime.now()
            date_timestamp = now.strftime('%Y%m%d')
            publish_date = now.strftime('%Y-%m-%d')
    else:
        # 如果没有发布时间，使用当前时间
        from datetime import datetime
        now = datetime.now()
        date_timestamp = now.strftime('%Y%m%d')
        publish_date = now.strftime('%Y-%m-%d')

    # 生成基础文件名：{专辑标题}_{发布时间日期戳}
    base_filename = f"{clean_album}_{date_timestamp}"

    # 如果有计数器数据，处理同日多篇文章的编号
    if counter_data is not None:
        count, need_suffix, suffix_number = increment_date_counter(counter_data, publish_date)

        if need_suffix and suffix_number:
            filename = f"{base_filename}_{suffix_number:02d}"
        else:
            filename = base_filename
    else:
        filename = base_filename

    return filename, counter_data

def check_article_exists_by_url(articles_data, url):
    """
    根据URL检查文章是否已经处理过

    Args:
        articles_data (dict): 文章数据
        url (str): 要检查的文章URL

    Returns:
        tuple: (bool, dict) 是否存在，以及对应的文章信息
    """
    if not articles_data or not articles_data.get('articles'):
        return False, None

    target_url_hash = extract_url_hash(url)

    for article in articles_data['articles']:
        if article.get('url') == url:
            return True, article

        # 也检查URL哈希是否匹配（防止URL参数变化）
        if extract_url_hash(article.get('url', '')) == target_url_hash:
            return True, article

    return False, None

def smart_save_article_content(url, title, content, output_dir, album_title=None,
                             index=0, publish_time=None, counter_data=None):
    """
    智能保存文章内容，使用发布时间命名 + 自增编号

    Args:
        url (str): 文章URL
        title (str): 文章标题
        content (str): 文章内容
        output_dir (str): 输出目录
        album_title (str): 专辑标题，可选
        index (int): 文章序号
        publish_time (str): 发布时间，格式如 "2024-01-15 10:30:00"
        counter_data (dict): 日期计数器字典

    Returns:
        tuple: (保存的文件路径, 更新后的计数器数据)，失败返回(None, None)
    """
    try:
        # 生成文件名和更新的计数器
        filename, updated_counter = generate_smart_filename(
            url, title, index, album_title, publish_time, counter_data
        )
        file_path = os.path.join(output_dir, f"{filename}.md")

        # 确保目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 如果文件已存在，跳过保存（基于发布时间去重）
        if os.path.exists(file_path):
            logging.info(f"文章已存在，跳过保存: {os.path.basename(file_path)}")
            return file_path, updated_counter

        # 只保存文章正文内容，不添加元数据
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content.strip())

        logging.info(f"文章保存成功: {os.path.basename(file_path)}")
        return file_path, updated_counter

    except Exception as e:
        logging.error(f"保存文章失败: {title}, 错误: {e}")
        return None, None

def extract_real_title_from_content(content):
    """
    从文章内容中提取真实标题

    Args:
        content (str): 文章内容

    Returns:
        str: 提取的标题，失败返回空字符串
    """
    if not content:
        return ""

    # 尝试多种标题提取策略
    lines = content.split('\n')

    # 策略1: 寻找第一个非空行，通常可能是标题
    for i, line in enumerate(lines):
        line = line.strip()
        if line and len(line) > 5 and len(line) < 100:
            # 排除明显不是标题的行
            if not re.match(r'^[0-9\s,\.，。、]+$', line) and not line.startswith('http'):
                return line

    # 策略2: 寻找包含特殊字符的标题行
    for line in lines[:10]:  # 只检查前10行
        line = line.strip()
        if line and any(char in line for char in '【】「」《》""'''):
            return line

    # 策略3: 返回第一个较长的非空行
    for line in lines[:5]:
        line = line.strip()
        if line and len(line) > 10:
            return line[:50] + "..." if len(line) > 50 else line

    return ""

def update_articles_with_url_matching(articles_data, new_articles):
    """
    将新文章列表与现有数据合并，基于URL进行匹配

    Args:
        articles_data (dict): 现有文章数据
        new_articles (list): 新抓取的文章列表

    Returns:
        dict: 更新后的文章数据
    """
    if not articles_data:
        articles_data = {
            'album_title': '',
            'album_url': '',
            'total_articles': 0,
            'processed_count': 0,
            'failed_count': 0,
            'pending_count': 0,
            'crawl_time': datetime.now().isoformat(),
            'articles': []
        }

    existing_articles = articles_data.get('articles', [])
    updated_articles = []

    # 处理新文章，检查是否已存在
    for new_article in new_articles:
        new_url = new_article.get('url', '')
        exists, existing_article = check_article_exists_by_url(
            {'articles': existing_articles}, new_url
        )

        if exists and existing_article:
            # 保留现有状态，但更新可能的预览内容
            updated_article = existing_article.copy()
            if new_article.get('preview') and not existing_article.get('preview'):
                updated_article['preview'] = new_article['preview']
            updated_articles.append(updated_article)
        else:
            # 新文章
            updated_articles.append(new_article)

    # 保留现有的但不在新列表中的文章（防止丢失数据）
    for existing_article in existing_articles:
        existing_url = existing_article.get('url', '')
        found = any(
            extract_url_hash(art.get('url', '')) == extract_url_hash(existing_url)
            for art in updated_articles
        )
        if not found:
            updated_articles.append(existing_article)

    # 按序号或URL哈希排序
    updated_articles.sort(key=lambda x: (x.get('index', 0), extract_url_hash(x.get('url', ''))))

    # 更新统计信息
    completed_count = sum(1 for a in updated_articles if a.get('status') == 'completed')
    failed_count = sum(1 for a in updated_articles if a.get('status') == 'failed')
    pending_count = sum(1 for a in updated_articles if a.get('status') == 'pending')

    articles_data['articles'] = updated_articles
    articles_data['total_articles'] = len(updated_articles)
    articles_data['processed_count'] = completed_count
    articles_data['failed_count'] = failed_count
    articles_data['pending_count'] = pending_count

    return articles_data