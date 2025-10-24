"""
主接线图页面
Main Diagram Page
"""
# flake8: noqa
import logging
from datetime import datetime
from nicegui import ui

logger = logging.getLogger(__name__)


class MainDiagramPage:
    """主接线图页面类"""
    
    def __init__(self, config_manager, websocket_client):
        self.config = config_manager
        self.websocket_client = websocket_client
        self.image_container = None
        self.diagram_image = None
        self.pending_svg_updates = []
        
        # 加载模拟量通道配置
        self.analog_channel_config = self.config.get_analog_channel_config()
        self.channel_id_map = {}  # 通道号到SVG控件ID的映射
        
        # 解析模拟量通道配置
        self._parse_analog_channel_config()
        
        # 立即注册WebSocket回调
        self._setup_svg_updater()
    
    def _parse_analog_channel_config(self):
        """解析模拟量通道配置"""
        for key, value in self.analog_channel_config.items():
            # 配置格式：通道号 = 显示名称,单位,SVG控件ID
            if key.startswith('通道'):
                parts = value.split(',')
                if len(parts) >= 3:
                    channel_num = key[2:]  # 提取通道号
                    display_name = parts[0].strip()
                    unit = parts[1].strip()
                    svg_id = parts[2].strip()
                    
                    # 创建通道号到SVG控件ID的映射
                    self.channel_id_map[channel_num] = {
                        'display_name': display_name,
                        'unit': unit,
                        'svg_id': svg_id
                    }
        
    def create_page(self) -> ui.column:
        """创建主接线图页面"""
        # 获取字体配置
        font_config = self.config.get_font_config()
        enable_responsive = font_config.get('enable_responsive_font', True)
        scale_factor = font_config.get('font_scale_factor', 1.0)
        status_size = int(font_config.get('status_font_size', 12) * scale_factor)
        
        # 根据配置生成字体样式
        if enable_responsive:
            svg_font = f"max({status_size-2}px, min(1.8vw, {status_size+2}px))"
        else:
            svg_font = f"{status_size}px"
        
        # 添加响应式字体CSS - 主要用于SVG中的文本
        ui.add_head_html(f'''
        <style>
        .svg-container text {{
            font-size: {svg_font} !important;
        }}
        .svg-container tspan {{
            font-size: {svg_font} !important;
        }}
        /* 确保SVG文本也有响应式字体 */
        svg text {{
            font-size: {svg_font} !important;
        }}
        svg tspan {{
            font-size: {svg_font} !important;
        }}
        </style>
        ''')
        
        with ui.card().classes('w-full h-full'):
            # 使用滚动区域解决图片裁剪问题
            scroll_height = 'height: calc(100vh - 120px);'  # 计算合适的滚动区域高度，确保底部边框可见
            with ui.scroll_area().classes('w-full').style(scroll_height):
                with ui.column().classes('w-full items-center p-4'):
                    # 创建图片容器
                    container_classes = 'w-full items-center relative'
                    self.image_container = ui.column().classes(container_classes)
                    with self.image_container:
                        self._create_svg_display()
                    
                    # 创建定时器来处理待更新的SVG控件
                    ui.timer(0.1, self.process_pending_svg_updates)
        
        return self.image_container
    
    def _create_svg_display(self):
        """创建SVG显示"""
        try:
            # SVG文件在项目根目录下，直接使用文件名
            svg_path = '一次回路图.svg'
            
            # logger.info(f"加载SVG文件: {svg_path}")
            
            # 使用SVG图片
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_html = f.read()
            wrapped_svg = f'<div class="svg-container">{svg_html}</div>'
            self.diagram_image = ui.html(wrapped_svg, sanitize=False).classes('w-full')
            
            # 添加基本样式
            ui.add_head_html('''
            <style>
            .svg-container { width: 100%; max-width: 100%; overflow: hidden; }
            .svg-container svg { width: 100% !important; height: auto !important; }
            </style>
            ''')
            
            logger.info("SVG文件加载成功")
            
        except FileNotFoundError as e:
            logger.error(f"SVG文件未找到: {e}")
            ui.label('SVG文件未找到，请确认"一次回路图.svg"在项目根目录').classes('text-negative')
        except Exception as e:
            logger.error(f"创建SVG显示失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            ui.label(f'SVG文件加载失败: {str(e)}').classes('text-negative')
    
    def _setup_svg_updater(self):
        """设置SVG控件更新器"""
        if self.websocket_client:
            # 注册数据回调
            self.websocket_client.register_data_callback('analog_data', self._handle_analog_data_callback)
            # switch_io数据类型已合并到system_status中，改为注册system_status回调
            self.websocket_client.register_data_callback('system_status', self._handle_system_status_callback)
            # logger.info("已注册WebSocket数据回调")
        else:
            logger.warning("WebSocket客户端未初始化")
    
    def queue_svg_update(self, control_id: str, value: str, is_normal: bool = True):
        """将SVG更新请求加入队列"""
        update_data = {
            'control_id': control_id,
            'value': value,
            'is_normal': is_normal,
            'timestamp': datetime.now()
        }
        self.pending_svg_updates.append(update_data)
        # logger.info(f"SVG更新已加入队列: {control_id} = {value}")

    def process_pending_svg_updates(self):
        """处理待更新的SVG控件"""
        if not self.pending_svg_updates:
            return
            
        updates_to_process = self.pending_svg_updates.copy()
        self.pending_svg_updates.clear()
        
        for update in updates_to_process:
            try:
                self.update_svg_control(
                    update['control_id'],
                    update['value'], 
                    update['is_normal']
                )
            except Exception as e:
                logger.error(f"处理SVG更新失败: {e}")
    
    def update_svg_control(self, control_id: str, value: str, is_normal: bool = True):
        """更新SVG中的控件显示值"""
        try:
            # 对于KM1，只处理图形变化，不更新文本
            if control_id.lower() == 'km1':
                # logger.info(f"更新KM1图形状态: {value}")
                js_code = f"""
                console.log('更新KM1状态: {value}');
                // KM1特殊处理
                if (true) {{
                    console.log('处理KM1状态变化');
                    const isClosed = ['合位','闭合','ON','1','True','true'].includes('{value}');
                    console.log('KM1是否合位:', isClosed);
                    
                    // 更新触点状态
                    const pairs = [
                      ['KM1_L_diag','KM1_L_vert'],
                      ['KM1_R_diag','KM1_R_vert'],
                    ];
                    pairs.forEach(([diagId, vertId]) => {{
                      const diag = document.getElementById(diagId);
                      const vert = document.getElementById(vertId);
                      console.log('处理触点对:', diagId, vertId, diag, vert);
                      
                      if (isClosed) {{
                        // 合位：显示竖线，隐藏斜线
                        if (diag) {{
                          diag.style.display = 'none';
                          diag.setAttribute('stroke-opacity','0');
                        }}
                        if (vert) {{
                          vert.style.display = '';
                          vert.setAttribute('stroke-opacity','1');
                          vert.setAttribute('stroke', '#ff0000');
                          vert.setAttribute('stroke-width', '3');
                        }}
                      }} else {{
                        // 分位：显示斜线，隐藏竖线
                        if (vert) {{
                          vert.style.display = 'none';
                          vert.setAttribute('stroke-opacity','0');
                        }}
                        if (diag) {{
                          diag.style.display = '';
                          diag.setAttribute('stroke-opacity','1');
                          diag.setAttribute('stroke', '#000000');
                          diag.setAttribute('stroke-width', '2');
                        }}
                      }}
                    }});
                }}
                """
                ui.run_javascript(js_code)
                return
            
            # 处理模拟量控件的文本更新
            # 首先尝试从通道配置中查找
            el_id = None
            for channel_num, channel_info in self.channel_id_map.items():
                if control_id.lower() == channel_info['svg_id'].lower():
                    # 直接使用配置文件中的SVG控件ID，不再添加_value后缀
                    el_id = channel_info['svg_id']
                    break
            
            # 如果在通道配置中找不到，使用默认映射
            if not el_id:
                default_id_map = {
                    'sv1': 'SV1_value',
                    'sv2': 'SV2_value',
                    'sa1': 'SA1_value', 
                    'sa2': 'SA2_value',
                }
                el_id = default_id_map.get(control_id.lower())
            
            if not el_id:
                logger.warning(f'未知控件: {control_id}')
                return

            # logger.info(f"更新SVG控件: {control_id} -> {el_id} = {value}")
            
            js_code = f"""
            console.log('更新SVG控件: {control_id} -> {el_id} = {value}');
            const el = document.getElementById('{el_id}');
            console.log('找到元素:', el);
            if (el) {{
                const t = el.querySelector('tspan');
                console.log('找到tspan:', t);
                (t||el).textContent = '{value}';
                (t||el).setAttribute('fill', '#00ff00');
                console.log('更新完成');
            }} else {{
                console.error('未找到元素:', '{el_id}');
            }}
            """
            ui.run_javascript(js_code)
        except Exception as e:
            logger.error(f"更新SVG控件失败: {e}")
    
    async def _handle_analog_data_callback(self, data):
        """处理模拟量数据回调"""
        try:
            # logger.info(f"主接线图页面收到模拟量数据: {data}")
            
            if isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue
                        
                    name = item.get('name', '')
                    value = item.get('physical_value')
                    unit = item.get('unit', '')
                    
                    # logger.info(f"处理模拟量项: name={name}, value={value}, unit={unit}")
                    
                    # 使用通用通道名称处理模拟量数据
                    # 遍历通道配置，查找匹配的通道
                    for channel_num, channel_info in self.channel_id_map.items():
                        display_name = channel_info['display_name']
                        svg_id = channel_info['svg_id']  # 直接使用配置文件中的SVG控件ID
                        channel_unit = channel_info['unit']
                        
                        # 检查是否匹配当前通道
                        if display_name in name:
                            # 检查SVG控件ID是否为空，为空则跳过更新（保留通道）
                            if not svg_id:
                                # logger.info(f"通道{channel_num}({display_name})为保留通道，跳过更新")
                                continue
                                
                            display_value = f"{value:.1f}{channel_unit}" if value is not None else f"0{channel_unit}"
                            # logger.info(f"更新通道{channel_num}({svg_id}): {display_value}")
                            # 直接传递SVG控件ID，不再需要转换
                            self.queue_svg_update(svg_id, display_value, True)
                            break
            else:
                logger.warning(f"模拟量数据格式不正确，期望列表，实际: {type(data)}")
        except Exception as e:
            logger.error(f"处理模拟量数据失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    async def _handle_system_status_callback(self, data: dict):
        """处理系统状态数据回调（包含开关量信息）"""
        try:
            # logger.info(f"主接线图页面收到系统状态数据: {data}")
            
            if isinstance(data, dict):
                # 从system_status数据中提取开关量输出信息
                switch_output = data.get('switch_output', {})
                
                # logger.info(f"开关量输出: {switch_output}")
                
                if 'bit0' in switch_output:
                    km1_value = switch_output['bit0']
                    state_text = '合位' if km1_value == 1 else '分位'
                    # logger.info(f"KM1状态更新: bit0={km1_value} -> {state_text}")
                    self.queue_svg_update('km1', state_text, True)
                else:
                    logger.warning("开关量输出中未找到bit0 (KM1)")
            else:
                logger.warning(f"系统状态数据格式不正确，期望字典，实际: {type(data)}")
        except Exception as e:
            logger.error(f"处理系统状态数据失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    async def _handle_digital_data_callback(self, data: dict):
        """处理开关量数据回调（已废弃，保留用于兼容性）"""
        logger.warning("_handle_digital_data_callback方法已废弃，switch_io数据类型已合并到system_status中")
        # 可以保留原有逻辑作为后备，但应该不会再被调用