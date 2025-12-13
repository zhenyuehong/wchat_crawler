#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
今日头条用户主页文章抓取脚本
"""

import os
import sys
import json
import time
import logging
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from config import (BASE_DIR, TOUTIAO_ARTICLES_DIR, LOGS_DIR, TOUTIAO_JSON_FILE,
                   DEFAULT_DELAY, get_random_delay, SELECTORS, SCROLL_PAUSE_TIME,
                   HEADLESS, WINDOW_SIZE, USER_AGENTS, get_random_user_agent)
from utils import (setup_driver, setup_logging, load_json_state, save_json_state,
                   validate_url, save_article_content, clean_filename,
                   format_progress_bar)

class ToutiaoUserCrawler:
    """今日头条用户主页文章抓取器"""

    def __init__(self, headless=False, delay=DEFAULT_DELAY):
        """初始化抓取器"""
        self.headless = headless
        self.delay = delay
        self.driver = None
        self.articles_data = None

        # 设置日志
        setup_logging(
            log_level='INFO',
            log_file=os.path.join(LOGS_DIR, "toutiao_crawler.log"),
            error_log_file=os.path.join(LOGS_DIR, "toutiao_errors.log")
        )

        logging.info("今日头条用户主页文章抓取器初始化完成")

    def setup_driver(self):
        """设置浏览器驱动"""
        try:
            self.driver = setup_driver(headless=self.headless, window_size=WINDOW_SIZE)
            # 设置随机User-Agent
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": get_random_user_agent()
            })
            logging.info("浏览器驱动设置成功")
            return True
        except Exception as e:
            logging.error(f"设置浏览器驱动失败: {e}")
            return False

    def load_user_page(self, user_url):
        """加载用户主页"""
        try:
            if not validate_url(user_url):
                logging.error(f"无效的URL: {user_url}")
                return False

            logging.info(f"开始加载用户主页: {user_url}")
            self.driver.get(user_url)

            # 等待页面加载
            time.sleep(3)

            # 检查是否成功加载
            if "toutiao.com" not in self.driver.current_url:
                logging.error("页面加载失败，可能被重定向")
                return False

            logging.info("用户主页加载成功")
            return True

        except Exception as e:
            logging.error(f"加载用户主页失败: {e}")
            return False

    def load_all_articles(self):
        """滚动加载所有文章"""
        try:
            logging.info("开始加载所有文章...")

            last_height = 0
            no_change_count = 0
            max_no_change = 3  # 连续3次没有变化就停止
            max_iterations = 50  # 最大迭代次数，防止无限循环
            iteration = 0

            while no_change_count < max_no_change and iteration < max_iterations:
                iteration += 1
                logging.info(f"第 {iteration} 次滚动加载...")

                # 滚动到底部
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

                # 等待新内容加载
                time.sleep(SCROLL_PAUSE_TIME)

                # 获取当前页面高度
                new_height = self.driver.execute_script("return document.body.scrollHeight")

                logging.info(f"页面高度: {new_height}")

                # 检查是否有变化
                if new_height == last_height:
                    no_change_count += 1
                    logging.info(f"页面高度无变化，计数: {no_change_count}/{max_no_change}")
                else:
                    no_change_count = 0
                    last_height = new_height
                    logging.info("页面高度有更新，重置计数器")

                # 检查是否有加载更多元素
                try:
                    loading_more = self.driver.find_elements(By.CSS_SELECTOR,
                        SELECTORS['toutiao'].get('loading_more', '.loading-more'))
                    if loading_more:
                        logging.info("检测到加载更多元素，继续等待...")
                        time.sleep(2)
                except:
                    pass

            # 获取最终文章数量
            try:
                article_elements = self.driver.find_elements(By.CSS_SELECTOR,
                    SELECTORS['toutiao']['article_cards'])
                final_count = len(article_elements)

                if final_count == 0:
                    logging.error("未找到任何文章元素，可能页面结构不兼容")
                else:
                    logging.info(f"文章加载完成，共 {final_count} 篇")

                return final_count
            except Exception as e:
                logging.error(f"获取文章数量失败: {e}")
                return 0

        except Exception as e:
            logging.error(f"加载所有文章失败: {e}")
            return 0

    def extract_articles_list(self):
        """提取文章列表"""
        try:
            new_articles = []

            # 获取所有文章元素
            article_elements = self.driver.find_elements(By.CSS_SELECTOR,
                SELECTORS['toutiao']['article_cards'])
            logging.info(f"找到 {len(article_elements)} 个文章元素")

            if not article_elements:
                logging.warning("未找到任何文章元素，可能页面结构不兼容或页面未加载完成")
                return []

            for index, element in enumerate(article_elements):
                try:
                    # 提取文章链接
                    link_element = element.find_element(By.CSS_SELECTOR,
                        SELECTORS['toutiao']['article_link'])
                    article_url = link_element.get_attribute('href')

                    if not article_url:
                        logging.warning(f"第{index+1}个文章元素无法提取链接，跳过")
                        continue

                    # 处理相对URL
                    if article_url.startswith('/'):
                        article_url = 'https://www.toutiao.com' + article_url

                    # 检查文章是否已经存在（基于URL去重）
                    if self.articles_data:
                        exists = any(a.get('url') == article_url for a in self.articles_data.get('articles', []))
                        if exists:
                            logging.info(f"文章已存在，跳过: {article_url[:50]}...")
                            continue

                    # 提取文章标题
                    title = link_element.get_attribute('aria-label') or link_element.text.strip()

                    # 提取发布时间
                    publish_time = ""
                    try:
                        time_element = element.find_element(By.CSS_SELECTOR,
                            SELECTORS['toutiao']['publish_time'])
                        publish_time = time_element.text.strip()
                    except:
                        pass

                    # 提取阅读量
                    read_count = ""
                    try:
                        read_element = element.find_element(By.CSS_SELECTOR,
                            SELECTORS['toutiao']['read_count'])
                        read_count = read_element.text.strip()
                    except:
                        pass

                    article_info = {
                        'index': index + 1,
                        'title': title,
                        'url': article_url,
                        'publish_time': publish_time,
                        'read_count': read_count,
                        'status': 'pending',
                        'file_path': None,
                        'error_message': None,
                        'processed_time': None,
                        'retry_count': 0
                    }

                    new_articles.append(article_info)
                    logging.debug(f"成功提取文章 {index+1}: {title[:30]}...")

                except Exception as e:
                    logging.error(f"提取第{index+1}个文章信息失败: {e}")
                    continue

            # 合并现有数据
            if self.articles_data and self.articles_data.get('articles'):
                logging.info(f"合并 {len(new_articles)} 篇新文章到现有数据")
                # 使用URL去重合并
                existing_urls = set(a['url'] for a in self.articles_data['articles'])
                for new_article in new_articles:
                    if new_article['url'] not in existing_urls:
                        self.articles_data['articles'].append(new_article)
                        existing_urls.add(new_article['url'])
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
        """提取文章正文内容"""
        try:
            logging.info(f"开始提取文章内容: {article_url}")

            # 打开新标签页
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])

            # 访问文章页面
            self.driver.get(article_url)

            # 等待页面加载
            time.sleep(3)

            # 提取文章标题
            title = ""
            try:
                title_element = self.driver.find_element(By.CSS_SELECTOR,
                    SELECTORS['toutiao']['article_title_full'])
                title = title_element.text.strip()
            except:
                pass

            # 提取作者信息
            author = ""
            try:
                author_element = self.driver.find_element(By.CSS_SELECTOR,
                    SELECTORS['toutiao']['author_name'])
                author = author_element.text.strip()
            except:
                pass

            # 提取文章元信息（包含发布时间）
            meta_info = ""
            try:
                meta_element = self.driver.find_element(By.CSS_SELECTOR,
                    SELECTORS['toutiao']['article_meta'])
                meta_info = meta_element.text.strip()
            except:
                pass

            # 提取文章内容
            content = ""
            try:
                content_element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR,
                        SELECTORS['toutiao']['article_content']))
                )

                # 获取所有段落
                paragraphs = content_element.find_elements(By.TAG_NAME, 'p')
                content_parts = []

                for p in paragraphs:
                    text = p.text.strip()
                    if text:
                        content_parts.append(text)

                content = '\n\n'.join(content_parts)

            except TimeoutException:
                logging.warning("无法找到文章内容元素")
                # 备用方案：获取整个页面文本
                content = self.driver.find_element(By.TAG_NAME, 'body').text.strip()

            # 关闭当前标签页，返回主页
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])

            # 构建完整内容
            full_content = f"# {title}\n\n"
            if author:
                full_content += f"**作者**: {author}\n\n"
            if meta_info:
                full_content += f"**发布信息**: {meta_info}\n\n"
            full_content += content

            logging.info(f"文章内容提取成功，长度: {len(content)} 字符")
            return full_content

        except Exception as e:
            logging.error(f"提取文章内容异常: {e}")
            # 确保返回主页
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return None

    def process_article(self, article_info, output_dir):
        """处理单个文章"""
        index = article_info['index']
        title = article_info['title']
        url = article_info['url']

        try:
            logging.info(f"开始处理第 {index} 篇文章: {title}")

            # 提取文章内容
            content = self.extract_article_content(url)
            if not content:
                raise Exception("文章内容为空")

            # 生成文件名
            clean_title = clean_filename(title)
            filename = f"{index}_{clean_title}.md"

            # 按日期创建子目录
            publish_date = datetime.now().strftime("%Y-%m-%d")
            date_dir = os.path.join(output_dir, publish_date)
            os.makedirs(date_dir, exist_ok=True)

            file_path = os.path.join(date_dir, filename)

            # 保存文章内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # 更新文章信息
            article_info['file_path'] = file_path
            article_info['processed_time'] = datetime.now().isoformat()

            # 更新状态
            for i, art in enumerate(self.articles_data['articles']):
                if art.get('url') == url:
                    art['status'] = 'completed'
                    art['file_path'] = file_path
                    art['processed_time'] = datetime.now().isoformat()
                    break

            logging.info(f"第 {index} 篇文章处理完成: {title}")
            return True

        except Exception as e:
            error_msg = f"处理失败: {e}"
            logging.error(f"第 {index} 篇文章处理失败: {title}, {error_msg}")

            # 更新状态
            for i, art in enumerate(self.articles_data['articles']):
                if art.get('url') == url:
                    art['status'] = 'failed'
                    art['error_message'] = error_msg
                    art['retry_count'] = art.get('retry_count', 0) + 1
                    break

            return False

    def crawl_user_articles(self, user_url, output_dir=TOUTIAO_ARTICLES_DIR, resume=True):
        """抓取用户主页文章"""
        try:
            # 加载现有状态
            if resume and os.path.exists(TOUTIAO_JSON_FILE):
                self.articles_data = load_json_state(TOUTIAO_JSON_FILE)
                if self.articles_data:
                    logging.info("加载现有状态成功")
                else:
                    logging.info("创建新的状态文件")
                    self.articles_data = None

            # 设置输出目录
            os.makedirs(output_dir, exist_ok=True)

            # 如果没有现有数据或不需要恢复，重新抓取
            if not self.articles_data or not resume:
                # 设置驱动
                if not self.setup_driver():
                    return False

                # 加载用户主页
                if not self.load_user_page(user_url):
                    return False

                # 加载所有文章
                loaded_count = self.load_all_articles()

                # 提取文章列表
                articles = self.extract_articles_list()

                # 初始化数据结构
                self.articles_data = {
                    'user_url': user_url,
                    'total_articles': len(articles),
                    'processed_count': 0,
                    'failed_count': 0,
                    'pending_count': len(articles),
                    'crawl_time': datetime.now().isoformat(),
                    'articles': articles
                }

                # 保存初始状态
                save_json_state(self.articles_data, TOUTIAO_JSON_FILE)

            # 设置驱动（如果还没有设置）
            if not self.driver:
                if not self.setup_driver():
                    return False

            # 确保在用户主页
            if user_url not in self.driver.current_url:
                self.load_user_page(user_url)

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

                # 保存状态
                self.articles_data['processed_count'] = sum(1 for a in self.articles_data['articles'] if a['status'] == 'completed')
                self.articles_data['failed_count'] = sum(1 for a in self.articles_data['articles'] if a['status'] == 'failed')
                self.articles_data['pending_count'] = sum(1 for a in self.articles_data['articles'] if a['status'] == 'pending')
                save_json_state(self.articles_data, TOUTIAO_JSON_FILE)

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
            logging.error(f"抓取用户主页失败: {e}")
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
    import argparse

    parser = argparse.ArgumentParser(description='今日头条用户主页文章抓取工具')
    parser.add_argument('--url', required=True, help='今日头条用户主页链接')
    parser.add_argument('--output', default=TOUTIAO_ARTICLES_DIR, help='文章保存目录')
    parser.add_argument('--delay', type=int, default=DEFAULT_DELAY, help='请求间隔时间（秒）')
    parser.add_argument('--no-resume', action='store_false', dest='resume', help='不从断点继续，重新开始')
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
    crawler = ToutiaoUserCrawler(headless=args.headless, delay=args.delay)

    # 开始抓取
    try:
        success = crawler.crawl_user_articles(
            user_url=args.url,
            output_dir=args.output,
            resume=args.resume
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