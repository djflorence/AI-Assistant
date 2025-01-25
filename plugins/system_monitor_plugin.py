import psutil
import time
from typing import Dict, Any, List
import os
from datetime import datetime

def plugin_info():
    return {
        'name': 'System Monitor',
        'description': 'Real-time system resource monitoring tools'
    }

def get_commands():
    return {
        'cpu_usage': {
            'function': cpu_usage,
            'description': 'Get real-time CPU usage information'
        },
        'memory_usage': {
            'function': memory_usage,
            'description': 'Get detailed memory usage stats'
        },
        'disk_space': {
            'function': disk_space,
            'description': 'Analyze disk space usage'
        },
        'process_monitor': {
            'function': process_monitor,
            'description': 'Monitor and manage system processes'
        }
    }

def cpu_usage(interval: float = 1.0) -> Dict[str, Any]:
    """Get detailed CPU usage information"""
    try:
        # Get CPU times at start
        cpu_times_start = psutil.cpu_times()
        
        # Wait for the specified interval
        time.sleep(interval)
        
        # Get CPU times at end
        cpu_times_end = psutil.cpu_times()
        
        # Calculate usage percentages
        total_start = sum([getattr(cpu_times_start, field) 
                          for field in cpu_times_start._fields])
        total_end = sum([getattr(cpu_times_end, field) 
                        for field in cpu_times_end._fields])
        
        total_diff = total_end - total_start
        
        usage = {}
        for field in cpu_times_end._fields:
            start = getattr(cpu_times_start, field)
            end = getattr(cpu_times_end, field)
            usage[field] = ((end - start) / total_diff) * 100 if total_diff > 0 else 0
        
        return {
            'success': True,
            'cpu_percent': psutil.cpu_percent(interval=None),
            'cpu_count': {
                'physical': psutil.cpu_count(logical=False),
                'logical': psutil.cpu_count(logical=True)
            },
            'cpu_freq': {
                'current': psutil.cpu_freq().current,
                'min': psutil.cpu_freq().min,
                'max': psutil.cpu_freq().max
            },
            'detailed_usage': usage,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def memory_usage() -> Dict[str, Any]:
    """Get detailed memory usage statistics"""
    try:
        virtual_memory = psutil.virtual_memory()
        swap_memory = psutil.swap_memory()
        
        return {
            'success': True,
            'virtual_memory': {
                'total': virtual_memory.total,
                'available': virtual_memory.available,
                'used': virtual_memory.used,
                'free': virtual_memory.free,
                'percent': virtual_memory.percent,
                'active': getattr(virtual_memory, 'active', None),
                'inactive': getattr(virtual_memory, 'inactive', None),
                'buffers': getattr(virtual_memory, 'buffers', None),
                'cached': getattr(virtual_memory, 'cached', None),
                'shared': getattr(virtual_memory, 'shared', None)
            },
            'swap_memory': {
                'total': swap_memory.total,
                'used': swap_memory.used,
                'free': swap_memory.free,
                'percent': swap_memory.percent,
                'sin': swap_memory.sin,
                'sout': swap_memory.sout
            },
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def disk_space(paths: List[str] = None) -> Dict[str, Any]:
    """Analyze disk space usage for specified paths or all mounted partitions"""
    try:
        if not paths:
            paths = [part.mountpoint for part in psutil.disk_partitions(all=False)]
            
        disk_info = {}
        for path in paths:
            try:
                usage = psutil.disk_usage(path)
                disk_info[path] = {
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent
                }
                
                # Get disk I/O statistics if available
                try:
                    io_counters = psutil.disk_io_counters(perdisk=True)
                    for disk, stats in io_counters.items():
                        if any(path.startswith(disk) for disk in paths):
                            disk_info[path]['io_stats'] = {
                                'read_count': stats.read_count,
                                'write_count': stats.write_count,
                                'read_bytes': stats.read_bytes,
                                'write_bytes': stats.write_bytes,
                                'read_time': stats.read_time,
                                'write_time': stats.write_time
                            }
                except Exception:
                    disk_info[path]['io_stats'] = None
                    
            except Exception as e:
                disk_info[path] = {'error': str(e)}
        
        return {
            'success': True,
            'disks': disk_info,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def process_monitor(sort_by: str = 'cpu_percent', top_n: int = 10) -> Dict[str, Any]:
    """Monitor system processes and get detailed information"""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 
                                       'memory_percent', 'status', 'create_time']):
            try:
                pinfo = proc.as_dict()
                pinfo['cpu_percent'] = proc.cpu_percent(interval=0.1)
                pinfo['memory_percent'] = proc.memory_percent()
                pinfo['create_time'] = datetime.fromtimestamp(pinfo['create_time']).isoformat()
                
                try:
                    pinfo['num_threads'] = proc.num_threads()
                    pinfo['num_fds'] = proc.num_fds()
                    pinfo['connections'] = len(proc.connections())
                    pinfo['open_files'] = len(proc.open_files())
                except Exception:
                    pass
                    
                processes.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Sort processes by the specified criterion
        processes.sort(key=lambda x: getattr(x, sort_by, 0), reverse=True)
        
        return {
            'success': True,
            'processes': processes[:top_n],
            'total_processes': len(processes),
            'sort_by': sort_by,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}
