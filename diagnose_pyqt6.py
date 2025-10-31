#!/usr/bin/env python3
"""PyQt6 DLL 加载诊断脚本"""

import sys
import os

print("=" * 60)
print("PyQt6 DLL 加载诊断")
print("=" * 60)

# 1. 检查 Python 版本
print(f"\n1. Python 版本: {sys.version}")
print(f"   可执行文件: {sys.executable}")

# 2. 检查 PyQt6 是否可以导入
print("\n2. 尝试导入 PyQt6 模块...")
try:
    import PyQt6
    print(f"   ✓ PyQt6 成功导入: {PyQt6.__file__}")
except ImportError as e:
    print(f"   ✗ PyQt6 导入失败: {e}")
    sys.exit(1)

# 3. 检查 PyQt6.QtCore
print("\n3. 尝试导入 PyQt6.QtCore...")
try:
    from PyQt6 import QtCore
    print(f"   ✓ QtCore 成功导入")
except ImportError as e:
    print(f"   ✗ QtCore 导入失败: {e}")
    print(f"   错误详情: {type(e).__name__}: {e}")

# 4. 检查 PyQt6.QtWidgets
print("\n4. 尝试导入 PyQt6.QtWidgets...")
try:
    from PyQt6 import QtWidgets
    print(f"   ✓ QtWidgets 成功导入")
except ImportError as e:
    print(f"   ✗ QtWidgets 导入失败: {e}")

# 5. 检查 PyQt6-Qt6 DLL
print("\n5. 检查 PyQt6-Qt6 库文件...")
try:
    import PyQt6_Qt6
    print(f"   ✓ PyQt6-Qt6 已安装: {PyQt6_Qt6.__file__}")
except ImportError as e:
    print(f"   ✗ PyQt6-Qt6 未找到: {e}")

# 6. 检查系统路径
print("\n6. Python 系统路径:")
for i, path in enumerate(sys.path[:5], 1):
    print(f"   {i}. {path}")

# 7. 检查依赖
print("\n7. 检查关键依赖...")
deps = ['PyQt6', 'PyQt6-Qt6', 'PyQt6-sip', 'geopandas', 'shapely', 'pandas']
for dep in deps:
    try:
        mod = __import__(dep)
        print(f"   ✓ {dep}")
    except ImportError:
        print(f"   ✗ {dep} 缺失")

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)
