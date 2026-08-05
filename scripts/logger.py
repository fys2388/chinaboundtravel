#!/usr/bin/env python3
"""
统一日志模块 - 为所有脚本提供一致的日志格式
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# 日志目录
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 日志格式
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 颜色代码（Windows需要colorama，这里使用标准格式）
class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""
    
    COLORS = {
        "DEBUG": "\033[36m",     # 青色
        "INFO": "\033[32m",      # 绿色
        "WARNING": "\033[33m",   # 黄色
        "ERROR": "\033[31m",     # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"
    
    def format(self, record):
        # 添加颜色
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        
        # 调用父类格式化
        return super().format(record)


def setup_logger(
    name: str,
    level: str = "INFO",
    log_file: str = None,
    console_output: bool = True
) -> logging.Logger:
    """
    创建配置好的logger
    
    Args:
        name: logger名称
        level: 日志级别
        log_file: 日志文件名（可选）
        console_output: 是否输出到控制台
    
    Returns:
        配置好的logger实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 格式化器
    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=DATE_FORMAT
    )
    
    # 文件处理器
    if log_file:
        log_path = LOG_DIR / log_file
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取已存在的logger
    
    Args:
        name: logger名称
    
    Returns:
        logger实例
    """
    return logging.getLogger(name)


def log_task(logger: logging.Logger, task_name: str, status: str, details: str = ""):
    """
    记录任务状态
    
    Args:
        logger: logger实例
        task_name: 任务名称
        status: 状态（PENDING, RUNNING, SUCCESS, FAILED）
        details: 详细信息
    """
    icon_map = {
        "PENDING": "⏳",
        "RUNNING": "🔄",
        "SUCCESS": "✅",
        "FAILED": "❌",
        "ERROR": "💥"
    }
    icon = icon_map.get(status, "⚪")
    logger.info(f"{icon} [{task_name}] {status}{f' - {details}' if details else ''}")


def log_progress(logger: logging.Logger, current: int, total: int, message: str = ""):
    """
    记录进度
    
    Args:
        logger: logger实例
        current: 当前进度
        total: 总数
        message: 消息
    """
    percent = (current / total * 100) if total > 0 else 0
    bar_length = 30
    filled = int(bar_length * current / total) if total > 0 else 0
    bar = '█' * filled + '░' * (bar_length - filled)
    
    logger.info(f"📊 [{bar}] {current}/{total} ({percent:.1f}%) {message}")


def log_api_call(logger: logging.Logger, endpoint: str, status_code: int, response_time: float):
    """
    记录API调用
    
    Args:
        logger: logger实例
        endpoint: API端点
        status_code: 状态码
        response_time: 响应时间（毫秒）
    """
    icon = "✅" if 200 <= status_code < 300 else "❌"
    logger.info(f"{icon} API: {endpoint} | {status_code} | {response_time:.0f}ms")


def log_error(logger: logging.Logger, error: Exception, context: str = ""):
    """
    记录错误
    
    Args:
        logger: logger实例
        error: 异常对象
        context: 错误上下文
    """
    context_str = f" - {context}" if context else ""
    logger.error(f"💥 错误{context_str}: {type(error).__name__}: {str(error)}")
    logger.debug(f"详细错误信息:", exc_info=True)


def log_section(logger: logging.Logger, title: str):
    """
    记录章节标题
    
    Args:
        logger: logger实例
        title: 标题
    """
    logger.info(f"\n{'=' * 60}")
    logger.info(f"📌 {title}")
    logger.info(f"{'=' * 60}\n")
