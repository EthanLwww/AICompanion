#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 app_finaluse.py 中提取 LOAD_JS 并保存到 static/js/load_js.js
"""
import os

# 读取原始文件
with open('app_finaluse.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 查找 LOAD_JS 的位置
start_marker = 'LOAD_JS = """'
end_marker = '"""\n\n# 创建Gradio界面'

start = content.find(start_marker)
end = content.find(end_marker)

if start != -1 and end != -1:
    # 提取 LOAD_JS 内容（不包括引号）
    js_content = content[start + len(start_marker):end]
    
    # 确保 companion_test_2.0/static/js 目录存在
    os.makedirs('companion_test_2.0/static/js', exist_ok=True)
    
    # 写入文件
    with open('companion_test_2.0/static/js/load_js.js', 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    print('✓ LOAD_JS extracted successfully')
    print(f'✓ File saved to: companion_test_2.0/static/js/load_js.js')
    print(f'✓ File size: {len(js_content)} bytes')
    
    # 也复制到 ai-companion/static/js
    os.makedirs('ai-companion/static/js', exist_ok=True)
    with open('ai-companion/static/js/load_js.js', 'w', encoding='utf-8') as f:
        f.write(js_content)
    print(f'✓ Also saved to: ai-companion/static/js/load_js.js')
else:
    print('✗ Failed to find LOAD_JS markers')
    print(f'start found: {start != -1}, end found: {end != -1}')
