#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安装完成确认脚本
"""

import sys
import os

def check_installation():
    """检查安装状态"""
    print("=" * 60)
    print("WeChat Article Crawler - Installation Status")
    print("=" * 60)

    # 检查Python版本
    print("Python Environment:")
    try:
        import sys
        print(f"+ Python version: {sys.version}")
        if sys.version_info < (3, 8):
            print("- Warning: Python 3.8+ recommended")
        else:
            print("+ Python version is sufficient")
    except Exception as e:
        print(f"- Error checking Python: {e}")
        return False

    # 检查核心依赖
    print("\nCore Dependencies:")
    dependencies = {
        'selenium': 'Selenium WebDriver',
        'requests': 'HTTP Requests',
        'bs4': 'BeautifulSoup4',
        'tqdm': 'Progress Bar'
    }

    all_installed = True
    for module, name in dependencies.items():
        try:
            __import__(module)
            print(f"+ {name} installed")
        except ImportError:
            print(f"- {name} not installed")
            all_installed = False

    # 检查项目文件
    print("\nProject Files:")
    required_files = [
        'crawler.py', 'config.py', 'utils.py', 'requirements.txt',
        'README.md', 'TROUBLESHOOTING.md'
    ]

    for file_name in required_files:
        if os.path.exists(file_name):
            print(f"+ {file_name} exists")
        else:
            print(f"- {file_name} missing")
            all_installed = False

    # 检查目录
    print("\nDirectories:")
    required_dirs = ['articles', 'logs']
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"+ {dir_name}/ directory exists")
        else:
            os.makedirs(dir_name)
            print(f"+ {dir_name}/ directory created")

    return all_installed

def show_usage():
    """显示使用说明"""
    print("\n" + "=" * 60)
    print("Ready to Use!")
    print("=" * 60)
    print("\nQuick Start:")
    print("python crawler.py --url \"WeChat album URL\"")

    print("\nExample:")
    print("python crawler.py --url \"https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzkyNjQyOTQzOA==&action=getalbum\"")

    print("\nAll Options:")
    print("python crawler.py --url \"URL\" [OPTIONS]")
    print("  --output PATH     Save directory (default: ./articles)")
    print("  --delay SECONDS    Request delay (default: 15)")
    print("  --headless        Run without browser window")
    print("  --retry-failed    Retry only failed articles")
    print("  --no-resume       Start fresh (ignore breakpoints)")

    print("\nFor help:")
    print("python crawler.py --help")

    print("\nTroubleshooting:")
    print("- See TROUBLESHOOTING.md")
    print("- Run: python quick_test.py")
    print("- Contact support if issues persist")

def main():
    """主函数"""
    print("WeChat Album Article Crawler - Setup Checker")
    print("This script will verify all components are properly installed.")

    is_complete = check_installation()

    if is_complete:
        show_usage()
        return 0
    else:
        print("\n" + "=" * 60)
        print("Installation incomplete. Please run install.bat or install dependencies manually.")
        return 1

if __name__ == "__main__":
    sys.exit(main())