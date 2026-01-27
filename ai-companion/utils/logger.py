import logging
import os
from datetime import datetime

def setup_logger(name="study_companion"):
    """
    设置全局统一的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # 避免重复添加 Handler
    if not logger.handlers:
        # 创建格式化器
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台 Handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # 文件 Handler (debug.log)
        log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "debug.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # 部署日志 Handler (deployment.log) - 记录关键节点
        deployment_log = os.path.join(os.path.dirname(os.path.dirname(__file__)), "deployment.log")
        deployment_handler = logging.FileHandler(deployment_log, encoding='utf-8')
        deployment_handler.setLevel(logging.INFO)
        deployment_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.addHandler(deployment_handler)
        
    return logger

# 导出全局实例
logger = setup_logger()

# ============ 便捷日志函数 ============

def log_module_init(module_name, details=""):
    """
    记录模块初始化信息（部署关键节点）
    """
    msg = f"[INIT] {module_name} module initialized"
    if details:
        msg += f" | {details}"
    logger.info(msg)

def log_checkpoint(checkpoint_name, details=""):
    """
    记录关键检查点（部署关键节点）
    """
    msg = f"[CHECKPOINT] {checkpoint_name}"
    if details:
        msg += f" | {details}"
    logger.info(msg)

def log_ui_event(event_name, user_action=""):
    """
    记录UI事件（调试用）
    """
    msg = f"[UI_EVENT] {event_name}"
    if user_action:
        msg += f" | action: {user_action}"
    logger.debug(msg)

def log_feature_call(feature_name, params=None):
    """
    记录功能调用（调试用）
    """
    msg = f"[FEATURE] {feature_name}"
    if params:
        msg += f" | params: {params}"
    logger.debug(msg)

def log_data_change(data_type, change_info):
    """
    记录数据变化（调试用）
    """
    logger.debug(f"[DATA] {data_type} changed: {change_info}")

def log_js_event(event_name, details=""):
    """
    记录JavaScript事件（调试用）
    """
    msg = f"[JS_EVENT] {event_name}"
    if details:
        msg += f" | {details}"
    logger.debug(msg)

def log_error_trace(error_name, exception):
    """
    记录错误追踪（带完整堆栈信息）
    """
    logger.error(f"[ERROR] {error_name}: {str(exception)}", exc_info=True)

def log_deployment_start(server_name, server_port):
    """
    记录应用启动
    """
    logger.info(f"[DEPLOYMENT_START] Starting application on {server_name}:{server_port}")

def log_deployment_error(error_name, error_detail):
    """
    记录部署错误（部署关键节点）
    """
    logger.error(f"[DEPLOYMENT_ERROR] {error_name}: {error_detail}")
