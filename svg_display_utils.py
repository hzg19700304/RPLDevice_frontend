"""
SVG显示工具模块
提供版本兼容的SVG显示功能，处理NiceGUI不同版本中ui.html sanitize参数的变化
"""

import nicegui
from nicegui import ui
import inspect


def get_ui_html_signature():
    """
    获取ui.html函数的签名信息
    """
    try:
        return inspect.signature(ui.html)
    except Exception as e:
        print(f"获取ui.html签名失败: {e}")
        return None


def create_svg_display(svg_content, classes='w-full'):
    """
    版本兼容的SVG显示函数
    
    根据NiceGUI版本自动处理sanitize参数：
    - NiceGUI 3.x: sanitize参数为必填，可接受False或自定义函数
    - NiceGUI 2.x及更早版本: 可能没有sanitize参数
    
    Args:
        svg_content (str): SVG内容字符串
        classes (str): CSS类名，默认为'w-full'
    
    Returns:
        ui.html对象
    """
    try:
        # 获取当前NiceGUI版本
        version = nicegui.__version__
        major_version = int(version.split('.')[0])
        
        # 获取ui.html的签名
        signature = get_ui_html_signature()
        
        if signature:
            # 检查sanitize参数是否存在
            has_sanitize = 'sanitize' in signature.parameters
            
            if has_sanitize:
                # NiceGUI 3.x版本，sanitize参数必填
                if major_version >= 3:
                    # 对于SVG内容，禁用sanitize以避免破坏SVG结构
                    return ui.html(svg_content, sanitize=False).classes(classes)
                else:
                    # 早期版本，尝试使用sanitize=False
                    try:
                        return ui.html(svg_content, sanitize=False).classes(classes)
                    except TypeError:
                        # 如果sanitize参数不被接受，回退到无参数版本
                        return ui.html(svg_content).classes(classes)
            else:
                # 没有sanitize参数的旧版本
                return ui.html(svg_content).classes(classes)
        else:
            # 无法获取签名信息，尝试最安全的方式
            try:
                # 首先尝试带sanitize=False
                return ui.html(svg_content, sanitize=False).classes(classes)
            except TypeError:
                # 如果失败，回退到无参数版本
                return ui.html(svg_content).classes(classes)
                
    except Exception as e:
        print(f"创建SVG显示时出错: {e}")
        # 最后的回退方案
        try:
            return ui.html(svg_content).classes(classes)
        except Exception as final_error:
            print(f"SVG显示创建失败: {final_error}")
            # 返回一个空的html元素作为占位符
            return ui.html("<div>SVG加载失败</div>").classes(classes)


def test_svg_display_compatibility():
    """
    测试SVG显示兼容性
    """
    print(f"当前NiceGUI版本: {nicegui.__version__}")
    
    signature = get_ui_html_signature()
    if signature:
        print(f"ui.html函数签名: {signature}")
        
        # 测试简单SVG
        test_svg = """<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
            <circle cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="red" />
        </svg>"""
        
        try:
            result = create_svg_display(test_svg)
            print("✓ SVG显示创建成功")
            return True
        except Exception as e:
            print(f"✗ SVG显示创建失败: {e}")
            return False
    else:
        print("无法获取ui.html函数签名")
        return False


if __name__ == "__main__":
    # 运行兼容性测试
    test_svg_display_compatibility()