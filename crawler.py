#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号专辑文章抓取脚本主程序
"""

import os
import sys
import json
import time
import argparse
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from config import (BASE_DIR, ARTICLES_DIR, LOGS_DIR, JSON_FILE,
                   DEFAULT_DELAY, get_random_delay, SELECTORS, SCROLL_PAUSE_TIME,
                   HEADLESS, WINDOW_SIZE)
from utils import (setup_driver, setup_logging, load_json_state, save_json_state,
                   validate_url, get_article_status, update_article_status,
                   save_article_content, scroll_to_bottom, clean_filename,
                   extract_title_from_preview, format_progress_bar, extract_url_hash,
                   check_article_exists_by_url, smart_save_article_content,
                   extract_real_title_from_content, update_articles_with_url_matching,
                   extract_publish_time_from_article, parse_wechat_time_text,
                   load_date_counter, save_date_counter)

class WeChatAlbumCrawler:
    """微信公众号专辑文章抓取器"""

    def __init__(self, headless=False, delay=DEFAULT_DELAY):
        """初始化抓取器"""
        self.headless = headless
        self.delay = delay
        self.driver = None
        self.articles_data = None

        # 设置日志
        setup_logging(
            log_level='INFO',
            log_file=os.path.join(LOGS_DIR, "crawler.log"),
            error_log_file=os.path.join(LOGS_DIR, "errors.log")
        )

        logging.info("微信公众号专辑文章抓取器初始化完成")

    def setup_driver(self):
        """设置浏览器驱动"""
        try:
            self.driver = setup_driver(headless=self.headless, window_size=WINDOW_SIZE)
            logging.info("浏览器驱动设置成功")
            return True
        except Exception as e:
            logging.error(f"设置浏览器驱动失败: {e}")
            return False

    def load_album_page(self, album_url):
        """加载专辑页面"""
        try:
            if not validate_url(album_url):
                logging.error(f"无效的URL: {album_url}")
                return False

            logging.info(f"开始加载专辑页面: {album_url}")
            self.driver.get(album_url)

            # 等待页面加载
            time.sleep(3)

            # 检查是否成功加载
            if "mp.weixin.qq.com" not in self.driver.current_url:
                logging.error("页面加载失败，可能被重定向")
                return False

            logging.info("专辑页面加载成功")
            return True

        except Exception as e:
            logging.error(f"加载专辑页面失败: {e}")
            return False

    def extract_album_info(self):
        """提取专辑基本信息"""
        try:
            # 提取专辑标题
            title_element = self.driver.find_element(By.CSS_SELECTOR, "#js_tag_name")
            album_title = title_element.text.strip() if title_element else "未知专辑"

            # 提取文章总数
            desc_element = self.driver.find_element(By.CSS_SELECTOR, "#js_desc_area span")
            total_articles = 0
            if desc_element:
                desc_text = desc_element.text
                # 提取数字，如 "263个内容"
                import re
                match = re.search(r'(\d+)', desc_text)
                if match:
                    total_articles = int(match.group(1))

            return album_title, total_articles

        except Exception as e:
            logging.error(f"提取专辑信息失败: {e}")
            return "未知专辑", 0

    def load_all_articles(self):
        """加载所有文章列表"""
        try:
            logging.info("开始加载所有文章...")

            last_count = 0
            no_change_count = 0
            max_no_change = 3  # 连续3次没有变化就停止

            while no_change_count < max_no_change:
                # 滚动到底部
                scroll_to_bottom(self.driver, SCROLL_PAUSE_TIME)

                # 获取当前文章数量
                articles_container = self.driver.find_element(By.CSS_SELECTOR, SELECTORS['album_container'])
                current_articles = articles_container.find_elements(By.CSS_SELECTOR, SELECTORS['album_items'])
                current_count = len(current_articles)

                logging.info(f"当前已加载 {current_count} 篇文章")

                # 检查是否有变化
                if current_count == last_count:
                    no_change_count += 1
                    logging.info(f"文章数量无变化，计数: {no_change_count}")
                else:
                    no_change_count = 0
                    last_count = current_count

                # 检查是否还有加载更多元素
                try:
                    loading_element = self.driver.find_element(By.CSS_SELECTOR, SELECTORS['loading_element'])
                    if loading_element.is_displayed():
                        logging.info("检测到加载更多元素，继续等待...")
                        time.sleep(2)
                        continue
                except NoSuchElementException:
                    pass

                # 检查是否到达底部
                try:
                    no_more_element = self.driver.find_element(By.CSS_SELECTOR, SELECTORS['no_more_element'])
                    if no_more_element.is_displayed():
                        logging.info("检测到已加载全部文章")
                        break
                except NoSuchElementException:
                    pass

                time.sleep(1)

            final_count = len(self.driver.find_elements(By.CSS_SELECTOR, SELECTORS['album_items']))
            logging.info(f"文章加载完成，共 {final_count} 篇")
            return final_count

        except Exception as e:
            logging.error(f"加载所有文章失败: {e}")
            return 0

    def extract_articles_list(self):
        """提取文章列表，支持URL去重"""
        try:
            new_articles = []

            # 获取所有文章元素
            articles_elements = self.driver.find_elements(By.CSS_SELECTOR, SELECTORS['album_items'])
            logging.info(f"找到 {len(articles_elements)} 个文章元素")

            for index, element in enumerate(articles_elements):
                try:
                    # 提取文章链接
                    article_url = element.get_attribute(SELECTORS['article_link'])
                    if not article_url:
                        continue

                    # 检查文章是否已经存在（基于URL去重）
                    if self.articles_data:
                        exists, existing_article = check_article_exists_by_url(self.articles_data, article_url)
                        if exists:
                            logging.info(f"文章已存在，跳过: {article_url[:50]}...")
                            continue

                    # 提取文章序号
                    article_index = element.get_attribute('data-idx')
                    if article_index:
                        article_index = int(article_index)
                    else:
                        article_index = index + 1

                    # 提取预览内容
                    try:
                        preview_element = element.find_element(By.CSS_SELECTOR, SELECTORS['article_title'])
                        preview_text = preview_element.text.strip()
                    except NoSuchElementException:
                        preview_text = ""

                    # 从预览内容提取标题
                    title = extract_title_from_preview(preview_text)

                    article_info = {
                        'index': article_index,
                        'title': title,
                        'url': article_url,
                        'preview': preview_text[:100] + "..." if len(preview_text) > 100 else preview_text,
                        'status': 'pending',
                        'file_path': None,
                        'error_message': None,
                        'processed_time': None,
                        'retry_count': 0
                    }

                    new_articles.append(article_info)

                except Exception as e:
                    logging.error(f"提取第{index+1}个文章信息失败: {e}")
                    continue

            # 如果有现有数据，进行合并
            if self.articles_data and self.articles_data.get('articles'):
                logging.info(f"合并 {len(new_articles)} 篇新文章到现有数据")
                self.articles_data = update_articles_with_url_matching(self.articles_data, new_articles)
                articles = self.articles_data['articles']
            else:
                articles = new_articles

            # 按序号排序
            articles.sort(key=lambda x: x['index'])

            # 只返回待处理的文章
            pending_articles = [a for a in articles if a['status'] == 'pending']
            logging.info(f"成功提取 {len(articles)} 篇文章，其中 {len(pending_articles)} 篇待处理")
            return articles

        except Exception as e:
            logging.error(f"提取文章列表失败: {e}")
            return []

    def extract_article_content(self, article_url):
        """提取文章正文内容和发布时间"""
        try:
            logging.info(f"开始提取文章内容: {article_url}")

            # 打开新标签页
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])

            # 访问文章页面
            self.driver.get(article_url)

            # 等待页面加载
            time.sleep(3)

            # 提取发布时间
            publish_time = extract_publish_time_from_article(self.driver)
            logging.info(f"提取到发布时间: {publish_time}")

            # 提取文章内容
            content = ""
            try:
                # 尝试不同的内容选择器
                content_selectors = [
                    '#js_content',
                    '.rich_media_content',
                    '.content',
                    '#content'
                ]

                content_element = None
                for selector in content_selectors:
                    try:
                        content_element = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        break
                    except TimeoutException:
                        continue

                if content_element:
                    # 获取纯文本内容
                    content = content_element.text.strip()
                    # 清理内容：去除从"收录于"开始的部分
                    content = self.clean_content(content)
                else:
                    # 如果找不到内容元素，尝试获取整个页面文本
                    content = self.driver.find_element(By.TAG_NAME, 'body').text.strip()
                    # 清理内容：去除从"收录于"开始的部分
                    content = self.clean_content(content)

            except Exception as e:
                logging.error(f"提取文章内容失败: {e}")
                # 备用方案：获取页面文本
                content = self.driver.find_element(By.TAG_NAME, 'body').text.strip()
                # 清理内容：去除从"收录于"开始的部分
                content = self.clean_content(content)

            # 关闭当前标签页，返回主页
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])

            logging.info(f"文章内容提取成功，长度: {len(content)} 字符")
            return content, publish_time

        except Exception as e:
            logging.error(f"提取文章内容异常: {e}")
            # 确保返回主页
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return None, None

    def _check_and_append_new_articles(self, album_url):
        """
        检查并追加新文章到现有JSON文件中
        每次启动时自动执行此功能
        """
        try:
            logging.info("开始检查是否有新文章...")

            # 临时设置驱动（如果还没有设置）
            temp_driver = None
            if not self.driver:
                temp_driver = setup_driver(headless=self.headless, window_size=WINDOW_SIZE)
                self.driver = temp_driver

            # 加载专辑页面
            if not self.load_album_page(album_url):
                logging.warning("无法加载专辑页面进行新文章检测")
                return

            # 加载所有文章
            logging.info("正在加载专辑页面以检测新文章...")
            loaded_count = self.load_all_articles()
            logging.info(f"页面加载完成，共找到 {loaded_count} 篇文章")

            # 提取当前页面的文章列表
            temp_articles_data = self.articles_data.copy() if self.articles_data else {'articles': []}
            temp_articles_data['articles'] = []  # 清空文章列表，重新提取
            self.articles_data = temp_articles_data

            articles = self.extract_articles_list()
            if not articles:
                logging.info("未找到任何文章，无法进行新文章检测")
                return

            # 重新加载原始数据
            original_data = load_json_state(JSON_FILE)
            if not original_data:
                logging.info("未找到原始数据，无法进行新文章检测")
                return

            # 收集现有文章的URL哈希
            existing_urls = set()
            if original_data.get('articles'):
                for article in original_data['articles']:
                    if article.get('url'):
                        existing_urls.add(extract_url_hash(article['url']))

            # 查找新文章
            new_articles = []
            max_existing_index = 0

            # 获取现有最大索引
            if original_data.get('articles'):
                for article in original_data['articles']:
                    if article.get('index', 0) > max_existing_index:
                        max_existing_index = article['index']

            for article in articles:
                article_url_hash = extract_url_hash(article.get('url', ''))
                if article_url_hash not in existing_urls:
                    # 为新文章分配连续的索引号
                    new_article = article.copy()
                    new_article['index'] = max_existing_index + len(new_articles) + 1
                    new_article['status'] = 'pending'
                    new_article['file_path'] = None
                    new_article['error_message'] = None
                    new_article['processed_time'] = None
                    new_article['retry_count'] = 0
                    new_articles.append(new_article)
                    logging.info(f"发现新文章: {article.get('title', '未知标题')[:50]}...")

            if new_articles:
                logging.info(f"发现 {len(new_articles)} 篇新文章，开始追加到JSON文件...")

                # 追加新文章到原始数据
                original_data['articles'].extend(new_articles)

                # 更新统计信息
                original_data['total_articles'] = len(original_data['articles'])
                original_data['pending_count'] = len([a for a in original_data['articles'] if a['status'] == 'pending'])
                original_data['processed_count'] = len([a for a in original_data['articles'] if a['status'] == 'completed'])
                original_data['failed_count'] = len([a for a in original_data['articles'] if a['status'] == 'failed'])
                original_data['crawl_time'] = datetime.now().isoformat()

                # 保存更新后的数据
                save_json_state(original_data, JSON_FILE)

                # 更新当前实例的数据
                self.articles_data = original_data

                logging.info(f"成功追加 {len(new_articles)} 篇新文章到 wechat_articles.json")
                logging.info(f"更新后总文章数: {original_data['total_articles']}")
                logging.info(f"待处理文章数: {original_data['pending_count']}")

                print(f"🔍 发现 {len(new_articles)} 篇新文章已自动追加到JSON文件")
                print(f"📊 当前总文章数: {original_data['total_articles']}")
                print(f"⏳ 待处理文章数: {original_data['pending_count']}")
            else:
                logging.info("未发现新文章，继续使用现有数据")
                print("✅ 未发现新文章，继续使用现有数据")

            # 清理临时驱动
            if temp_driver:
                try:
                    temp_driver.quit()
                except:
                    pass
                self.driver = None

        except Exception as e:
            logging.error(f"检测新文章时出错: {e}")
            print(f"⚠️ 检测新文章时出错，继续使用现有数据: {e}")

            # 确保清理临时驱动
            if 'temp_driver' in locals() and temp_driver:
                try:
                    temp_driver.quit()
                except:
                    pass
                self.driver = None

    def clean_content(self, content):
        """
        清理文章内容，去除从"收录于"开始的部分

        Args:
            content (str): 原始文章内容

        Returns:
            str: 清理后的文章内容
        """
        import re

        if not content:
            return content

        # 查找"收录于"的位置
        pattern = r'\n?收录于'
        match = re.search(pattern, content)

        if match:
            # 保留"收录于"之前的内容
            cleaned_content = content[:match.start()].rstrip()
            return cleaned_content
        else:
            # 如果没有找到"收录于"，返回原内容
            return content

    def process_article(self, article_info, output_dir):
        """处理单个文章，支持智能标题提取和去重"""
        index = article_info['index']
        title = article_info['title']
        url = article_info['url']

        try:
            logging.info(f"开始处理第 {index} 篇文章: {title}")

            # 提取文章内容和发布时间
            content, publish_time = self.extract_article_content(url)
            if not content:
                raise Exception("文章内容为空")

            # 尝试从内容中提取真实标题
            real_title = extract_real_title_from_content(content)
            final_title = real_title if real_title else title

            # 使用智能保存功能（传入发布时间和计数器）
            album_title = self.articles_data.get('album_title') if self.articles_data else None
            file_path, updated_counter = smart_save_article_content(url, final_title, content, output_dir, album_title, index, publish_time, getattr(self, 'date_counter', {}))
            if not file_path:
                raise Exception("保存文章失败")

            # 更新计数器
            if updated_counter:
                self.date_counter.update(updated_counter)
                self._last_updated_counter = updated_counter

            # 更新文章信息中的真实标题
            article_info['title'] = final_title

            # 找到对应的文章索引并更新状态
            article_index = None
            for i, art in enumerate(self.articles_data['articles']):
                if art.get('url') == url or extract_url_hash(art.get('url', '')) == extract_url_hash(url):
                    article_index = i
                    break

            if article_index is not None:
                update_article_status(self.articles_data, article_index, status='completed', file_path=file_path)
            else:
                logging.warning(f"无法找到文章索引: {url}")

            logging.info(f"第 {index} 篇文章处理完成: {final_title}")
            return True

        except Exception as e:
            error_msg = f"处理失败: {e}"
            logging.error(f"第 {index} 篇文章处理失败: {title}, {error_msg}")

            # 找到对应的文章索引并更新状态
            article_index = None
            for i, art in enumerate(self.articles_data['articles']):
                if art.get('url') == url or extract_url_hash(art.get('url', '')) == extract_url_hash(url):
                    article_index = i
                    break

            if article_index is not None:
                update_article_status(self.articles_data, article_index, status='failed', error_message=error_msg)
            else:
                logging.warning(f"无法找到文章索引: {url}")

            return False

    def crawl_album(self, album_url, output_dir=ARTICLES_DIR, resume=True, retry_failed_only=False):
        """抓取专辑文章"""
        try:
            # 加载现有状态
            if resume and os.path.exists(JSON_FILE):
                self.articles_data = load_json_state(JSON_FILE)
                if self.articles_data:
                    logging.info("加载现有状态成功")
                    # 检查是否有新文章需要追加
                    if not retry_failed_only:
                        self._check_and_append_new_articles(album_url)
                else:
                    logging.info("创建新的状态文件")
                    self.articles_data = None

            # 设置输出目录
            os.makedirs(output_dir, exist_ok=True)

            # 加载日期计数器
            album_title = self.articles_data.get('album_title') if self.articles_data else None
            self.date_counter = load_date_counter(output_dir, album_title) if album_title else {}

            # 如果只重试失败的文章，过滤文章列表
            if retry_failed_only and self.articles_data:
                failed_articles = [a for a in self.articles_data['articles'] if a['status'] == 'failed']
                if not failed_articles:
                    logging.info("没有失败的文章需要重试")
                    return True

                # 重置失败文章状态为pending
                for article in failed_articles:
                    article['status'] = 'pending'
                    article['error_message'] = None
                    article['retry_count'] += 1

                logging.info(f"重试 {len(failed_articles)} 篇失败的文章")

            # 如果没有现有数据或不需要恢复，重新抓取
            if not self.articles_data or not resume:
                # 设置驱动
                if not self.setup_driver():
                    return False

                # 加载专辑页面
                if not self.load_album_page(album_url):
                    return False

                # 提取专辑信息
                album_title, total_articles = self.extract_album_info()

                # 加载所有文章
                loaded_count = self.load_all_articles()

                # 提取文章列表
                articles = self.extract_articles_list()

                # 初始化数据结构
                self.articles_data = {
                    'album_title': album_title,
                    'album_url': album_url,
                    'total_articles': len(articles),
                    'processed_count': 0,
                    'failed_count': 0,
                    'pending_count': len(articles),
                    'crawl_time': datetime.now().isoformat(),
                    'articles': articles
                }

                # 保存初始状态
                save_json_state(self.articles_data, JSON_FILE)

            # 设置驱动（如果还没有设置）
            if not self.driver:
                if not self.setup_driver():
                    return False

            # 确保在专辑页面
            if album_url not in self.driver.current_url:
                self.load_album_page(album_url)

            # 处理待处理的文章
            pending_articles = [a for a in self.articles_data['articles'] if a['status'] == 'pending']

            if not pending_articles:
                logging.info("没有待处理的文章")
                return True

            logging.info(f"开始处理 {len(pending_articles)} 篇待处理文章")

            success_count = 0
            for i, article_info in enumerate(pending_articles):
                # 显示进度
                progress = format_progress_bar(
                    i + 1, len(pending_articles),
                    prefix=f"处理进度",
                    suffix=f"{i + 1}/{len(pending_articles)}"
                )
                print(f"\r{progress}", end="", flush=True)

                # 处理文章
                if self.process_article(article_info, output_dir):
                    success_count += 1

                # 保存状态和日期计数器
                save_json_state(self.articles_data, JSON_FILE)
                if album_title:
                    save_date_counter(output_dir, album_title, self.date_counter)

                # 更新计数器（从保存函数获取的更新）
                if hasattr(self, '_last_updated_counter'):
                    self.date_counter.update(self._last_updated_counter)

                # 延时
                if i < len(pending_articles) - 1:  # 不是最后一篇
                    delay = get_random_delay()
                    logging.info(f"等待 {delay:.1f} 秒...")
                    time.sleep(delay)

            print()  # 换行

            # 最终统计
            final_completed = sum(1 for a in self.articles_data['articles'] if a['status'] == 'completed')
            final_failed = sum(1 for a in self.articles_data['articles'] if a['status'] == 'failed')

            logging.info(f"处理完成！成功: {final_completed}, 失败: {final_failed}")
            print(f"\n处理完成！")
            print(f"总文章数: {len(self.articles_data['articles'])}")
            print(f"成功处理: {final_completed}")
            print(f"处理失败: {final_failed}")
            print(f"文章保存在: {output_dir}")

            return final_completed > 0

        except Exception as e:
            logging.error(f"抓取专辑失败: {e}")
            return False

        finally:
            # 关闭浏览器
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='微信公众号专辑文章抓取工具')
    parser.add_argument('--url', required=True, help='微信公众号专辑链接')
    parser.add_argument('--output', default=ARTICLES_DIR, help='文章保存目录')
    parser.add_argument('--delay', type=int, default=DEFAULT_DELAY, help='请求间隔时间（秒）')
    parser.add_argument('--no-resume', action='store_false', dest='resume', help='不从断点继续，重新开始')
    parser.add_argument('--retry-failed', action='store_true', help='仅重试失败的文章')
    parser.add_argument('--headless', action='store_true', help='无头模式运行')

    args = parser.parse_args()

    # 验证URL
    if not validate_url(args.url):
        print("错误：无效的URL")
        return 1

    # 确保目录存在
    os.makedirs(args.output, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)

    # 创建抓取器
    crawler = WeChatAlbumCrawler(headless=args.headless, delay=args.delay)

    # 开始抓取
    try:
        success = crawler.crawl_album(
            album_url=args.url,
            output_dir=args.output,
            resume=args.resume,
            retry_failed_only=args.retry_failed
        )
        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n用户中断操作")
        logging.info("用户中断操作")
        return 1

    except Exception as e:
        print(f"\n程序异常: {e}")
        logging.error(f"程序异常: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())