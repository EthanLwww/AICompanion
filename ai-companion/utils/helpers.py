import json
import base64
from typing import Any, Dict, List, Optional
import time
import hashlib
from datetime import datetime


def hex_to_audio_data(hex_string: str) -> Optional[bytes]:
    """
    将十六进制字符串转换为音频数据
    """
    if not hex_string:
        return None
    try:
        return bytes.fromhex(hex_string)
    except ValueError:
        return None


def audio_data_to_hex(audio_data: bytes) -> str:
    """
    将音频数据转换为十六进制字符串
    """
    if not audio_data:
        return ""
    return audio_data.hex()


def format_time(seconds: int) -> str:
    """
    将秒数格式化为 HH:MM:SS 格式
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_minutes_to_duration(minutes: int) -> str:
    """
    将分钟数格式化为易读的持续时间格式
    """
    if minutes < 60:
        return f"{minutes}分钟"
    elif minutes < 1440:  # 小于一天
        hours = minutes // 60
        remaining_minutes = minutes % 60
        if remaining_minutes > 0:
            return f"{hours}小时{remaining_minutes}分钟"
        else:
            return f"{hours}小时"
    else:  # 一天或以上
        days = minutes // 1440
        remaining_hours = (minutes % 1440) // 60
        if remaining_hours > 0:
            return f"{days}天{remaining_hours}小时"
        else:
            return f"{days}天"


def get_current_timestamp() -> float:
    """
    获取当前时间戳
    """
    return time.time()


def get_formatted_datetime() -> str:
    """
    获取格式化的当前日期时间
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def calculate_age(start_time: float) -> float:
    """
    计算从开始时间到现在的年龄（秒）
    """
    return time.time() - start_time


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    安全地解析JSON字符串
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, default: Any = None) -> str:
    """
    安全地将对象转换为JSON字符串
    """
    try:
        return json.dumps(obj, ensure_ascii=False)
    except (TypeError, ValueError):
        return json.dumps(default) if default is not None else ""


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断文本到指定长度
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除不安全字符
    """
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def generate_hash(data: str, algorithm: str = 'sha256') -> str:
    """
    生成数据的哈希值
    """
    hasher = hashlib.new(algorithm)
    hasher.update(data.encode('utf-8'))
    return hasher.hexdigest()


def merge_dicts(base_dict: Dict, update_dict: Dict, deep: bool = False) -> Dict:
    """
    合并两个字典
    """
    result = base_dict.copy()
    
    for key, value in update_dict.items():
        if deep and isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = merge_dicts(result[key], value, deep=True)
        else:
            result[key] = value
    
    return result


def flatten_list(nested_list: List) -> List:
    """
    展平嵌套列表
    """
    flattened = []
    for item in nested_list:
        if isinstance(item, list):
            flattened.extend(flatten_list(item))
        else:
            flattened.append(item)
    return flattened


def group_by(items: List[Dict], key: str) -> Dict[Any, List[Dict]]:
    """
    按指定键对字典列表进行分组
    """
    groups = {}
    for item in items:
        group_key = item.get(key)
        if group_key not in groups:
            groups[group_key] = []
        groups[group_key].append(item)
    return groups


def debounce(func, wait_time: float):
    """
    防抖装饰器，防止函数在指定时间内被频繁调用
    """
    def debounced(*args, **kwargs):
        # 这里简化实现，实际应用中可能需要更复杂的防抖逻辑
        return func(*args, **kwargs)
    return debounced


def throttle(func, interval: float):
    """
    节流装饰器，限制函数在指定时间间隔内最多执行一次
    """
    last_called = [0]
    
    def throttled(*args, **kwargs):
        current_time = time.time()
        if current_time - last_called[0] >= interval:
            last_called[0] = current_time
            return func(*args, **kwargs)
    return throttled


class DataStorage:
    """
    简单的数据存储类，用于在应用间共享数据
    """
    
    def __init__(self):
        self._data = {}
    
    def set(self, key: str, value: Any):
        """设置值"""
        self._data[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取值"""
        return self._data.get(key, default)
    
    def delete(self, key: str):
        """删除键值"""
        if key in self._data:
            del self._data[key]
    
    def clear(self):
        """清空所有数据"""
        self._data.clear()
    
    def keys(self) -> List[str]:
        """获取所有键"""
        return list(self._data.keys())
    
    def items(self) -> List[tuple]:
        """获取所有键值对"""
        return list(self._data.items())


# 全局数据存储实例
global_data_storage = DataStorage()