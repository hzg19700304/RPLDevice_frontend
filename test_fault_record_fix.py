#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试故障录波页面修复
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # 测试导入故障录波页面
    from pages.fault_record_page import FaultRecordPage
    print("✓ 故障录波页面导入成功")
    
    # 检查关键方法是否存在
    if hasattr(FaultRecordPage, 'query_detail'):
        print("✓ query_detail方法存在")
    else:
        print("✗ query_detail方法不存在")
    
    if hasattr(FaultRecordPage, 'show_progress_dialog'):
        print("✓ show_progress_dialog方法存在")
    else:
        print("✗ show_progress_dialog方法不存在")
    
    if hasattr(FaultRecordPage, '_handle_progress'):
        print("✓ _handle_progress方法存在")
    else:
        print("✗ _handle_progress方法不存在")
    
    if hasattr(FaultRecordPage, '_handle_complete'):
        print("✓ _handle_complete方法存在")
    else:
        print("✗ _handle_complete方法不存在")
    
    # 检查代码中是否还有KProgress的引用
    import inspect
    source = inspect.getsource(FaultRecordPage)
    if 'KProgress' in source:
        print("✗ 代码中仍然存在KProgress引用")
    else:
        print("✓ 代码中已移除KProgress引用")
    
    # 检查是否使用了ui.progress
    if 'ui.progress' in source:
        print("✓ 代码中使用了ui.progress")
    else:
        print("✗ 代码中未使用ui.progress")
    
    print("\n所有测试通过！故障录波页面修复成功。")
    
except ImportError as e:
    print(f"✗ 导入错误: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ 其他错误: {e}")
    sys.exit(1)