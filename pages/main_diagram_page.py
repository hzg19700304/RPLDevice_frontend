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
        
        # 立即注册WebSocket回调
        self._setup_svg_updater()
        
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
            scroll_height = 'height: calc(100vh - 100px);'
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
            self.diagram_image = ui.html(wrapped_svg).classes('w-full')
            
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
            id_map = {
                'sv1': 'SV1_value',
                'sa1': 'SA1_value', 
                'sa2': 'SA2_value',
                # 'km1': 'KM1_state',  # SVG中没有这个元素，只处理图形变化
            }
            el_id = id_map.get(control_id.lower())
            
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
            
            # 处理其他控件的文本更新
            if not el_id:
                logger.warning(f'未知控件: {control_id}')
                return

            # logger.info(f"更新SVG控件: {control_id} -> {el_id} = {value}")
            
            color = '#00ff00' if is_normal else '#ff0000'
            js_code = f"""
            console.log('更新SVG控件: {control_id} -> {el_id} = {value}');
            const el = document.getElementById('{el_id}');
            console.log('找到元素:', el);
            if (el) {{
                const t = el.querySelector('tspan');
                console.log('找到tspan:', t);
                (t||el).textContent = '{value}';
                (t||el).setAttribute('fill', '{color}');
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
                    is_normal = self._check_value_normal(name, value)
                    
                    # logger.info(f"处理模拟量项: name={name}, value={value}, unit={unit}")
                    
                    # 根据数据名称更新对应的控件
                    if '支路电压1' in name or '电压' in name:
                        display_value = f"{value:.1f}{unit}" if value is not None else "0V"
                        # logger.info(f"更新SV1: {display_value}")
                        self.queue_svg_update('sv1', display_value, is_normal)
                    elif '支路1电流' in name:
                        display_value = f"{value:.1f}{unit}" if value is not None else "0A"
                        # logger.info(f"更新SA1: {display_value}")
                        self.queue_svg_update('sa1', display_value, is_normal)
                    elif '支路2电流' in name:
                        display_value = f"{value:.1f}{unit}" if value is not None else "0A"
                        # logger.info(f"更新SA2: {display_value}")
                        self.queue_svg_update('sa2', display_value, is_normal)
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

    def _check_value_normal(self, name: str, value: float) -> bool:
        """检查数值是否正常"""
        if value is None:
            return False
        
        if '电压' in name or 'SV' in name:
            return 180.0 <= value <= 250.0
        elif '电流' in name or 'SA' in name:
            return 0.0 <= value <= 10.0
        
        return True