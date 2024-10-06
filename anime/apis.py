import requests
import datetime
import re
import pprint

from collections import deque

from .utils import get_midnights, html_to_discord

class AniList:
    BASE_URL = 'https://graphql.anilist.co'

    @classmethod
    def airingtoday(cls):
        midnights = get_midnights()
        query = '''
        query AiringSchedules($airingAtGreater: Int, $airingAtLesser: Int, $sort: [AiringSort]) {
            Page {
                airingSchedules(airingAt_greater: $airingAtGreater, airingAt_lesser: $airingAtLesser, sort: $sort) {
                    media {
                        title {
                            english
                            romaji
                        }
                        id
                        trending
                    }
                    airingAt
                    timeUntilAiring
                    episode
                }
            }
        }
        '''

        variables = {
            "airingAtGreater": midnights[0],
            "airingAtLesser": midnights[1],
            "sort": "TIME"
        }

        response = requests.post(cls.BASE_URL, json={'query': query, 'variables': variables})

        if response.ok:
            data = response.json()

            retval = []
            for e in data['data']['Page']['airingSchedules']:
                title = e['media']['title']['english'] if e['media']['title']['english'] else e['media']['title']['romaji']
                ep = e['episode']
                time = e['airingAt']

                retval.append({
                    'name': title,
                    'episode': ep,
                    'airtime': time,
                })
            
            return retval

    @classmethod
    def search(cls, search_query: str):
        query = '''
        query Media($search: String, $type: MediaType) {
            Media(search: $search, type: $type) {
                averageScore
                coverImage {
                    large
                }
                episodes
                genres
                id
                idMal
                meanScore
                popularity
                rankings {
                    allTime
                    context
                    rank
                }
                seasonYear
                startDate {
                    day
                    month
                    year
                }
                synonyms
                tags {
                    name
                }
                title {
                    english(stylised: true)
                    romaji
                }
                trending
                trailer {
                    site
                    id
                }
                description
                status
            }
        }
        '''

        variables = {
            "search": search_query,
            "type": "ANIME",
        }

        response = requests.post(cls.BASE_URL, json={'query': query, 'variables': variables})

        if response.ok:
            data = response.json()
            item = data['data']['Media']

            retval = {
                "title": item['title'],
                "thumb": item['coverImage']['large'],
                "num_episodes": item['episodes'],
                "genres": item['genres'],
                "score": item['meanScore'],
                "popularity": item['popularity'],
                "start": f"{item['startDate']['month']}/{item['startDate']['day']}/{item['startDate']['year']}",
                "tags": [t['name'] for t in item['tags']],
                "trailer": f"[YouTube](https://www.youtube.com/watch?v={item['trailer']['id']})" if item['trailer'] else "No trailer",
                "description": html_to_discord(item['description']),
                "status": item['status'],
            }

            return retval

    @classmethod
    def get_popular(cls, page_num: int=1):
        """Show today's top trending anime"""
        # Here we define our query as a multi-line string
        query = '''
        query Page($status: MediaStatus, $type: MediaType, $sort: [MediaSort], $page: Int, $perPage: Int) {
            Page(page: $page, perPage: $perPage) {
                media(status: $status, type: $type, sort: $sort) {
                    id
                    title {
                        english
                        romaji
                    }
                    trending
                    siteUrl
                }
            }
        }
        '''

        variables = {
            "status": "RELEASING",
            "sort": "TRENDING_DESC",
            "type": "ANIME",
            "page": page_num,
            "perPage": 10,
        }

        response = requests.post(cls.BASE_URL, json={'query': query, 'variables': variables})

        if response.ok:
            data = response.json()
            retval = []

            for media in data['data']['Page']['media']:
                title = media['title']['english'] if media['title']['english'] else media['title']['romaji']
                trending = media['trending']
                link = media['siteUrl']

                retval.append({
                    'name': title,
                    'score': trending,
                })
            
            return retval
        
class AniDB:
    pass

class Jellyfin:
    pass

class Plex:
    pass

class MyAnimeList:
    BASE_URL = "https://api.jikan.moe/v4"

    @classmethod
    def get_popular(cls, n=25):
        url = f"{cls.BASE_URL}/top/anime"

        params = {
            'type': "tv", 
            'filter': "airing",
            'limit': n,
            'page': 1,
        }
        headers = {'Content-Type': 'application/json'}

        response = requests.get(url, params=params, headers=headers).json()

        retval = []
        for item in response['data']:
            preferred_title = next((title['title'] for title in item['titles'] if title['type'] == 'English'), item['titles'][0]['title'])
            score = item['score']

            retval.append({
                'name': preferred_title,
                'score': int(score * 100)
            })
        

        return retval