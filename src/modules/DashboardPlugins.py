import os
import sys
import importlib.util
from pathlib import Path
from typing import Dict, Callable, List, Optional
import threading


class DashboardPlugins:
    
    def __init__(self, app, WireguardConfigurations, directory: str = 'plugins'):
        self.directory = Path('plugins')
        self.loadedPlugins: dict[str, Callable] = {}
        self.errorPlugins: List[str] = []
        self.logger = app.logger
        self.WireguardConfigurations = WireguardConfigurations
        
    def startThreads(self):
        self.loadAllPlugins()
        self.executeAllPlugins()
    
    def preparePlugins(self) -> list[Path]:
        
        readyPlugins = []
        
        if not self.directory.exists():
            os.mkdir(self.directory)
            return []
        
        for plugin in self.directory.iterdir():
            if plugin.is_dir():
                codeFile = plugin / "main.py"
                if codeFile.exists():
                    self.logger.info(f"Prepared plugin: {plugin.name}")
                    readyPlugins.append(plugin)
            
        return readyPlugins
    
    def loadPlugin(self, path: Path) -> Optional[Callable]:
        pluginName = path.name
        codeFile = path / "main.py"
        
        try:
            spec = importlib.util.spec_from_file_location(
                f"WGDashboardPlugin_{pluginName}",
                codeFile
            )
            
            if spec is None or spec.loader is None:
                raise ImportError(f"Failed to create spec for {pluginName}")
            
            module = importlib.util.module_from_spec(spec)
            
            plugin_dir_str = str(path)
            if plugin_dir_str not in sys.path:
                sys.path.insert(0, plugin_dir_str)

            try:
                spec.loader.exec_module(module)
            finally:
                if plugin_dir_str in sys.path:
                    sys.path.remove(plugin_dir_str)

            if hasattr(module, 'main'):
                main_func = getattr(module, 'main')
                if callable(main_func):
                    self.logger.info(f"Successfully loaded plugin [{pluginName}]")
                    return main_func
                else:
                    raise AttributeError(f"'main' in {pluginName} is not callable")
            else:
                raise AttributeError(f"Plugin {pluginName} does not have a 'main' function")
            
        except Exception as e:
            self.logger.error(f"Failed to load the plugin [{pluginName}]. Reason: {str(e)}")
            self.errorPlugins.append(pluginName)
            return None
        
    def loadAllPlugins(self):
        self.loadedPlugins.clear()
        self.errorPlugins.clear()
        
        preparedPlugins = self.preparePlugins()
        
        for plugin in preparedPlugins:
            pluginName = plugin.name
            mainFunction = self.loadPlugin(plugin)
            
            if mainFunction:
                self.loadedPlugins[pluginName] = mainFunction
        if self.errorPlugins:
            self.logger.warning(f"Failed to load {len(self.errorPlugins)} plugin(s): {self.errorPlugins}")
    
    def executePlugin(self, pluginName: str):
        if pluginName not in self.loadedPlugins.keys():
            self.logger.error(f"Failed to execute plugin [{pluginName}]. Reason: Not loaded")
            return False
        
        plugin = self.loadedPlugins.get(pluginName)
        
        try:
            t = threading.Thread(target=plugin, args=(self.WireguardConfigurations,), daemon=True)
            t.name = f'WGDashboardPlugin_{pluginName}'
            t.start()
            
            if t.is_alive():
                self.logger.info(f"Execute plugin [{pluginName}] success. PID: {t.native_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to execute plugin [{pluginName}]. Reason: {str(e)}")
            return False
        
        return True
    
    def executeAllPlugins(self):
        for plugin in self.loadedPlugins.keys():
            self.executePlugin(plugin)