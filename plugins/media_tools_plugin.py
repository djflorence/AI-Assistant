from PIL import Image, ImageEnhance, ImageFilter
import os
from typing import Dict, Any, List, Tuple
from pydub import AudioSegment
import cv2
import numpy as np
from datetime import datetime
import json

def plugin_info():
    return {
        'name': 'Media Tools',
        'description': 'Tools for image, audio, and video manipulation'
    }

def get_commands():
    return {
        'image_edit': {
            'function': image_edit,
            'description': 'Basic image editing operations'
        },
        'audio_convert': {
            'function': audio_convert,
            'description': 'Convert audio between formats'
        },
        'video_trim': {
            'function': video_trim,
            'description': 'Trim video files'
        },
        'media_info': {
            'function': media_info,
            'description': 'Get detailed media file information'
        }
    }

def image_edit(image_path: str, operations: List[Dict[str, Any]], 
               output_path: str = None) -> Dict[str, Any]:
    """
    Perform basic image editing operations
    
    Operations format:
    [
        {"type": "resize", "width": 800, "height": 600},
        {"type": "rotate", "angle": 90},
        {"type": "filter", "name": "blur"},
        {"type": "adjust", "brightness": 1.2, "contrast": 1.1, "saturation": 1.0}
    ]
    """
    try:
        # Open the image
        img = Image.open(image_path)
        
        # Process each operation in sequence
        for op in operations:
            op_type = op.get('type', '').lower()
            
            if op_type == 'resize':
                width = op.get('width', img.width)
                height = op.get('height', img.height)
                img = img.resize((width, height), Image.LANCZOS)
                
            elif op_type == 'rotate':
                angle = op.get('angle', 0)
                img = img.rotate(angle, expand=True)
                
            elif op_type == 'filter':
                filter_name = op.get('name', '').lower()
                if filter_name == 'blur':
                    img = img.filter(ImageFilter.BLUR)
                elif filter_name == 'sharpen':
                    img = img.filter(ImageFilter.SHARPEN)
                elif filter_name == 'edge_enhance':
                    img = img.filter(ImageFilter.EDGE_ENHANCE)
                    
            elif op_type == 'adjust':
                brightness = op.get('brightness', 1.0)
                contrast = op.get('contrast', 1.0)
                saturation = op.get('saturation', 1.0)
                
                if brightness != 1.0:
                    enhancer = ImageEnhance.Brightness(img)
                    img = enhancer.enhance(brightness)
                if contrast != 1.0:
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(contrast)
                if saturation != 1.0:
                    enhancer = ImageEnhance.Color(img)
                    img = enhancer.enhance(saturation)
        
        # Save the result
        if not output_path:
            base, ext = os.path.splitext(image_path)
            output_path = f"{base}_edited{ext}"
        
        img.save(output_path)
        
        return {
            'success': True,
            'output_path': output_path,
            'original_size': os.path.getsize(image_path),
            'new_size': os.path.getsize(output_path),
            'dimensions': img.size
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def audio_convert(audio_path: str, output_format: str, 
                 output_path: str = None) -> Dict[str, Any]:
    """Convert audio files between formats"""
    try:
        # Load the audio file
        audio = AudioSegment.from_file(audio_path)
        
        # Generate output path if not provided
        if not output_path:
            base = os.path.splitext(audio_path)[0]
            output_path = f"{base}.{output_format.lower()}"
        
        # Export in new format
        audio.export(output_path, format=output_format.lower())
        
        return {
            'success': True,
            'output_path': output_path,
            'original_size': os.path.getsize(audio_path),
            'new_size': os.path.getsize(output_path),
            'duration_seconds': len(audio) / 1000.0,
            'channels': audio.channels,
            'sample_width': audio.sample_width,
            'frame_rate': audio.frame_rate
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def video_trim(video_path: str, start_time: float, end_time: float, 
               output_path: str = None) -> Dict[str, Any]:
    """Trim video files"""
    try:
        # Open the video file
        cap = cv2.VideoCapture(video_path)
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Generate output path if not provided
        if not output_path:
            base, ext = os.path.splitext(video_path)
            output_path = f"{base}_trimmed{ext}"
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        # Set starting frame
        start_frame = int(start_time * fps)
        end_frame = int(end_time * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        # Process frames
        current_frame = start_frame
        while current_frame <= end_frame:
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)
            current_frame += 1
        
        # Release resources
        cap.release()
        out.release()
        
        return {
            'success': True,
            'output_path': output_path,
            'original_size': os.path.getsize(video_path),
            'new_size': os.path.getsize(output_path),
            'duration': end_time - start_time,
            'fps': fps,
            'resolution': f"{width}x{height}"
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def media_info(file_path: str) -> Dict[str, Any]:
    """Get detailed information about media files"""
    try:
        file_type = None
        info = {
            'file_info': {
                'size': os.path.getsize(file_path),
                'created': datetime.fromtimestamp(os.path.getctime(file_path)).isoformat(),
                'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                'extension': os.path.splitext(file_path)[1].lower()
            }
        }
        
        # Check if it's an image
        try:
            with Image.open(file_path) as img:
                info['image_info'] = {
                    'format': img.format,
                    'mode': img.mode,
                    'dimensions': img.size,
                    'dpi': img.info.get('dpi'),
                    'exif': json.dumps(img._getexif()) if hasattr(img, '_getexif') and img._getexif() else None
                }
                file_type = 'image'
        except Exception:
            pass
        
        # Check if it's an audio file
        try:
            audio = AudioSegment.from_file(file_path)
            info['audio_info'] = {
                'duration_seconds': len(audio) / 1000.0,
                'channels': audio.channels,
                'sample_width': audio.sample_width,
                'frame_rate': audio.frame_rate,
                'frame_count': len(audio.get_array_of_samples()),
                'max_amplitude': audio.max,
                'rms': audio.rms
            }
            file_type = 'audio'
        except Exception:
            pass
        
        # Check if it's a video
        try:
            cap = cv2.VideoCapture(file_path)
            if cap.isOpened():
                info['video_info'] = {
                    'fps': cap.get(cv2.CAP_PROP_FPS),
                    'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                    'duration': cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS),
                    'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                    'fourcc': cap.get(cv2.CAP_PROP_FOURCC)
                }
                file_type = 'video'
                cap.release()
        except Exception:
            pass
        
        info['file_type'] = file_type
        return {'success': True, 'info': info}
    except Exception as e:
        return {'success': False, 'error': str(e)}
