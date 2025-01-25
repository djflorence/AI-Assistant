from typing import List

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
