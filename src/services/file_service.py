import os
import fnmatch
import mimetypes
import shutil
import zipfile
import tarfile
import json
import subprocess
import speedtest
from datetime import datetime
from typing import List, Dict, Optional, Union
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import git
from git.exc import InvalidGitRepositoryError
from pathlib import Path
import threading
import logging

class DirectoryMonitor:
    """Monitor a directory for file changes"""
    def __init__(self, directory):
        self.directory = directory
        self.observers = []
        self.running = False
        self.thread = None
    
    def add_observer(self, callback):
        """Add an observer to be notified of changes"""
        self.observers.append(callback)
    
    def start(self):
        """Start monitoring the directory"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor)
            self.thread.daemon = True
            self.thread.start()
    
    def stop(self):
        """Stop monitoring the directory"""
        self.running = False
        if self.thread:
            self.thread.join()
    
    def _monitor(self):
        """Monitor directory for changes"""
        import time
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        
        class Handler(FileSystemEventHandler):
            def __init__(self, callback):
                self.callback = callback
            
            def on_created(self, event):
                if not event.is_directory:
                    self.callback('created', event.src_path)
            
            def on_modified(self, event):
                if not event.is_directory:
                    self.callback('modified', event.src_path)
            
            def on_deleted(self, event):
                if not event.is_directory:
                    self.callback('deleted', event.src_path)
        
        observer = Observer()
        observer.schedule(
            Handler(self._notify_observers),
            self.directory,
            recursive=False
        )
        observer.start()
        
        try:
            while self.running:
                time.sleep(1)
        finally:
            observer.stop()
            observer.join()
    
    def _notify_observers(self, event_type, file_path):
        """Notify all observers of a change"""
        for observer in self.observers:
            try:
                observer(event_type, file_path)
            except Exception as e:
                logging.error(f"Error notifying observer: {e}")


class DirectoryMonitor2(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback
        self.observer = Observer()
    
    def on_created(self, event):
        if not event.is_directory:
            self.callback('created', event.src_path)
    
    def on_modified(self, event):
        if not event.is_directory:
            self.callback('modified', event.src_path)
    
    def on_deleted(self, event):
        if not event.is_directory:
            self.callback('deleted', event.src_path)
    
    def start_monitoring(self, path):
        """Start monitoring a directory"""
        if not os.path.exists(path):
            os.makedirs(path)
        self.observer.schedule(self, path, recursive=False)
        self.observer.start()
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.observer.stop()
        self.observer.join()


class FileService:
    """Service for file operations"""
    def __init__(self):
        self.monitors = {}
    
    def start_monitoring(self, directory, callback):
        """Start monitoring a directory for changes"""
        try:
            # Create monitor if it doesn't exist
            if directory not in self.monitors:
                monitor = DirectoryMonitor2(callback)
                self.monitors[directory] = monitor
            
            # Ensure directory exists
            if not os.path.exists(directory):
                os.makedirs(directory)
            
            # Start monitoring
            self.monitors[directory].start_monitoring(directory)
            
        except Exception as e:
            logging.error(f"Error setting up directory monitoring: {e}")
    
    def stop_monitoring(self, directory):
        """Stop monitoring a directory"""
        if directory in self.monitors:
            self.monitors[directory].stop_monitoring()
            del self.monitors[directory]
    
    def stop_all_monitoring(self):
        """Stop all directory monitoring"""
        for directory in list(self.monitors.keys()):
            self.stop_monitoring(directory)

    @staticmethod
    def search_files(directory: str, pattern: str = "*", recursive: bool = True,
                    size_limit: Optional[int] = None, 
                    date_after: Optional[datetime] = None,
                    date_before: Optional[datetime] = None) -> List[Dict]:
        """Search for files with advanced filtering"""
        try:
            results = []
            for root, _, files in os.walk(directory):
                if not recursive and root != directory:
                    continue
                    
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    if not fnmatch.fnmatch(file, pattern):
                        continue
                        
                    stats = os.stat(file_path)
                    file_info = {
                        'name': file,
                        'path': file_path,
                        'size': stats.st_size,
                        'created': datetime.fromtimestamp(stats.st_ctime),
                        'modified': datetime.fromtimestamp(stats.st_mtime),
                        'accessed': datetime.fromtimestamp(stats.st_atime)
                    }
                    
                    if size_limit and stats.st_size > size_limit:
                        continue
                    if date_after and file_info['modified'] < date_after:
                        continue
                    if date_before and file_info['modified'] > date_before:
                        continue
                        
                    results.append(file_info)
                    
            return results
        except Exception as e:
            print(f"Error searching files: {e}")
            return []

    @staticmethod
    def analyze_file(file_path: str, preview_lines: int = 5) -> Dict:
        """Analyze file content and provide insights"""
        try:
            file_info = {
                'path': file_path,
                'size': os.path.getsize(file_path),
                'type': mimetypes.guess_type(file_path)[0],
                'preview': [],
                'encoding': None,
                'line_count': 0,
                'word_count': 0,
                'binary': False
            }
            
            try:
                with open(file_path, 'rb') as f:
                    is_binary = b'\0' in f.read(1024)
                    file_info['binary'] = is_binary
            except:
                pass
                
            if not file_info['binary']:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        file_info['line_count'] = len(lines)
                        file_info['preview'] = lines[:preview_lines]
                        text = ' '.join(lines)
                        file_info['word_count'] = len(text.split())
                except:
                    file_info['error'] = "Could not read file content"
            
            return file_info
        except Exception as e:
            print(f"Error analyzing file: {e}")
            return {}

    @staticmethod
    def backup_files(source_dir: str, backup_dir: str, 
                    include_patterns: Optional[List[str]] = None,
                    exclude_patterns: Optional[List[str]] = None) -> Dict:
        """Create a backup of files"""
        try:
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
                
            backup_time = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(backup_dir, f'backup_{backup_time}')
            os.makedirs(backup_path)
            
            copied_files = []
            total_size = 0
            
            for root, _, files in os.walk(source_dir):
                for file in files:
                    if include_patterns and not any(fnmatch.fnmatch(file, p) for p in include_patterns):
                        continue
                    if exclude_patterns and any(fnmatch.fnmatch(file, p) for p in exclude_patterns):
                        continue
                        
                    src_path = os.path.join(root, file)
                    rel_path = os.path.relpath(src_path, source_dir)
                    dst_path = os.path.join(backup_path, rel_path)
                    
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    shutil.copy2(src_path, dst_path)
                    file_size = os.path.getsize(src_path)
                    
                    copied_files.append({
                        'source': src_path,
                        'destination': dst_path,
                        'size': file_size
                    })
                    total_size += file_size
            
            return {
                'backup_path': backup_path,
                'files': copied_files,
                'total_size': total_size,
                'timestamp': backup_time
            }
        except Exception as e:
            print(f"Error creating backup: {e}")
            return {}

    @staticmethod
    def compress_files(file_paths: List[str], output_path: str, format: str = 'zip') -> Dict:
        """Compress files into an archive"""
        try:
            if format == 'zip':
                with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for file_path in file_paths:
                        zf.write(file_path, os.path.basename(file_path))
            elif format == 'tar':
                with tarfile.open(output_path, 'w:gz') as tf:
                    for file_path in file_paths:
                        tf.add(file_path, arcname=os.path.basename(file_path))
            
            return {
                'archive_path': output_path,
                'format': format,
                'size': os.path.getsize(output_path),
                'files': [os.path.basename(f) for f in file_paths]
            }
        except Exception as e:
            print(f"Error compressing files: {e}")
            return {}

    @staticmethod
    def analyze_directory(path: str = None) -> Optional[Dict]:
        """Analyze a directory and return information about its contents"""
        try:
            if path is None:
                path = os.getcwd()
                
            total_files = 0
            total_size = 0
            extensions = {}
            
            for root, dirs, files in os.walk(path):
                for file in files:
                    total_files += 1
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                        ext = os.path.splitext(file)[1].lower() or 'no extension'
                        extensions[ext] = extensions.get(ext, 0) + 1
                    except:
                        continue
                        
            return {
                'total_files': total_files,
                'total_size': FileService.format_size(total_size),
                'extensions': dict(sorted(extensions.items(), key=lambda x: x[1], reverse=True))
            }
        except Exception as e:
            print(f"Error analyzing directory: {str(e)}")
            return None

    @staticmethod
    def analyze_code_file(file_path: str) -> Optional[Dict]:
        """Analyze a single code file"""
        try:
            if not os.path.isfile(file_path):
                return None
                
            ext = os.path.splitext(file_path)[1].lower()
            code_extensions = {'.py', '.js', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go'}
            
            if ext not in code_extensions:
                return None
                
            todos = []
            functions = []
            classes = []
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.readlines()
                    
                    # Look for TODOs
                    for i, line in enumerate(content, 1):
                        if 'TODO' in line:
                            todos.append({
                                'file': os.path.basename(file_path),
                                'line': i,
                                'content': line.strip()
                            })
                            
                    # Basic function and class detection
                    for i, line in enumerate(content):
                        if line.strip().startswith('def '):
                            functions.append({
                                'name': line.split('def ')[1].split('(')[0],
                                'file': os.path.basename(file_path),
                                'line': i + 1,
                                'complexity': FileService.count_complexity(content[i:])
                            })
                        elif line.strip().startswith('class '):
                            class_info = FileService.analyze_class(content[i:])
                            class_info['file'] = os.path.basename(file_path)
                            class_info['line'] = i + 1
                            classes.append(class_info)
                            
                    # Count different types of lines
                    code_lines = 0
                    comment_lines = 0
                    blank_lines = 0
                    
                    for line in content:
                        line = line.strip()
                        if not line:
                            blank_lines += 1
                        elif line.startswith('#'):
                            comment_lines += 1
                        else:
                            code_lines += 1
                    
                    return {
                        'filename': os.path.basename(file_path),
                        'extension': ext,
                        'size': os.path.getsize(file_path),
                        'lines': {
                            'total': len(content),
                            'code': code_lines,
                            'comments': comment_lines,
                            'blank': blank_lines
                        },
                        'todos': todos,
                        'functions': functions,
                        'classes': classes
                    }
            except:
                return None
                
        except Exception as e:
            print(f"Error analyzing file: {str(e)}")
            return None

    @staticmethod
    def analyze_code_directory(path: str = None) -> Optional[Dict]:
        """Analyze code in a directory"""
        try:
            if path is None:
                path = os.getcwd()
            
            if not os.path.isdir(path):
                return None
                
            code_files = []
            todos = []
            functions = []
            classes = []
            total_lines = 0
            code_lines = 0
            comment_lines = 0
            blank_lines = 0
            file_types = {}
            
            code_extensions = {'.py', '.js', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go'}
            
            for root, dirs, files in os.walk(path):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in code_extensions:
                        file_path = os.path.join(root, file)
                        file_analysis = FileService.analyze_code_file(file_path)
                        
                        if file_analysis:
                            code_files.append(file_analysis)
                            file_types[ext] = file_types.get(ext, 0) + 1
                            
                            # Aggregate statistics
                            total_lines += file_analysis['lines']['total']
                            code_lines += file_analysis['lines']['code']
                            comment_lines += file_analysis['lines']['comments']
                            blank_lines += file_analysis['lines']['blank']
                            
                            todos.extend(file_analysis['todos'])
                            functions.extend(file_analysis['functions'])
                            classes.extend(file_analysis['classes'])
                        
            return {
                'directory': path,
                'files': {
                    'total': len(code_files),
                    'by_type': file_types,
                    'analyzed': code_files
                },
                'lines': {
                    'total': total_lines,
                    'code': code_lines,
                    'comments': comment_lines,
                    'blank': blank_lines
                },
                'todos': todos,
                'functions': functions,
                'classes': classes
            }
                
        except Exception as e:
            print(f"Error analyzing directory: {str(e)}")
            return None

    @staticmethod
    def count_complexity(lines: List[str]) -> int:
        """Simple cyclomatic complexity counter"""
        complexity = 1
        for line in lines:
            if any(keyword in line for keyword in ['if ', 'for ', 'while ', 'and', 'or']):
                complexity += 1
        return complexity

    @staticmethod
    def analyze_class(lines: List[str]) -> Dict:
        """Analyze a class definition"""
        class_name = lines[0].split('class ')[1].split('(')[0].strip()
        methods = []
        
        for i, line in enumerate(lines):
            if line.strip().startswith('def '):
                method_name = line.split('def ')[1].split('(')[0]
                methods.append({
                    'name': method_name,
                    'line': i + 1,
                    'complexity': FileService.count_complexity(lines[i:])
                })
                
        return {
            'name': class_name,
            'methods': methods
        }

    @staticmethod
    def check_git_status(path: str = None) -> Optional[Dict]:
        """Check Git repository status"""
        try:
            if path is None:
                path = os.getcwd()
                
            repo = git.Repo(path)
            
            # Get current branch
            branch = repo.active_branch.name
            
            # Check if repo is dirty
            is_dirty = repo.is_dirty()
            
            # Get modified, staged, and untracked files
            modified_files = [item.a_path for item in repo.index.diff(None)]
            staged_files = [item.a_path for item in repo.index.diff('HEAD')]
            untracked_files = repo.untracked_files
            
            # Get remote status
            commits_ahead = commits_behind = 0
            if repo.remotes:
                try:
                    remote = repo.remote()
                    remote.fetch()
                    commits_ahead = len(list(repo.iter_commits('origin/' + branch + '..' + branch)))
                    commits_behind = len(list(repo.iter_commits(branch + '..origin/' + branch)))
                except:
                    pass
                    
            # Get last commit info
            last_commit = None
            if repo.head.is_valid():
                commit = repo.head.commit
                last_commit = {
                    'hash': commit.hexsha,
                    'message': commit.message.strip(),
                    'author': f"{commit.author.name} <{commit.author.email}>",
                    'date': commit.authored_datetime.isoformat()
                }
                
            return {
                'branch': branch,
                'is_dirty': is_dirty,
                'modified_files': modified_files,
                'staged_files': staged_files,
                'untracked_files': untracked_files,
                'commits_ahead': commits_ahead,
                'commits_behind': commits_behind,
                'last_commit': last_commit
            }
        except InvalidGitRepositoryError:
            return None
        except Exception as e:
            print(f"Error checking git status: {str(e)}")
            return None

    @staticmethod
    def find_development_servers() -> Optional[List[Dict]]:
        """Find running development servers"""
        try:
            import psutil
            
            dev_servers = []
            server_processes = {
                'node': ['node', 'nodemon', 'npm', 'yarn'],
                'python': ['python', 'flask', 'django', 'uvicorn', 'gunicorn'],
                'ruby': ['rails', 'puma', 'unicorn'],
                'php': ['php', 'artisan', 'symfony'],
                'java': ['spring', 'tomcat', 'jetty']
            }
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'connections']):
                try:
                    pinfo = proc.info
                    if any(server in str(pinfo['name']).lower() for servers in server_processes.values() for server in servers):
                        connections = pinfo['connections']
                        listening_ports = [conn.laddr.port for conn in connections if conn.status == 'LISTEN']
                        
                        if listening_ports:
                            dev_servers.append({
                                'process_name': pinfo['name'],
                                'pid': pinfo['pid'],
                                'local_address': f"localhost:{listening_ports[0]}",
                                'status': 'Running'
                            })
                except:
                    continue
                    
            return dev_servers
        except Exception as e:
            print(f"Error finding development servers: {str(e)}")
            return None

    @staticmethod
    def test_internet_speed() -> Optional[Dict]:
        """Test internet connection speed"""
        try:
            print("Starting speed test...")
            st = speedtest.Speedtest()
            
            print("Getting best server...")
            st.get_best_server()
            
            print("Testing download speed...")
            download_speed = st.download() / 1_000_000  # Convert to Mbps
            
            print("Testing upload speed...")
            upload_speed = st.upload() / 1_000_000  # Convert to Mbps
            
            print("Testing ping...")
            ping = st.results.ping
            
            return {
                'download': download_speed,
                'upload': upload_speed,
                'ping': ping,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            print(f"Error testing internet speed: {str(e)}")
            return None

    @staticmethod
    def format_size(size: int) -> str:
        """Format size in bytes to human readable string"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    @staticmethod
    def scan_installed_applications() -> Dict:
        """
        Scan the system for installed applications and save them to a JSON file
        Returns a dictionary of discovered applications
        """
        try:
            import winreg
            import json
            from pathlib import Path

            apps_dict = {}

            def add_to_dict(name, path, source):
                """Helper function to add apps to dictionary"""
                if name and path:
                    name = name.strip()
                    path = path.strip()
                    
                    # Clean up the name - remove version numbers and common suffixes
                    clean_name = name.split('-')[0].split('(')[0].strip()
                    
                    # For executables, use the filename without extension as name
                    if path.lower().endswith('.exe'):
                        exe_name = os.path.splitext(os.path.basename(path))[0].lower()
                        if not apps_dict.get(exe_name):
                            apps_dict[exe_name] = {
                                'paths': set(),
                                'sources': set()
                            }
                        apps_dict[exe_name]['paths'].add(path)
                        apps_dict[exe_name]['sources'].add(source)
                    
                    # Also add the clean name entry
                    if clean_name and clean_name not in apps_dict:
                        apps_dict[clean_name] = {
                            'paths': set(),
                            'sources': set()
                        }
                    if clean_name:
                        apps_dict[clean_name]['paths'].add(path)
                        apps_dict[clean_name]['sources'].add(source)

            # Scan Registry Uninstall keys
            reg_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
            ]

            for reg_hkey, reg_path in reg_paths:
                try:
                    reg_key = winreg.OpenKey(reg_hkey, reg_path)
                    for i in range(winreg.QueryInfoKey(reg_key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(reg_key, i)
                            subkey = winreg.OpenKey(reg_key, subkey_name)
                            try:
                                name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                # Try multiple registry values for the path
                                path = None
                                for value_name in ["InstallLocation", "DisplayIcon", "UninstallString"]:
                                    try:
                                        path = winreg.QueryValueEx(subkey, value_name)[0]
                                        if path:
                                            # Clean up path if it contains arguments
                                            path = path.split('"')[1] if '"' in path else path.split(',')[0]
                                            break
                                    except:
                                        continue
                                if path:
                                    add_to_dict(name, path, "registry")
                            except:
                                pass
                            winreg.CloseKey(subkey)
                        except:
                            continue
                    winreg.CloseKey(reg_key)
                except:
                    continue

            # Scan Start Menu
            start_menu_paths = [
                os.path.join(os.environ["ProgramData"], "Microsoft", "Windows", "Start Menu", "Programs"),
                os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs")
            ]

            for start_menu in start_menu_paths:
                if os.path.exists(start_menu):
                    for root, dirs, files in os.walk(start_menu):
                        for file in files:
                            if file.endswith('.lnk'):
                                try:
                                    import win32com.client
                                    shell = win32com.client.Dispatch("WScript.Shell")
                                    shortcut = shell.CreateShortCut(os.path.join(root, file))
                                    name = os.path.splitext(file)[0]
                                    target_path = shortcut.Targetpath
                                    if target_path and os.path.exists(target_path):
                                        add_to_dict(name, target_path, "start_menu")
                                except:
                                    continue

            # Scan Program Files directories
            program_dirs = [
                os.environ.get("ProgramFiles", "C:\\Program Files"),
                os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
                os.environ.get("LocalAppData", ""),
                os.environ.get("AppData", "")
            ]

            # Additional common paths for specific applications
            program_dirs.extend([
                "C:\\Program Files\\Blender Foundation",
                os.path.expandvars("%ProgramFiles%\\Blender Foundation")
            ])

            for program_dir in program_dirs:
                if os.path.exists(program_dir):
                    for root, dirs, files in os.walk(program_dir):
                        for file in files:
                            if file.endswith('.exe'):
                                try:
                                    full_path = os.path.join(root, file)
                                    name = os.path.splitext(file)[0]
                                    # Special handling for common applications
                                    if "blender" in root.lower() and "blender.exe" in file.lower():
                                        add_to_dict("blender", full_path, "program_files")
                                    add_to_dict(name, full_path, "program_files")
                                except:
                                    continue

            # Convert sets to lists for JSON serialization
            apps_json = {}
            for app_name, app_data in apps_dict.items():
                apps_json[app_name] = {
                    'paths': list(app_data['paths']),
                    'sources': list(app_data['sources'])
                }

            # Save to file
            apps_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'installed_apps.json')
            with open(apps_file, 'w', encoding='utf-8') as f:
                json.dump(apps_json, f, indent=2)

            return apps_json

        except Exception as e:
            print(f"Error scanning installed applications: {str(e)}")
            return {}

    @staticmethod
    def launch_application(app_name: str, auto_accept: bool = True) -> str:
        """Launch a system application with optional auto-accept"""
        from src.services.system_service import launch_application
        return launch_application(app_name, auto_accept=auto_accept)
