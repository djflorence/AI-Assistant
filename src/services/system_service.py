import psutil
import platform
import os
import datetime
import speedtest
import wmi
import shutil
import socket
import subprocess
import git
from git import Repo
from typing import Dict, List, Optional, Union, Tuple
import sys
import json
from pathlib import Path

def get_system_health() -> Dict:
    """Get system health information"""
    try:
        # Initialize WMI
        c = wmi.WMI()
        
        # Get CPU info
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_temp = None
        try:
            cpu = c.Win32_Processor()[0]
            if hasattr(cpu, 'Temperature'):
                cpu_temp = float(cpu.Temperature)
        except:
            pass
            
        # Get memory info
        memory = psutil.virtual_memory()
        
        # Get disk info
        disks = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent
                })
            except:
                continue
                
        # Get battery info if available
        battery = None
        if hasattr(psutil, 'sensors_battery'):
            batt = psutil.sensors_battery()
            if batt:
                time_left = str(datetime.timedelta(seconds=batt.secsleft)) if batt.secsleft > 0 else "Unknown"
                battery = {
                    'percent': batt.percent,
                    'power_plugged': batt.power_plugged,
                    'time_left': time_left
                }
                
        return {
            'cpu': {
                'usage': cpu_percent,
                'temperature': cpu_temp
            },
            'memory': {
                'total': memory.total,
                'available': memory.available,
                'used': memory.used,
                'percent': memory.percent
            },
            'disks': disks,
            'battery': battery
        }
    except Exception as e:
        print(f"Error getting system health: {str(e)}")
        return None

