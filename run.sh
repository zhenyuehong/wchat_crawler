#!/bin/bash

# 微信公众号专辑文章抓取工具运行脚本

echo "========================================"
echo "微信公众号专辑文章抓取工具"
echo "========================================"
echo

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "错误：未找到Python，请先安装Python 3.8+"
        echo "下载地址：https://www.python.org/downloads/"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

echo "使用Python: $PYTHON_CMD"
$PYTHON_CMD --version

# 检查是否存在requirements.txt
if [ ! -f "requirements.txt" ]; then
    echo "错误：未找到requirements.txt文件"
    exit 1
fi

# 安装依赖
echo "正在检查并安装依赖包..."
pip3 install -r requirements.txt 2>/dev/null || pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "警告：依赖包安装可能有问题，但继续运行..."
fi

echo
echo "使用方法："
echo "  python crawler.py --url \"微信公众号专辑链接\""
echo
echo "示例："
echo "  python crawler.py --url \"https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzkyNjQyOTQzOA==&action=getalbum&album_id=3864942002693373954\""
echo
echo "更多参数："
echo "  --output \"./articles\"    # 文章保存目录"
echo "  --delay 15              # 请求间隔时间（秒）"
echo "  --headless              # 无头模式运行"
echo "  --retry-failed          # 仅重试失败的文章"
echo "  --no-resume             # 不从断点继续，重新开始"
echo

# 如果用户提供了参数，直接运行
if [ $# -gt 0 ]; then
    echo "正在运行：python crawler.py $*"
    python crawler.py "$@"
else
    echo "请输入专辑链接，或直接运行脚本后手动输入："
    read -p "请输入微信公众号专辑链接: " album_url

    if [ -z "$album_url" ]; then
        echo "未输入链接，程序退出"
        exit 1
    fi

    echo
    echo "正在运行抓取程序..."
    python crawler.py --url "$album_url"
fi

echo
echo "程序运行完成！"