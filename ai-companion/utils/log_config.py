"""
日志配置管理器 - 支持测试和生产环境的动态日志级别切换
"""
import os
import logging
from typing import Dict, Optional

class LogConfigManager:
    """日志配置管理器"""
    
    # 环境配置映射
    ENV_CONFIGS = {
        'development': {
            'console_level': logging.DEBUG,
            'file_level': logging.DEBUG,
            'format': '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            'enable_enhanced_logs': True,  # 启用增强测试日志
            'performance_monitoring': True  # 启用性能监控
        },
        'testing': {
            'console_level': logging.INFO,
            'file_level': logging.DEBUG,
            'format': '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            'enable_enhanced_logs': True,
            'performance_monitoring': True
        },
        'production': {
            'console_level': logging.WARNING,
            'file_level': logging.INFO,
            'format': '[%(asctime)s] [%(levelname)s] %(message)s',
            'enable_enhanced_logs': False,  # 关闭增强测试日志
            'performance_monitoring': False
        }
    }
    
    def __init__(self, env: Optional[str] = None):
        self.current_env = env or self._detect_environment()
        self.config = self.ENV_CONFIGS.get(self.current_env, self.ENV_CONFIGS['production'])
        
    def _detect_environment(self) -> str:
        """自动检测运行环境"""
        # 检查环境变量
        env_var = os.getenv('APP_ENV', '').lower()
        if env_var in ['dev', 'development']:
            return 'development'
        elif env_var in ['test', 'testing']:
            return 'testing'
        elif env_var in ['prod', 'production']:
            return 'production'
            
        # 检查是否在创空间环境
        if self._is_modelscope_environment():
            return 'production'
            
        # 默认为开发环境
        return 'development'
    
    def _is_modelscope_environment(self) -> bool:
        """检测是否在魔搭创空间环境"""
        # 检查常见的创空间环境特征
        return (
            os.getenv('MODELSCOPE_ENV') is not None or
            os.getenv('DASHSCOPE_ENV') is not None or
            'modelscope' in os.getcwd().lower()
        )
    
    def get_current_config(self) -> Dict:
        """获取当前环境配置"""
        return self.config.copy()
    
    def should_enable_enhanced_logs(self) -> bool:
        """判断是否应该启用增强日志"""
        return self.config.get('enable_enhanced_logs', False)
    
    def should_enable_performance_monitoring(self) -> bool:
        """判断是否应该启用性能监控"""
        return self.config.get('performance_monitoring', False)
    
    def apply_config(self, logger_instance: logging.Logger):
        """应用配置到指定的logger实例"""
        # 设置logger级别
        logger_instance.setLevel(min(
            self.config['console_level'],
            self.config['file_level']
        ))
        
        # 配置handlers（如果需要的话）
        # 这里可以根据需要添加具体的handler配置
        
    def get_environment_info(self) -> Dict:
        """获取环境信息"""
        return {
            'environment': self.current_env,
            'enhanced_logs_enabled': self.should_enable_enhanced_logs(),
            'performance_monitoring_enabled': self.should_enable_performance_monitoring(),
            'console_level': logging.getLevelName(self.config['console_level']),
            'file_level': logging.getLevelName(self.config['file_level'])
        }

# 全局实例
log_manager = LogConfigManager()

# 便捷函数
def is_enhanced_logging_enabled() -> bool:
    """检查是否启用了增强日志"""
    return log_manager.should_enable_enhanced_logs()

def is_performance_monitoring_enabled() -> bool:
    """检查是否启用了性能监控"""
    return log_manager.should_enable_performance_monitoring()

def get_current_environment() -> str:
    """获取当前环境名称"""
    return log_manager.current_env

def setup_environment_based_logging(logger_instance: logging.Logger):
    """基于环境设置日志配置"""
    log_manager.apply_config(logger_instance)
    return log_manager.get_environment_info()