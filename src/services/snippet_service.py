import json
import os
from datetime import datetime
from typing import List, Dict

class SnippetService:
    def __init__(self, snippets_file: str = "snippets.json"):
        self.snippets_file = snippets_file
        self.snippets = self._load_snippets()

    def _load_snippets(self) -> List[Dict]:
        if os.path.exists(self.snippets_file):
            with open(self.snippets_file, 'r') as f:
                return json.load(f)
        return []

    def _save_snippets(self):
        with open(self.snippets_file, 'w') as f:
            json.dump(self.snippets, f, indent=2)

    def add_snippet(self, title: str, code: str, language: str, tags: List[str] = None):
        snippet = {
            'id': len(self.snippets) + 1,
            'title': title,
            'code': code,
            'language': language,
            'tags': tags or [],
            'created_at': datetime.now().isoformat(),
            'times_used': 0
        }
        self.snippets.append(snippet)
        self._save_snippets()
        return snippet

    def get_snippets(self, tag: str = None) -> List[Dict]:
        if tag:
            return [s for s in self.snippets if tag in s['tags']]
        return self.snippets

    def search_snippets(self, query: str) -> List[Dict]:
        query = query.lower()
        return [s for s in self.snippets if 
                query in s['title'].lower() or 
                query in s['code'].lower() or 
                any(query in tag.lower() for tag in s['tags'])]

    def use_snippet(self, snippet_id: int) -> str:
        for snippet in self.snippets:
            if snippet['id'] == snippet_id:
                snippet['times_used'] += 1
                self._save_snippets()
                return snippet['code']
        return ""
