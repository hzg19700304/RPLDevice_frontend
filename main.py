#!/usr/bin/env python3
# flake8: noqa
"""
钢轨电位限制柜人机界面主程序
Rail Potential Limiting Device HMI Main Application
"""

import asyncio
import logging
from pathlib import Path
from nicegui import ui, app
from config_manager import ConfigManager
from websocket_client import WebSocketClient
from ui_components import UIComponents
from pages.page_manager import PageManager


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RPLDeviceHMI:
    """钢轨电位限制柜人机界面主类"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.websocket_client = None
        self.page_manager = None
        self.ui_components = None
        
    async def initialize(self):
        """初始化应用"""
        try:
            # 加载配置
            await self.config.load_config()
            # logger.info("配置加载完成")
            
            # 初始化WebSocket客户端
            self.websocket_client = WebSocketClient(self.config)
            
            # 初始化页面管理器
            self.page_manager = PageManager(self.config, self.websocket_client)
            
            # 初始化UI组件（需要在页面管理器之后）
            self.ui_components = UIComponents(self.config, self.page_manager)
            
            # 设置UI主题和样式
            self._setup_ui_theme()
            
            # 创建主界面
            self._create_main_layout()

            # ⭐ 注册 WebSocket 连接状态回调
            self.websocket_client.register_connection_callback(
                self._on_websocket_connection_changed)
            
            # ⭐ 注册 connection_status 消息回调（串口状态现在通过connection_status发送）
            self.websocket_client.register_data_callback(
                'connection_status', self._on_connection_status_received)
            
            # 保留serial_status回调以兼容旧版本
            self.websocket_client.register_data_callback(
                'serial_status', self._on_serial_status_received)
            
            # logger.info("数据通过WebSocket获取")  # 注释掉调试信息
            
            logger.info("应用初始化完成")
            
        except Exception as e:
            logger.error(f"应用初始化失败: {e}")
            raise
    
    def _setup_ui_theme(self):
        """设置UI主题"""
        # 获取字体配置
        font_config = self.config.get_font_config()
        # logger.info(f"字体配置: {font_config}")  # 注释掉调试信息
        
        enable_responsive = font_config.get('enable_responsive_font', True)
        scale_factor = font_config.get('font_scale_factor', 1.0)
        
        # 基础字体大小
        base_size = int(font_config.get('base_font_size', 14) * scale_factor)
        title_size = int(font_config.get('title_font_size', 20) * scale_factor)
        menu_size = int(font_config.get('menu_font_size', 18) * scale_factor)
        status_size = int(font_config.get('status_font_size', 12) * scale_factor)
        
        # 获取布局配置
        layout_config = self.config.get_layout_config()
        min_width = layout_config.get('min_window_width', 1200)
        
        # logger.info(f"计算后的字体大小 - 基础: {base_size}, 标题: {title_size}, 菜单: {menu_size}, 状态: {status_size}")  # 注释掉调试信息
        # logger.info(f"响应式字体: {enable_responsive}, 缩放因子: {scale_factor}")  # 注释掉调试信息
        # logger.info(f"窗口最小宽度: {min_width}px")  # 注释掉调试信息
        
        # 根据配置生成字体样式
        if enable_responsive:
            # 响应式字体
            base_font = f"max({base_size-2}px, min(2vw, {base_size+4}px))"
            title_font = f"max({title_size-4}px, min(3vw, {title_size+4}px))"
            menu_font = f"max({menu_size-2}px, min(2.5vw, {menu_size+6}px))"
            status_font = f"max({status_size-2}px, min(1.8vw, {status_size+4}px))"
        else:
            # 固定字体大小
            base_font = f"{base_size}px"
            title_font = f"{title_size}px"
            menu_font = f"{menu_size}px"
            status_font = f"{status_size}px"
        
        # logger.info(f"生成的CSS字体样式 - 基础: {base_font}, 标题: {title_font}, 菜单: {menu_font}, 状态: {status_font}")  # 注释掉调试信息
        
        # 设置全局样式
        ui.add_head_html(f'''
        <style>
        /* 全局样式 - 去掉滚动条，适应屏幕，设置最小宽度 */
        html, body {{
            overflow: hidden !important;
            height: 100vh !important;
            margin: 0 !important;
            padding: 0 !important;
            min-width: {min_width}px !important;
        }}
        
        .q-page-container {{
            overflow: hidden !important;
        }}
        
        .q-drawer {{
            background-color: #2C3E50 !important;
        }}
        .q-header {{
            background-color: #2C3E50 !important;
        }}
        .q-footer {{
            background-color: #ECF0F1 !important;
            color: #2C3E50 !important;
        }}
        .q-btn {{
            min-height: 40px !important;
            border-radius: 4px !important;
            font-size: {base_font} !important;
        }}
        .q-input {{
            min-height: 40px !important;
            font-size: {base_font} !important;
        }}
        .q-select {{
            min-height: 40px !important;
            font-size: {base_font} !important;
        }}
        .q-checkbox {{
            font-size: {base_font} !important;
        }}
        .q-card {{
            border-radius: 6px !important;
            padding: 12px !important;
        }}
        .q-table th {{
            background-color: #ECF0F1 !important;
            height: 40px !important;
            font-size: {base_font} !important;
        }}
        .q-table td {{
            min-height: 36px !important;
            font-size: {base_font} !important;
        }}
        .touch-friendly {{
            min-width: 44px !important;
            min-height: 44px !important;
        }}
        
        /* 全局响应式字体设置 */
        body, .q-body {{
            font-size: {base_font} !important;
        }}
        
        /* 标题字体 */
        h1, h2, h3, h4, h5, h6, .text-h1, .text-h2, .text-h3, .text-h4, .text-h5, .text-h6 {{
            font-size: {title_font} !important;
        }}
        
        /* 普通文本 */
        p, span, div, .text-body1, .text-body2 {{
            font-size: {base_font} !important;
        }}
        
        /* 标签文本 */
        .q-field__label, .q-item__label {{
            font-size: {base_font} !important;
        }}
        
        /* 菜单字体 */
        .menu-text {{
            font-size: {menu_font} !important;
        }}
        
        /* 状态文本字体 */
        .status-text {{
            font-size: {status_font} !important;
        }}

        </style>
        ''')
    
    def _create_main_layout(self):
        """创建主界面布局"""
        # 创建顶部栏
        self.ui_components.create_header()
        
        # 创建左侧导航栏
        self.ui_components.create_left_drawer()
        
        # 创建主内容区域
        self.page_manager.setup_pages()
        
        # 创建底部状态栏
        self.ui_components.create_footer()

    async def _on_websocket_connection_changed(self, connected: bool):
        """WebSocket 连接状态变化回调"""
        # if connected:
        #     logger.info("WebSocket连接成功")
        # else:
        #     logger.warning("WebSocket连接断开")
        if self.ui_components:
            # 更新 UI 显示
            self.ui_components.update_connection_status(connected, 'websocket')
    
    async def _on_connection_status_received(self, data: dict):
        """处理连接状态消息回调（包含串口状态）"""
        try:
            websocket_connected = data.get('websocket_connected', False)
            hmi_serial_available = data.get('hmi_serial_available', False)
            scada_serial_available = data.get('scada_serial_available', False)
            
            # logger.info(f"收到连接状态消息 - WebSocket: {websocket_connected}, HMI串口: {hmi_serial_available}, SCADA串口: {scada_serial_available}")
            # logger.info(f"完整数据: {data}")
            
            if self.ui_components:
                # 控制板串口状态直接使用HMI串口状态（它们是同一个串口）
                self.ui_components.update_connection_status(hmi_serial_available, 'control_board')
                # 更新PSCADA串口状态（SCADA串口）
                self.ui_components.update_connection_status(scada_serial_available, 'pscada')
                # 更新WebSocket连接状态
                self.ui_components.update_connection_status(websocket_connected, 'websocket')
                
        except Exception as e:
            logger.error(f"处理连接状态消息失败: {e}")
    
    async def _on_serial_status_received(self, data: dict):
        """处理串口状态消息回调（兼容旧版本）"""
        try:
            hmi_serial_available = data.get('hmi_serial_available', False)
            scada_serial_available = data.get('scada_serial_available', False)
            control_board_serial_available = data.get('control_board_serial_available', False)
            
            logger.info(f"收到串口状态消息（旧版本） - HMI: {hmi_serial_available}, SCADA: {scada_serial_available}, control_board: {control_board_serial_available}")
            logger.info(f"完整数据: {data}")
            
            if self.ui_components:
                # 更新控制板串口状态（HMI串口）
                self.ui_components.update_connection_status(hmi_serial_available, 'control_board')
                # 更新PSCADA串口状态（SCADA串口）
                self.ui_components.update_connection_status(scada_serial_available, 'pscada')
                
        except Exception as e:
            logger.error(f"处理串口状态消息失败: {e}")
    
    def cleanup(self):
        """清理资源"""
        if self.websocket_client:
            self.websocket_client.close()
    
    async def start_websocket(self):
        """启动WebSocket连接"""
        if self.websocket_client:
            logger.info("开始连接WebSocket服务器")
            result = await self.websocket_client.connect()
            logger.info(f"WebSocket连接结果: {result}")
            
            # 获取连接状态
            status = self.websocket_client.get_connection_status()
            logger.info(f"WebSocket连接状态: {status}")
    
    async def shutdown(self):
        """关闭应用"""
        if self.websocket_client:
            await self.websocket_client.disconnect()
        logger.info("应用已关闭")

# 全局应用实例
hmi_app = RPLDeviceHMI()

@ui.page('/')
async def index():
    """主页面"""
    await hmi_app.initialize()
    
    # 确保WebSocket连接在页面加载完成后建立
    ui.timer(1.0, hmi_app.start_websocket, once=True)

if __name__ in {"__main__", "__mp_main__"}:
    # 配置NiceUI应用
    ui.run(
        title="钢轨电位限制柜人机界面",
        port=8080,
        host="0.0.0.0",
        favicon="🚄",
        dark=False,
        show=False  # 不自动打开浏览器
    )