def get_process_info() -> List[Dict]:
    """Get information about running processes"""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            try:
                pinfo = proc.info
                processes.append({
                    'pid': pinfo['pid'],
                    'name': pinfo['name'],
                    'cpu_percent': pinfo['cpu_percent'],
                    'memory_info': format_bytes(pinfo['memory_info'].rss)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)
    except Exception as e:
        print(f"Error getting process info: {str(e)}")
        return None

def get_network_info() -> Dict:
    """Get network information"""
    try:
        # Get network interfaces
        interfaces = []
        for name, addrs in psutil.net_if_addrs().items():
            addresses = []
            for addr in addrs:
                if addr.family == 2:  # IPv4
                    addresses.append({
                        'ip': addr.address,
                        'netmask': addr.netmask,
                        'broadcast': addr.broadcast
                    })
            if addresses:
                interfaces.append({
                    'name': name,
                    'addresses': addresses
                })
                
        # Get network connections
        connections = []
        for conn in psutil.net_connections():
            try:
                process = psutil.Process(conn.pid)
                connections.append({
                    'pid': conn.pid,
                    'name': process.name(),
                    'status': conn.status,
                    'type': 'TCP' if conn.type == 1 else 'UDP',
                    'port': conn.laddr.port if conn.laddr else None
                })
            except:
                continue
                
        return {
            'interfaces': interfaces,
            'connections': connections
        }
    except Exception as e:
        print(f"Error getting network info: {str(e)}")
        return None

def test_internet_speed() -> Optional[Dict]:
    """Test internet connection speed"""
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        
        # Get download speed
        download = st.download() / 1_000_000  # Convert to Mbps
        
        # Get upload speed
        upload = st.upload() / 1_000_000  # Convert to Mbps
        
        # Get ping
        ping = st.results.ping
        
        return {
            'download': f"{download:.1f} Mbps",
            'upload': f"{upload:.1f} Mbps",
            'ping': f"{ping:.0f} ms"
        }
    except Exception as e:
        print(f"Error testing internet speed: {str(e)}")
        return None

def get_system_devices() -> Dict:
    """Get information about connected devices"""
    try:
        c = wmi.WMI()
        
        # Get USB devices
        usb_devices = []
        for device in c.Win32_USBHub():
            usb_devices.append({
                'name': device.Description or device.DeviceID,
                'status': device.Status or 'Unknown'
            })
            
        # Get disk drives
        disk_drives = []
        for drive in c.Win32_DiskDrive():
            disk_drives.append({
                'name': drive.Caption,
                'size': drive.Size,
                'interface': drive.InterfaceType
            })
            
        # Get network adapters
        network_adapters = []
        for adapter in c.Win32_NetworkAdapter(PhysicalAdapter=True):
            network_adapters.append({
                'name': adapter.Name,
                'mac_address': adapter.MACAddress
            })
            
        # Get monitors
        monitors = []
        for monitor in c.Win32_DesktopMonitor():
            monitors.append({
                'name': monitor.Caption or monitor.DeviceID,
                'screen_width': monitor.ScreenWidth,
                'screen_height': monitor.ScreenHeight
            })
            
        return {
            'usb_devices': usb_devices,
            'disk_drives': disk_drives,
            'network_adapters': network_adapters,
            'monitors': monitors
        }
    except Exception as e:
        print(f"Error getting system devices: {str(e)}")
        return None

def clean_system() -> Optional[Dict]:
    """Clean temporary files from the system"""
    try:
        paths_to_clean = [
            os.path.join(os.environ['TEMP']),
            os.path.join(os.environ['WINDIR'], 'Temp'),
            os.path.join(os.environ['LOCALAPPDATA'], 'Temp')
        ]
        
        total_space_saved = 0
        cleaned_paths = []
        
        for path in paths_to_clean:
            if os.path.exists(path):
                space_before = get_dir_size(path)
                files_removed = clean_directory(path)
                space_after = get_dir_size(path)
                space_saved = space_before - space_after
                
                total_space_saved += space_saved
                cleaned_paths.append({
                    'path': path,
                    'files_removed': files_removed,
                    'space_saved': space_saved
                })
                
        return {
            'total_space_saved': total_space_saved,
            'cleaned_paths': cleaned_paths
        }
    except Exception as e:
        print(f"Error cleaning system: {str(e)}")
        return None

def get_dir_size(path: str) -> int:
    """Get the total size of a directory"""
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total += os.path.getsize(fp)
            except:
                continue
    return total

def clean_directory(path: str) -> int:
    """Clean a directory and return number of files removed"""
    files_removed = 0
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            try:
                os.remove(os.path.join(root, name))
                files_removed += 1
            except:
                continue
        for name in dirs:
            try:
                os.rmdir(os.path.join(root, name))
            except:
                continue
    return files_removed

def format_bytes(size: int) -> str:
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"

def analyze_code_directory(directory: str = '.') -> Dict:
    """Analyze a code directory for insights"""
    try:
        stats = {
            'files': {
                'total': 0,
                'by_type': {}
            },
            'code': {
                'total_lines': 0,
                'code_lines': 0,
                'comment_lines': 0,
                'blank_lines': 0
            },
            'functions': [],
            'classes': [],
            'issues': [],
            'todos': []
        }
        
        # Walk through directory
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                
                # Get file extension
                _, ext = os.path.splitext(file)
                ext = ext.lower()
                
                # Update file type count
                stats['files']['by_type'][ext] = stats['files']['by_type'].get(ext, 0) + 1
                stats['files']['total'] += 1
                
                # Analyze Python files
                if ext == '.py':
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        
                        current_class = None
                        current_function = None
                        
                        for i, line in enumerate(lines, 1):
                            line = line.strip()
                            
                            # Count line types
                            if not line:
                                stats['code']['blank_lines'] += 1
                            elif line.startswith('#'):
                                stats['code']['comment_lines'] += 1
                                # Check for TODOs
                                if 'todo' in line.lower():
                                    stats['todos'].append({
                                        'file': file_path,
                                        'line': i,
                                        'content': line[1:].strip()
                                    })
                            else:
                                stats['code']['code_lines'] += 1
                                
                                # Track functions and classes
                                if line.startswith('def '):
                                    func_name = line[4:line.find('(')]
                                    current_function = {
                                        'name': func_name,
                                        'file': file_path,
                                        'line': i,
                                        'complexity': 1  # Basic complexity score
                                    }
                                    if current_class:
                                        current_class['methods'].append(current_function)
                                    else:
                                        stats['functions'].append(current_function)
                                
                                elif line.startswith('class '):
                                    class_name = line[6:line.find('(') if '(' in line else line[6:line.find(':')]]
                                    current_class = {
                                        'name': class_name,
                                        'file': file_path,
                                        'line': i,
                                        'methods': []
                                    }
                                    stats['classes'].append(current_class)
                                
                                # Simple complexity scoring
                                if current_function and any(x in line for x in ['if', 'for', 'while', 'except']):
                                    current_function['complexity'] += 1
                        
                        stats['code']['total_lines'] += len(lines)
                        
                    except Exception as e:
                        stats['issues'].append(f"Error analyzing {file_path}: {str(e)}")
                        continue
        
        return stats
    except Exception as e:
        print(f"Error analyzing code directory: {str(e)}")
        return None

def check_git_status(directory: str = '.') -> Dict:
    """Check git repository status"""
    try:
        import git
        
        # Initialize repo
        repo = git.Repo(directory)
        
        # Get current branch
        branch = repo.active_branch.name
        
        # Get status
        status = repo.git.status()
        
        # Get recent commits
        commits = []
        for commit in repo.iter_commits(max_count=5):
            commits.append({
                'hash': commit.hexsha[:7],
                'message': commit.message.strip(),
                'author': commit.author.name,
                'date': datetime.datetime.fromtimestamp(commit.committed_date).strftime('%Y-%m-%d %H:%M:%S')
            })
        
        # Get modified files
        modified = [item.a_path for item in repo.index.diff(None)]
        
        # Get untracked files
        untracked = repo.untracked_files
        
        return {
            'branch': branch,
            'status': status,
            'recent_commits': commits,
            'modified_files': modified,
            'untracked_files': untracked
        }
        
    except Exception as e:
        print(f"Error checking git status: {str(e)}")
        return None

def get_environment_info() -> Dict:
    """Get development environment information"""
    try:
        # Get Python info
        python_info = {
            'version': platform.python_version(),
            'implementation': platform.python_implementation(),
            'compiler': platform.python_compiler(),
            'path': sys.executable
        }
        
        # Get system info
        system_info = {
            'os': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor()
        }
        
        # Get environment variables
        env_vars = {k: v for k, v in os.environ.items() if not k.startswith('_')}
        
        return {
            'python': python_info,
            'system': system_info,
            'environment_variables': env_vars
        }
        
    except Exception as e:
        print(f"Error getting environment info: {str(e)}")
        return None

def find_development_servers() -> List[Dict]:
    """Find running development servers"""
    try:
        servers = []
        
        # Get all network connections
        for conn in psutil.net_connections():
            try:
                process = psutil.Process(conn.pid)
                name = process.name().lower()
                cmdline = ' '.join(process.cmdline()).lower()
                
                # Check for common development servers
                server_types = {
                    'flask': ['flask', 'werkzeug'],
                    'django': ['django', 'runserver'],
                    'node': ['node', 'npm', 'nodemon'],
                    'react': ['react-scripts', 'webpack'],
                    'vue': ['vue-cli-service'],
                    'angular': ['ng serve'],
                    'php': ['php -s', 'php artisan serve'],
                    'python': ['python -m http.server', 'python3 -m http.server']
                }
                
                for server_type, keywords in server_types.items():
                    if any(k in name or k in cmdline for k in keywords):
                        servers.append({
                            'type': server_type,
                            'pid': conn.pid,
                            'port': conn.laddr.port if conn.laddr else None,
                            'status': conn.status,
                            'process_name': name,
                            'command': cmdline
                        })
                        break
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        return servers
        
    except Exception as e:
        print(f"Error finding development servers: {str(e)}")
        return None

def launch_application(app_name: str, debug_log: Optional[List] = None, auto_accept: bool = True) -> str:
    """Launch a system application using installed_apps.json"""
    try:
        # Load installed apps from JSON
        apps_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'installed_apps.json')
        if not os.path.exists(apps_file):
            return "Error: installed_apps.json not found"
            
        with open(apps_file, 'r') as f:
            installed_apps = json.load(f)
        
        # Try to find the app by name or alias
        app_key = None
        
        # First try exact match
        app_key = next((k for k in installed_apps.keys() if k.lower() == app_name.lower()), None)
        
        # Then try aliases
        if not app_key:
            app_key = next((k for k in installed_apps.keys() 
                          if 'aliases' in installed_apps[k] 
                          and any(alias.lower() == app_name.lower() for alias in installed_apps[k]['aliases'])), None)
        
        # Finally try partial matches in both names and aliases
        if not app_key:
            app_key = next((k for k in installed_apps.keys() 
                          if app_name.lower() in k.lower() or
                          ('aliases' in installed_apps[k] and
                           any(app_name.lower() in alias.lower() for alias in installed_apps[k]['aliases']))), None)
            
        if not app_key:
            return f"Application '{app_name}' not found in installed apps"
            
        app_info = installed_apps[app_key]
        if not app_info.get('paths'):
            return f"No valid paths found for {app_name}"
            
        # First try to find the main executable (not launcher)
        app_path = next((p for p in app_info['paths'] 
                        if os.path.exists(p) 
                        and p.lower().endswith('.exe') 
                        and not p.lower().endswith('-launcher.exe')
                        and not 'launcher' in p.lower()), None)
        
        # If no main executable found, try any executable
        if not app_path:
            app_path = next((p for p in app_info['paths'] 
                           if os.path.exists(p) 
                           and p.lower().endswith(('.exe', '.bat'))), None)
        
        # If still no executable found, try any valid path
        if not app_path:
            app_path = next((p for p in app_info['paths'] if os.path.exists(p)), None)
            
        if not app_path:
            return f"No valid installation path found for {app_name}"
            
        # If auto_accept is False, return a message asking for confirmation
        if not auto_accept:
            return f"Would you like to launch {app_key}? Type /accept to confirm or /reject to cancel."
            
        # Launch the application
        try:
            if os.path.isfile(app_path):
                os.startfile(app_path)
            else:
                # If it's a directory, look for main executable
                exe_name = f"{os.path.basename(app_path)}.exe"
                exe_path = os.path.join(app_path, exe_name)
                if os.path.exists(exe_path):
                    os.startfile(exe_path)
                else:
                    # Just open the directory if no executable found
                    os.startfile(app_path)
            return f"Launched {app_key} successfully"
        except Exception as e:
            error_msg = f"Error launching {app_key}: {str(e)}"
            if debug_log is not None:
                debug_log.append(error_msg)
            return error_msg
            
    except Exception as e:
        error_msg = f"Error launching {app_name}: {str(e)}"
        if debug_log is not None:
            debug_log.append(error_msg)
        return error_msg

