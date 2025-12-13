#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文章抓取器启动脚本
支持微信公众号和今日头条平台
"""

import os
import sys
from crawler import main

def interactive_mode():
    """交互式模式"""
    print("=" * 60)
    print("文章抓取工具 - 支持微信公众号和今日头条")
    print("=" * 60)

    # 输入URL
    print("\n请输入要抓取的链接:")
    print("- 微信公众号专辑链接（如：https://mp.weixin.qq.com/...）")
    print("- 今日头条用户主页链接（如：https://www.toutiao.com/c/user/...）")
    url = input("\nURL: ").strip()

    if not url:
        print("错误：URL不能为空")
        return 1

    # 自动识别平台
    if "mp.weixin.qq.com" in url:
        platform = "微信公众号"
    elif "toutiao.com" in url:
        platform = "今日头条"
    else:
        print("\n请选择平台类型:")
        print("1. 微信公众号")
        print("2. 今日头条")
        choice = input("请输入选项（1或2）: ").strip()

        if choice == "1":
            platform = "微信公众号"
        elif choice == "2":
            platform = "今日头条"
        else:
            print("错误：无效的选项")
            return 1

    # 其他选项
    print(f"\n已选择平台: {platform}")
    print("请输入其他选项（直接回车使用默认值）:")

    # 输出目录
    default_output = "toutiao_article" if platform == "今日头条" else "articles"
    output = input(f"输出目录 (默认: {default_output}): ").strip()
    if not output:
        output = default_output

    # 延时
    default_delay = "3"
    delay = input(f"请求间隔秒数 (默认: {default_delay}): ").strip()
    if not delay:
        delay = default_delay

    # 是否断点续传
    resume_input = input("是否从断点继续 (y/n, 默认: y): ").strip().lower()
    resume = resume_input != 'n'

    # 是否无头模式
    headless_input = input("是否无头模式运行 (y/n, 默认: n): ").strip().lower()
    headless = headless_input == 'y'

    # 构建命令行参数
    cmd_args = [
        '--url', url,
        '--output', output,
        '--delay', delay
    ]

    if not resume:
        cmd_args.append('--no-resume')

    if headless:
        cmd_args.append('--headless')

    # 保存原始sys.argv
    original_argv = sys.argv

    try:
        # 设置新的sys.argv
        sys.argv = ['run.py'] + cmd_args

        print("\n" + "=" * 60)
        print("开始抓取...")
        print("=" * 60 + "\n")

        # 调用主函数
        return main()

    finally:
        # 恢复原始sys.argv
        sys.argv = original_argv

def print_usage():
    """打印使用说明"""
    print("""
使用方法:
1. 交互式模式（推荐）:
   python run.py

2. 命令行模式:
   python run.py --url <链接> [选项]

示例:
# 抓取微信公众号专辑
python run.py --url https://mp.weixin.qq.com/s/xxxx

# 抓取今日头条用户主页
python run.py --url https://www.toutiao.com/c/user/xxxx

更多选项:
--output <目录>     指定输出目录
--delay <秒数>      设置请求间隔
--no-resume         不从断点继续
--headless          无头模式运行

注意事项:
- 微信公众号文章保存在 articles/ 目录
- 今日头条文章保存在 toutiao_article/ 目录
- 支持 Ctrl+C 中断和断点续传
    """)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 命令行模式
        if '--help' in sys.argv or '-h' in sys.argv:
            print_usage()
            sys.exit(0)
        sys.exit(main())
    else:
        # 交互式模式
        sys.exit(interactive_mode())