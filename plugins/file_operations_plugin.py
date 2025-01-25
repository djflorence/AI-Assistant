import os
import shutil
import zipfile
from typing import List, Dict, Any
import hashlib
from pathlib import Path
import filecmp
from datetime import datetime

def plugin_info():
    return {
        'name': 'File Operations',
        'description': 'Advanced file management and organization tools'
    }

def get_commands():
    return {
        'compress_files': {
            'function': compress_files,
            'description': 'Compresses files/folders into zip archive'
        },
        'batch_rename': {
            'function': batch_rename,
            'description': 'Renames multiple files using patterns'
        },
        'duplicate_finder': {
            'function': duplicate_finder,
            'description': 'Finds duplicate files in directories'
        },
        'file_sync': {
            'function': file_sync,
            'description': 'Synchronizes contents of two directories'
        }
    }

def compress_files(files: List[str], output_path: str) -> Dict[str, Any]:
    """Compresses given files into a zip archive"""
    try:
        # Create timestamp for unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if not output_path.endswith('.zip'):
            output_path = f"{output_path}_{timestamp}.zip"
            
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in files:
                if os.path.isfile(file):
                    zipf.write(file, os.path.basename(file))
                elif os.path.isdir(file):
                    for root, _, filenames in os.walk(file):
                        for filename in filenames:
                            file_path = os.path.join(root, filename)
                            arcname = os.path.relpath(file_path, os.path.dirname(file))
                            zipf.write(file_path, arcname)
        
        return {
            'success': True,
            'archive_path': output_path,
            'size': os.path.getsize(output_path)
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def batch_rename(directory: str, pattern: str, replacement: str, 
                file_types: List[str] = None) -> Dict[str, Any]:
    """Renames multiple files using pattern matching"""
    try:
        renamed_files = []
        errors = []
        
        for filename in os.listdir(directory):
            if file_types and not any(filename.endswith(ft) for ft in file_types):
                continue
                
            old_path = os.path.join(directory, filename)
            if os.path.isfile(old_path):
                try:
                    new_name = filename.replace(pattern, replacement)
                    new_path = os.path.join(directory, new_name)
                    
                    if old_path != new_path:
                        os.rename(old_path, new_path)
                        renamed_files.append({
                            'old_name': filename,
                            'new_name': new_name
                        })
                except Exception as e:
                    errors.append({
                        'file': filename,
                        'error': str(e)
                    })
        
        return {
            'success': True,
            'renamed_files': renamed_files,
            'errors': errors
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def duplicate_finder(directories: List[str]) -> Dict[str, Any]:
    """Finds duplicate files across directories"""
    try:
        hash_dict = {}
        duplicates = {}
        
        def get_file_hash(filepath: str, block_size: int = 65536) -> str:
            hasher = hashlib.sha256()
            with open(filepath, 'rb') as file:
                while True:
                    data = file.read(block_size)
                    if not data:
                        break
                    hasher.update(data)
            return hasher.hexdigest()
        
        for directory in directories:
            for root, _, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(root, filename)
                    file_hash = get_file_hash(filepath)
                    
                    if file_hash in hash_dict:
                        if file_hash not in duplicates:
                            duplicates[file_hash] = [hash_dict[file_hash]]
                        duplicates[file_hash].append(filepath)
                    else:
                        hash_dict[file_hash] = filepath
        
        return {
            'success': True,
            'duplicates': duplicates,
            'total_groups': len(duplicates),
            'total_duplicates': sum(len(files) - 1 for files in duplicates.values())
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def file_sync(source_dir: str, target_dir: str, delete: bool = False) -> Dict[str, Any]:
    """Synchronizes two directories"""
    try:
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        comparison = filecmp.dircmp(source_dir, target_dir)
        changes = {
            'copied': [],
            'updated': [],
            'deleted': [],
            'errors': []
        }
        
        # Copy new files
        for item in comparison.left_only:
            src_path = os.path.join(source_dir, item)
            dst_path = os.path.join(target_dir, item)
            try:
                if os.path.isfile(src_path):
                    shutil.copy2(src_path, dst_path)
                    changes['copied'].append(item)
                elif os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path)
                    changes['copied'].append(f"{item}/")
            except Exception as e:
                changes['errors'].append({'file': item, 'error': str(e)})
        
        # Update different files
        for item in comparison.diff_files:
            src_path = os.path.join(source_dir, item)
            dst_path = os.path.join(target_dir, item)
            try:
                shutil.copy2(src_path, dst_path)
                changes['updated'].append(item)
            except Exception as e:
                changes['errors'].append({'file': item, 'error': str(e)})
        
        # Delete files not in source if delete=True
        if delete:
            for item in comparison.right_only:
                try:
                    path = os.path.join(target_dir, item)
                    if os.path.isfile(path):
                        os.remove(path)
                    elif os.path.isdir(path):
                        shutil.rmtree(path)
                    changes['deleted'].append(item)
                except Exception as e:
                    changes['errors'].append({'file': item, 'error': str(e)})
        
        return {
            'success': True,
            'changes': changes,
            'summary': {
                'copied': len(changes['copied']),
                'updated': len(changes['updated']),
                'deleted': len(changes['deleted']),
                'errors': len(changes['errors'])
            }
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}