def scan_installed_apps() -> Dict[str, Dict]:
    """Scan system for installed applications and return a dictionary of app info"""
    installed_apps = {}
    
    # Common program directories
    program_dirs = [
        os.environ.get('ProgramFiles', 'C:\\Program Files'),
        os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'),
        os.path.join(os.environ.get('LocalAppData', ''), 'Programs'),
        os.path.join(os.environ.get('LocalAppData', ''), 'Google\\Chrome'),  # Chrome specific
        os.path.join(os.environ.get('ProgramFiles', ''), 'Google\\Chrome'),  # Chrome specific
        os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'Google\\Chrome'),  # Chrome specific
        os.environ.get('SystemRoot', 'C:\\Windows'),  # System applications
        os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32'),  # More system applications
    ]
    
    # Known applications with their common names and executable patterns
    known_apps = {
        'Google Chrome': {
            'patterns': ['chrome.exe'],
            'directories': ['Google\\Chrome', 'Chrome'],
            'aliases': ['chrome', 'google chrome']
        },
        'Mozilla Firefox': {
            'patterns': ['firefox.exe'],
            'directories': ['Mozilla Firefox'],
            'aliases': ['firefox']
        },
        'Blender': {
            'patterns': ['blender.exe'],
            'directories': ['Blender Foundation'],
            'aliases': ['blender']
        },
        'Notepad': {
            'patterns': ['notepad.exe'],
            'directories': ['System32', 'Windows'],
            'aliases': ['notepad']
        },
        'Paint': {
            'patterns': ['mspaint.exe'],
            'directories': ['System32', 'Windows'],
            'aliases': ['paint', 'mspaint']
        },
        'Calculator': {
            'patterns': ['calc.exe'],
            'directories': ['System32', 'Windows'],
            'aliases': ['calc', 'calculator']
        },
        'Command Prompt': {
            'patterns': ['cmd.exe'],
            'directories': ['System32', 'Windows'],
            'aliases': ['cmd', 'command prompt', 'terminal']
        },
        'File Explorer': {
            'patterns': ['explorer.exe'],
            'directories': ['System32', 'Windows'],
            'aliases': ['explorer', 'file explorer', 'windows explorer']
        },
        'Task Manager': {
            'patterns': ['taskmgr.exe'],
            'directories': ['System32', 'Windows'],
            'aliases': ['taskmgr', 'task manager']
        },
        'Control Panel': {
            'patterns': ['control.exe'],
            'directories': ['System32', 'Windows'],
            'aliases': ['control', 'control panel']
        },
        'PowerShell': {
            'patterns': ['powershell.exe'],
            'directories': ['System32\\WindowsPowerShell\\v1.0', 'System32'],
            'aliases': ['powershell', 'power shell']
        },
        'Microsoft Edge': {
            'patterns': ['msedge.exe'],
            'directories': ['Microsoft\\Edge\\Application', 'Program Files\\Microsoft\\Edge\\Application'],
            'aliases': ['edge', 'msedge']
        },
        'Visual Studio Code': {
            'patterns': ['Code.exe'],
            'directories': ['Microsoft VS Code', 'VS Code'],
            'aliases': ['code', 'vscode', 'vs code']
        }
    }
    
    def add_app(name: str, path: str, source: str):
        """Add an application to the dictionary"""
        if name not in installed_apps:
            installed_apps[name] = {'paths': [], 'sources': [], 'aliases': []}
        if path not in installed_apps[name]['paths']:
            installed_apps[name]['paths'].append(path)
        if source not in installed_apps[name]['sources']:
            installed_apps[name]['sources'].append(source)
    
    # First scan for known applications
    for app_name, app_info in known_apps.items():
        for program_dir in program_dirs:
            if not os.path.exists(program_dir):
                continue
                
            # Look in specified directories first
            for known_dir in app_info['directories']:
                full_dir = os.path.join(program_dir, known_dir)
                if os.path.exists(full_dir):
                    for pattern in app_info['patterns']:
                        for root, _, files in os.walk(full_dir):
                            for file in files:
                                if file.lower() == pattern.lower():
                                    full_path = os.path.join(root, file)
                                    add_app(app_name, full_path, 'known_app')
                                    # Add aliases
                                    if 'aliases' not in installed_apps[app_name]:
                                        installed_apps[app_name]['aliases'] = []
                                    installed_apps[app_name]['aliases'].extend(app_info['aliases'])
                
            # Also look directly in program_dir for the patterns
            for pattern in app_info['patterns']:
                direct_path = os.path.join(program_dir, pattern)
                if os.path.exists(direct_path):
                    add_app(app_name, direct_path, 'known_app')
                    if 'aliases' not in installed_apps[app_name]:
                        installed_apps[app_name]['aliases'] = []
                    installed_apps[app_name]['aliases'].extend(app_info['aliases'])
    
    # Then scan for other applications
    for program_dir in program_dirs:
        if not os.path.exists(program_dir):
            continue
            
        for root, dirs, files in os.walk(program_dir):
            # Skip certain directories
            if any(skip in root.lower() for skip in ['windows\\winsxs', 'windows\\installer', 'temp', 'tmp']):
                continue
                
            for file in files:
                if file.lower().endswith('.exe'):
                    # Skip known utility executables
                    if file.lower() in ['unins000.exe', 'installer.exe', 'setup.exe', 'update.exe']:
                        continue
                        
                    # Get the application name from the directory structure
                    rel_path = os.path.relpath(root, program_dir)
                    parts = rel_path.split(os.sep)
                    if parts and parts[0]:
                        app_name = parts[0]
                        # Skip if we already found this app in known_apps
                        if app_name not in installed_apps:
                            full_path = os.path.join(root, file)
                            add_app(app_name, full_path, 'program_files')
    
    # Save to JSON file
    apps_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'installed_apps.json')
    with open(apps_file, 'w') as f:
        json.dump(installed_apps, f, indent=2)
    
    return installed_apps
