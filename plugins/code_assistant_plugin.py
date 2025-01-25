import autopep8
import ast
import astroid
from typing import List, Dict, Any
import pylint.lint
from pylint.reporters import JSONReporter
import io
import sys
from docstring_parser import parse

def plugin_info():
    return {
        'name': 'Code Assistant',
        'description': 'Advanced code analysis and formatting tools'
    }

def get_commands():
    return {
        'analyze_code': {
            'function': analyze_code,
            'description': 'Analyzes code for potential improvements'
        },
        'format_code': {
            'function': format_code,
            'description': 'Auto-formats code using PEP 8'
        },
        'generate_docs': {
            'function': generate_docs,
            'description': 'Generates documentation for code'
        },
        'find_bugs': {
            'function': find_bugs,
            'description': 'Static code analysis for potential bugs'
        }
    }

def analyze_code(code: str) -> Dict[str, Any]:
    """Analyzes Python code for complexity and potential issues"""
    try:
        # Parse the code
        tree = ast.parse(code)
        
        # Analysis results
        results = {
            'complexity': 0,
            'function_count': 0,
            'class_count': 0,
            'line_count': len(code.splitlines()),
            'issues': []
        }
        
        # Analyze nodes
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                results['function_count'] += 1
            elif isinstance(node, ast.ClassDef):
                results['class_count'] += 1
            
        return results
    except Exception as e:
        return {'error': str(e)}

def format_code(code: str, aggressive: int = 1) -> str:
    """Formats Python code according to PEP 8"""
    try:
        formatted_code = autopep8.fix_code(
            code,
            options={'aggressive': aggressive}
        )
        return formatted_code
    except Exception as e:
        return f"Error formatting code: {str(e)}"

def generate_docs(code: str) -> Dict[str, Any]:
    """Generates documentation for Python code"""
    try:
        tree = ast.parse(code)
        docs = {
            'classes': [],
            'functions': [],
            'module_doc': ast.get_docstring(tree)
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_doc = {
                    'name': node.name,
                    'docstring': ast.get_docstring(node) or 'No documentation',
                    'methods': []
                }
                docs['classes'].append(class_doc)
                
            elif isinstance(node, ast.FunctionDef):
                func_doc = {
                    'name': node.name,
                    'docstring': ast.get_docstring(node) or 'No documentation',
                    'params': [arg.arg for arg in node.args.args]
                }
                docs['functions'].append(func_doc)
                
        return docs
    except Exception as e:
        return {'error': str(e)}

def find_bugs(code: str) -> List[Dict[str, Any]]:
    """Performs static code analysis to find potential bugs"""
    try:
        # Create a temporary file-like object
        f = io.StringIO()
        reporter = JSONReporter(f)
        
        # Run pylint
        pylint.lint.Run(
            ['-'], reporter=reporter,
            do_exit=False,
            args=['--disable=all', '--enable=E,F']  # Only errors and fatal errors
        )
        
        # Get the results
        f.seek(0)
        results = f.read()
        
        return [
            {
                'type': issue['type'],
                'line': issue['line'],
                'message': issue['message']
            }
            for issue in results
        ]
    except Exception as e:
        return [{'error': str(e)}]
