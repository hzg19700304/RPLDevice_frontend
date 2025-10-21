我来帮你梳理一下通过 WebSocket 传送数据到主接线图的完整流程:

## 数据传输流程

### 1. WebSocket 连接建立 (`websocket_client.py`)

```python
# 在 main.py 中启动 WebSocket 连接
await hmi_app.start_websocket()
```

### 2. 注册数据回调 (`main_diagram_page.py`)

在 `MainDiagramPage.__init__()` 中调用 `_setup_svg_updater()`:

```python
def _setup_svg_updater(self):
    if self.websocket_client:
        # 注册两个数据回调函数
        self.websocket_client.register_data_callback('analog_data', self._handle_analog_data_callback)
        self.websocket_client.register_data_callback('switch_io', self._handle_digital_data_callback)
```

### 3. 接收 WebSocket 消息 (`websocket_client.py`)

```python
async def _receive_loop(self):
    """接收消息循环"""
    async for message in self.websocket:
        data = json.loads(message)
        await self._handle_message(data)

async def _handle_message(self, message: Dict[str, Any]):
    """处理接收到的消息"""
    message_type = message.get('type')
    data = message.get('data', {})
    
    # 调用注册的回调函数
    if message_type in self.data_callbacks:
        for callback in self.data_callbacks[message_type]:
            await callback(data)
```

### 4. 处理数据并更新 SVG (`main_diagram_page.py`)

**模拟量数据处理:**

```python
async def _handle_analog_data_callback(self, data):
    """处理模拟量数据回调"""
    if isinstance(data, list):
        for item in data:
            name = item.get('name', '')
            value = item.get('physical_value')
            unit = item.get('unit', '')
            
            # 根据数据名称更新对应的控件
            if '支路电压1' in name or '电压' in name:
                display_value = f"{value:.1f}{unit}"
                self.queue_svg_update('sv1', display_value, is_normal)
            elif '支路1电流' in name:
                display_value = f"{value:.1f}{unit}"
                self.queue_svg_update('sa1', display_value, is_normal)
            elif '支路2电流' in name:
                display_value = f"{value:.1f}{unit}"
                self.queue_svg_update('sa2', display_value, is_normal)
```

**开关量数据处理:**

```python
async def _handle_digital_data_callback(self, data: dict):
    """处理开关量数据回调"""
    if isinstance(data, dict):
        output_data = data.get('output', {})
        
        if 'bit0' in output_data:
            km1_value = output_data['bit0']
            state_text = '合位' if km1_value == 1 else '分位'
            self.queue_svg_update('km1', state_text, True)
```

### 5. 队列化更新 SVG

```python
def queue_svg_update(self, control_id: str, value: str, is_normal: bool = True):
    """将 SVG 更新请求加入队列"""
    update_data = {
        'control_id': control_id,
        'value': value,
        'is_normal': is_normal,
        'timestamp': datetime.now()
    }
    self.pending_svg_updates.append(update_data)
```

### 6. 定时处理队列并更新 SVG

```python
# 在 create_page() 中创建定时器
ui.timer(0.1, self.process_pending_svg_updates)

def process_pending_svg_updates(self):
    """处理待更新的 SVG 控件"""
    if not self.pending_svg_updates:
        return
    
    updates_to_process = self.pending_svg_updates.copy()
    self.pending_svg_updates.clear()
    
    for update in updates_to_process:
        self.update_svg_control(
            update['control_id'],
            update['value'], 
            update['is_normal']
        )
```

### 7. 通过 JavaScript 更新 SVG 元素

```python
def update_svg_control(self, control_id: str, value: str, is_normal: bool = True):
    """更新 SVG 中的控件显示值"""
    # 对于文本元素
    js_code = f"""
    const el = document.getElementById('{el_id}');
    if (el) {{
        const t = el.querySelector('tspan');
        (t||el).textContent = '{value}';
        (t||el).setAttribute('fill', '{color}');
    }}
    """
    ui.run_javascript(js_code)
    
    # 对于 KM1 开关状态(图形变化)
    js_code = f"""
    const isClosed = ['合位','闭合','ON','1','True','true'].includes('{value}');
    // 更新触点状态(显示/隐藏斜线和竖线)
    """
    ui.run_javascript(js_code)
```

## 关键函数调用链

```
WebSocket Server 发送数据
    ↓
websocket_client._receive_loop()
    ↓
websocket_client._handle_message()
    ↓
main_diagram_page._handle_analog_data_callback() 或
main_diagram_page._handle_digital_data_callback()
    ↓
main_diagram_page.queue_svg_update()
    ↓
main_diagram_page.process_pending_svg_updates() (定时器触发)
    ↓
main_diagram_page.update_svg_control()
    ↓
ui.run_javascript() (更新 DOM)
```

## 数据格式示例

**模拟量数据:**

```python
{
    'type': 'analog_data',
    'data': [
        {'name': '支路电压1', 'physical_value': 220.5, 'unit': 'V'},
        {'name': '支路1电流', 'physical_value': 3.2, 'unit': 'A'}
    ]
}
```

**开关量数据:**

```python
{
    'type': 'switch_io',
    'data': {
        'output': {'bit0': 1},  # KM1 合位
        'input': {}
    }
}
```

这个设计使用了回调机制和队列化更新,确保 UI 更新不会阻塞 WebSocket 接收,是一个典型的异步数据处理模式。