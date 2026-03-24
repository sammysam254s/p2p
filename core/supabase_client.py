import requests
import json
from django.conf import settings
from decouple import config


class SupabaseClient:
    def __init__(self):
        self.url = config('SUPABASE_URL')
        self.anon_key = config('SUPABASE_ANON_KEY')
        self.headers = {
            'apikey': self.anon_key,
            'Authorization': f'Bearer {self.anon_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
    
    def _make_request(self, method, endpoint, data=None, params=None):
        """Make HTTP request to Supabase REST API"""
        url = f"{self.url}/rest/v1/{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers, params=params)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            elif method == 'PATCH':
                response = requests.patch(url, headers=self.headers, json=data)
            elif method == 'DELETE':
                response = requests.delete(url, headers=self.headers, params=params)
            
            response.raise_for_status()
            return response.json() if response.content else None
            
        except requests.exceptions.RequestException as e:
            print(f"Supabase API Error: {e}")
            return None
    
    def select(self, table, columns="*", filters=None, order=None, limit=None):
        """Select data from table"""
        params = {'select': columns}
        
        if filters:
            for key, value in filters.items():
                if isinstance(value, str):
                    params[key] = f'eq.{value}'
                else:
                    params[key] = f'eq.{value}'
        
        if order:
            params['order'] = order
        
        if limit:
            params['limit'] = limit
            
        return self._make_request('GET', table, params=params)
    
    def insert(self, table, data):
        """Insert data into table"""
        if isinstance(data, list):
            return self._make_request('POST', table, data=data)
        else:
            return self._make_request('POST', table, data=[data])
    
    def update(self, table, data, filters):
        """Update data in table"""
        params = {}
        for key, value in filters.items():
            params[key] = f'eq.{value}'
        
        endpoint = f"{table}?" + "&".join([f"{k}={v}" for k, v in params.items()])
        return self._make_request('PATCH', endpoint, data=data)
    
    def delete(self, table, filters):
        """Delete data from table"""
        params = {}
        for key, value in filters.items():
            params[key] = f'eq.{value}'
        
        endpoint = f"{table}?" + "&".join([f"{k}={v}" for k, v in params.items()])
        return self._make_request('DELETE', endpoint)


# Global instance
supabase = SupabaseClient()