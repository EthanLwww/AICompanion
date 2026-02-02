"""
日志清理和版本迁移工具 - 用于正式版本上线时清理测试日志
"""
import re
import os
from typing import List, Tuple, Dict
from pathlib import Path

class LogCleanupTool:
    """日志清理工具"""
    
    # 测试阶段增强日志的标识模式
    TEST_LOG_PATTERNS = [
        r'#\s*【TEST_ENHANCEMENT】.*',  # 测试增强标记
        r'logger\.debug\(f"\[SUPERVISION_DEBUG\] .*测试.*"\)',  # 测试相关的debug日志
        r'console\.log\(.*\[SUPERVISION_DEBUG\].*测试.*\)',  # 前端测试日志
        r'📊|🎯|💾|🔍|📥|📝|🚀|📡|📊|✅|❌|⚠️|⏱️|🌐|❗',  # 特殊emoji标识
        r'├─|└─',  # 树形结构日志
        r'enhanced_|detailed_|trace_|diagnostic_',  # 增强日志关键词
    ]
    
    # 需要保留的核心日志模式
    CORE_LOG_PATTERNS = [
        r'logger\.(info|warning|error|critical)\(f?"\[SUPERVISION\]',  # 核心监督日志
        r'logger\.(info|warning|error|critical)\(f?"\[VISION_AI\]',   # 核心AI日志
        r'console\.log\(.*\[SUPERVISION\]',  # 前端核心日志
    ]
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        
    def scan_project_files(self) -> List[Path]:
        """扫描项目中需要检查的文件"""
        files_to_check = []
        
        # 定义要检查的文件模式
        file_patterns = [
            '**/*.py',
            '**/*.js',
            '**/*.jsx',
            '**/*.ts',
            '**/*.tsx'
        ]
        
        for pattern in file_patterns:
            files_to_check.extend(self.project_root.glob(pattern))
            
        return files_to_check
    
    def analyze_file_logs(self, file_path: Path) -> Dict:
        """分析单个文件中的日志使用情况"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return {
                'file': str(file_path),
                'error': str(e),
                'test_logs': [],
                'core_logs': []
            }
        
        test_logs = []
        core_logs = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # 检查测试日志
            for pattern in self.TEST_LOG_PATTERNS:
                if re.search(pattern, line_stripped):
                    test_logs.append({
                        'line': line_num,
                        'content': line_stripped[:100] + ('...' if len(line_stripped) > 100 else ''),
                        'pattern': pattern
                    })
                    break
            
            # 检查核心日志
            for pattern in self.CORE_LOG_PATTERNS:
                if re.search(pattern, line_stripped):
                    core_logs.append({
                        'line': line_num,
                        'content': line_stripped[:100] + ('...' if len(line_stripped) > 100 else ''),
                        'pattern': pattern
                    })
                    break
        
        return {
            'file': str(file_path),
            'total_lines': len(lines),
            'test_logs_count': len(test_logs),
            'core_logs_count': len(core_logs),
            'test_logs': test_logs,
            'core_logs': core_logs
        }
    
    def generate_cleanup_report(self) -> Dict:
        """生成清理报告"""
        files = self.scan_project_files()
        report = {
            'total_files': len(files),
            'files_analyzed': [],
            'summary': {
                'total_test_logs': 0,
                'total_core_logs': 0,
                'files_with_test_logs': 0,
                'files_needing_attention': []
            }
        }
        
        for file_path in files:
            analysis = self.analyze_file_logs(file_path)
            report['files_analyzed'].append(analysis)
            
            report['summary']['total_test_logs'] += analysis['test_logs_count']
            report['summary']['total_core_logs'] += analysis['core_logs_count']
            
            if analysis['test_logs_count'] > 0:
                report['summary']['files_with_test_logs'] += 1
                report['summary']['files_needing_attention'].append({
                    'file': analysis['file'],
                    'test_logs': analysis['test_logs_count'],
                    'core_logs': analysis['core_logs_count']
                })
        
        return report
    
    def cleanup_test_logs(self, dry_run: bool = True) -> Dict:
        """清理测试日志（实际执行清理）"""
        report = self.generate_cleanup_report()
        cleanup_actions = []
        
        for file_analysis in report['files_analyzed']:
            if file_analysis['test_logs_count'] == 0:
                continue
                
            file_path = Path(file_analysis['file'])
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                cleaned_lines = []
                removed_lines = []
                
                for line_num, line in enumerate(lines, 1):
                    should_remove = False
                    
                    # 检查是否为测试日志行
                    for test_log in file_analysis['test_logs']:
                        if test_log['line'] == line_num:
                            should_remove = True
                            removed_lines.append({
                                'line_num': line_num,
                                'content': line.strip()
                            })
                            break
                    
                    if not should_remove:
                        cleaned_lines.append(line)
                
                if not dry_run and removed_lines:
                    # 执行实际清理
                    backup_path = file_path.with_suffix(file_path.suffix + '.backup')
                    # 创建备份
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    
                    # 写入清理后的内容
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(cleaned_lines)
                
                cleanup_actions.append({
                    'file': str(file_path),
                    'removed_lines': len(removed_lines),
                    'backup_created': not dry_run,
                    'removed_details': removed_lines if not dry_run else []
                })
                
            except Exception as e:
                cleanup_actions.append({
                    'file': str(file_path),
                    'error': str(e)
                })
        
        return {
            'dry_run': dry_run,
            'actions': cleanup_actions,
            'summary': {
                'files_processed': len([a for a in cleanup_actions if 'error' not in a]),
                'total_lines_removed': sum(a.get('removed_lines', 0) for a in cleanup_actions),
                'errors': [a for a in cleanup_actions if 'error' in a]
            }
        }
    
    def get_production_ready_config(self) -> str:
        """生成生产环境就绪的日志配置建议"""
        return '''
# 生产环境日志配置建议

## 保留的核心日志：
1. [SUPERVISION] 前缀的重要业务日志
2. [VISION_AI] 前缀的AI分析结果日志
3. 错误和警告级别的日志
4. 关键业务流程的状态变更日志

## 移除的测试日志：
1. 带有【TEST_ENHANCEMENT】标记的详细调试日志
2. 包含特殊emoji的美化日志格式
3. 树形结构的详细追踪日志
4. DEBUG级别的详细处理流程日志

## 建议的日志级别设置：
- 控制台输出：WARNING及以上
- 文件记录：INFO及以上
- 特殊调试：仅在需要时临时启用
'''

# 便捷函数
def run_log_analysis(project_path: str = None) -> Dict:
    """运行日志分析"""
    tool = LogCleanupTool(project_path)
    return tool.generate_cleanup_report()

def run_log_cleanup(project_path: str = None, dry_run: bool = True) -> Dict:
    """运行日志清理"""
    tool = LogCleanupTool(project_path)
    return tool.cleanup_test_logs(dry_run=dry_run)

def get_production_recommendations() -> str:
    """获取生产环境推荐配置"""
    tool = LogCleanupTool()
    return tool.get_production_ready_config()