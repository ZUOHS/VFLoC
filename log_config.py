import os
import logging
from datetime import datetime
import colorlog

# 设置日志保存路径
log_path = os.path.join(os.getcwd(), 'logs')
if not os.path.exists(log_path):
    os.makedirs(log_path)

handler = colorlog.StreamHandler()  # 控制台处理器
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    log_colors={
        'DEBUG': 'blue',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }
))

logger = logging.getLogger()  # 获取全局日志器
logger.setLevel(logging.INFO)  # 设置全局日志级别
logger.addHandler(handler)  # 添加彩色控制台处理器

# 文件日志处理器
log_filename = datetime.now().strftime('%Y-%m-%d') + '.log'
file_handler = logging.FileHandler(os.path.join(log_path, log_filename), encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
logger.addHandler(file_handler)  # 添加到全局日志器


def some_function():
    logger.debug("这是一条调试级别的日志")
    logger.info("这是一条信息级别的日志")
    logger.warning("这是一条警告级别的日志")
    logger.error("这是一条错误级别的日志")
    logger.critical("这是一条严重错误级别的日志")


if __name__ == "__main__":
    some_function()
