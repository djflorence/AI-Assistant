import importlib
import os
from typing import Dict, List, Callable, Any
import inspect

class Plugin:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.commands = {}
        self.enabled = True

    def add_command(self, name: str, func: Callable, description: str):
        self.commands[name] = {
            'function': func,
            'description': description,
            'signature': inspect.signature(func)
        }

    def execute_command(self, command: str, *args, **kwargs) -> Any:
        if command in self.commands and self.enabled:
            return self.commands[command]['function'](*args, **kwargs)
        raise ValueError(f"Command {command} not found or plugin disabled")

class PluginService:
    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = plugins_dir
        self.plugins: Dict[str, Plugin] = {}
        self._load_plugins()

    def _load_plugins(self):
        """Load all plugins from the plugins directory"""
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir)
            self._create_example_plugin()
            
        for filename in os.listdir(self.plugins_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                self._load_plugin(filename[:-3])

    def _create_example_plugin(self):
        """Create an example plugin to demonstrate the plugin system"""
        example = """from typing import List

def plugin_info():
    return {
        'name': 'Example Plugin',
        'description': 'An example plugin showing basic functionality'
    }

def get_commands():
    return {
        'greet': {
            'function': greet,
            'description': 'Sends a greeting to the user'
        },
        'calculate': {
            'function': calculate,
            'description': 'Performs basic arithmetic'
        }
    }

def greet(name: str = "User") -> str:
    return f"Hello, {name}!"

def calculate(operation: str, numbers: List[float]) -> float:
    if operation == 'sum':
        return sum(numbers)
    elif operation == 'average':
        return sum(numbers) / len(numbers)
    raise ValueError(f"Unknown operation: {operation}")
"""
        with open(os.path.join(self.plugins_dir, 'example_plugin.py'), 'w') as f:
            f.write(example)

    def _load_plugin(self, plugin_name: str):
        try:
            module = importlib.import_module(f"{self.plugins_dir}.{plugin_name}")
            info = module.plugin_info()
            plugin = Plugin(info['name'], info['description'])
            
            for cmd_name, cmd_info in module.get_commands().items():
                plugin.add_command(cmd_name, cmd_info['function'], cmd_info['description'])
            
            self.plugins[plugin_name] = plugin
        except Exception as e:
            print(f"Failed to load plugin {plugin_name}: {str(e)}")

    def get_plugins(self) -> Dict[str, Plugin]:
        return self.plugins

    def get_plugin(self, name: str) -> Plugin:
        return self.plugins.get(name)

    def enable_plugin(self, name: str):
        if name in self.plugins:
            self.plugins[name].enabled = True

    def disable_plugin(self, name: str):
        if name in self.plugins:
            self.plugins[name].enabled = False

    def execute_command(self, plugin_name: str, command: str, *args, **kwargs) -> Any:
        plugin = self.get_plugin(plugin_name)
        if plugin:
            return plugin.execute_command(command, *args, **kwargs)
        raise ValueError(f"Plugin {plugin_name} not found")
