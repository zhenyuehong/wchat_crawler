# -*- coding: utf-8 -*-
"""
Edge 浏览器驱动工具函数 (备选方案)
"""

import os
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service

def setup_edge_driver(headless=False, window_size=(1280, 720)):
    """设置Edge浏览器驱动（备选方案）"""
    try:
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
        driver.set_page_load_timeout(60)

        # 移除 navigator.webdriver 属性以避免被检测
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        logging.info("Edge 驱动创建成功")
        return driver

    except Exception as e:
        logging.error(f"设置 Edge 驱动失败: {e}")
        raise

def test_edge_driver():
    """测试 Edge 驱动"""
    try:
        print("测试 Edge 浏览器驱动...")
        driver = setup_edge_driver(headless=True)
        driver.get("https://www.baidu.com")
        title = driver.title
        print(f"Edge 测试成功，页面标题: {title}")
        driver.quit()
        return True
    except Exception as e:
        print(f"Edge 测试失败: {e}")
        return False

if __name__ == "__main__":
    test_edge_driver()