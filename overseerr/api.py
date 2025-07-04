import requests
from urllib.parse import quote

class Overseerr_API():
    def __init__(self, endpoint, api_key):
        self.endpoint = endpoint

        self._session = requests.Session()
        self._api_key = api_key
        self._headers = {
            "X-API-Key": self._api_key,
            "accept": "application/json"
        }

        self._request_defaults = {
            'seasons': 'all',
            'is4k': False,
        }

        self._default_user = 10

    async def set_api_key(self, key: str) -> None:
        self._api_key = key
        self._headers['X-API-Key'] = key

    async def _get_users(self):
        url = f"{self.endpoint}/user"
        params = {
            'take': 20,
            'skip': 0,
            'sort': 'created',
        }

        response = self._session.get(url, params=params, headers=self._headers)
        if not response.ok:
            return []

        data = response.json()
        #ret = data
        ret = [{'id': x['id'], 'username': x['displayName']} for x in data['results']]

        return ret

    async def get_user_by_discord_id(self, discord_user_id: str) -> int|None:
        params = {}
        ret = None
        users = await self._get_users()
        ids = [u['id'] for u in users]
        for i in ids:
            url = f"{self.endpoint}/user/{i}/settings/notifications"
            response = self._session.get(url, params=params, headers=self._headers)
            if response.ok:
                data = response.json()
                current_discord_id = data.get('discordId')
                if current_discord_id and current_discord_id == discord_user_id:
                    ret = i
                    break
        
        return ret
            
    async def create_request(self, media_type: str, media_id: int, user_id=None):
        url = f"{self.endpoint}/request"
        data = self._request_defaults | {
            'mediaId': media_id,
            'mediaType': media_type
        }

        headers = self._headers | {
            'Content-Type': 'application/json',
            'X-API-User': str(user_id) if user_id else str(self._default_user)
        }
        response = self._session.post(url=url, json=data, headers=headers)

        if not response.ok:
            return

        data = response.json()
        return data

    async def get_item(self, media_type, media_id):
        url = f"{self.endpoint}/{media_type}/{media_id}"
        response = self._session.get(url, params={'language': 'en'}, headers=self._headers)
        if response.ok:
            data = response.json()
            return data
    
    async def search(self, query):
        url = f"{self.endpoint}/search"
        params = {
            'query': quote(query),
            'page': 1,
            'language': 'en',
        }
        response = self._session.get(url, params=params, headers=self._headers)

        if response.ok:
            data = response.json()['results']
            return data

