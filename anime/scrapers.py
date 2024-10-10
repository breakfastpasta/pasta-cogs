import requests
import re
import json
import asyncio
import inspect

from abc import ABC, abstractmethod
from typing import Literal
from functools import wraps, partial

from bs4 import BeautifulSoup

def run_in_executor(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        if inspect.ismethod(func):
            context, *args = args
            bound_func = partial(func, context)
        else:
            bound_func = func
        return await loop.run_in_executor(None, bound_func, *args, **kwargs)
    return wrapper

class AnimeScraper(ABC):
    def __init__(self, proxy_url=None):
        self._session = requests.Session()
        self._proxy_url = proxy_url
        if self._proxy_url:
            self._session.proxies = {
                'http': proxy_url,
                'https': proxy_url,
            }

    @property
    def session(self):
        return self._session

    @property
    def proxy_url(self):
        return self._proxy_url

    @proxy_url.setter
    def proxy_url(self, value: str):
        self._proxy_url = value
        self._session.proxies = {
            'http': value,
            'https': value,
        }
    
    @run_in_executor
    def get_popular(self, period: Literal['day', 'week', 'month', 'season', 'anticipated']=None, page=None) -> [dict()]:
        return self._get_popular(period, page)

    @abstractmethod
    def _get_popular(self, period, page) -> [dict()]:
        pass

class GoGoAnime(AnimeScraper):
    BASE_URL = "https://ajax.gogocdn.net/ajax"

    def _get_popular(self, period, page):
        period = None
        page = 1 if not page else page
        url = f"{self.BASE_URL}/page-recent-release-ongoing.html?page={str(page)}"

        response = self.session.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        table = soup.select_one('.added_series_body > ul:nth-child(1)')
        series = table.find_all('li')

        retval = []
        i = 10
        for item in series:
            name = item.find('a', title=True).attrs['title']
            name = re.sub(r'\(.*Dub\)', '', name).strip()

            ep = item.find_all('p')[-1].find('a').text
            ep_num = re.search(r'Episode (\d+)', ep).group(1)

            retval.append({
                "name": name,
                "score": i*100,
            })
            i -= 1

        return retval

class HiAnime(AnimeScraper):
    BASE_URL = "https://hianime.to"

    def _get_popular(self, period, page):
        period = 'day' if not period or period not in ['day', 'week', 'month'] else period
        page = None
        url = f"{self.BASE_URL}/top-airing"

        response = self.session.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        table = soup.select_one(f'#top-viewed-{period} > ul:nth-child(1)')
        series = table.find_all('li')

        retval = []    
        i = 10
        for item in series:
            h3 = item.find('h3', class_='film-name')
            name = h3.find('a').text.strip()
            
            retval.append({
                "name": name,
                "score": i*100
            })
            i -= 1

        return retval

class AnimeCorner(AnimeScraper):
    BASE_URL = "https://animecorner.me/category/anime-corner/rankings"

    def _get_popular(self, period, page):
        period = 'week' if not period or period not in ["week", "season", "year", "anticipated"] else period
        page = None
        subpath = f"/anime-of-the-{'season' if period == 'anticipated' else period}"
        url = f"{self.BASE_URL}{subpath}"

        response = self.session.get(url)
        soup = BeautifulSoup(response.text, 'lxml')

        posts = soup.select_one(f'.penci-wrapper-data')
        items = posts.find_all('li', class_='list-post')

        for item in items:
            title_tag = item.find('h2', class_='penci-entry-title')
            if title_tag:
                link_tag = title_tag.find('a')
                if link_tag and period in link_tag.text.lower():
                    post_link = link_tag['href']
                    break
        
        response = self.session.get(post_link)
        soup = BeautifulSoup(response.text, 'lxml')

        table = soup.find('tbody')
        results = table.find_all('tr')

        retval = []
        for result in results:
            info = result.find_all('td')
            title = info[1].text
            score = info[2].text
            retval.append({
                "name": title,
                "score": score,
            })
        
        return retval

class AniTrendz(AnimeScraper):
    BASE_URL = "https://www.anitrendz.com/charts"

    def _get_popular(self, period, page):
        url = f"{self.BASE_URL}/top-anime"

        response = self.session.get(url)

        soup = BeautifulSoup(response.text, 'lxml')

        script = soup.find('script', id="__NEXT_DATA__", type="application/json")
        json_text = script.get_text()
        data = json.loads(json_text)
        chart = data['props']['pageProps']['charts'][0]['choices']

        retval = []

        for item in sorted(chart, key=lambda x: x['position']):
            retval.append({
                "name": item['name'],
                "score": item['total'],
            })
        
        return retval

        # with open('page.html', 'w') as f:
        #     f.write(soup.prettify())


def main():
    p = int(input("Enter page num for gogo (1): ").strip() or "1")
    per_hi = input("Enter period for hianime (DAY/week/month): ").strip().lower() or 'day'
    if per_hi not in ["day", "week", "month"]:
        print("invalid period")
        return
    per_ac = input("Enter period for animecorner (WEEK/season/anticipated): ").strip().lower() or 'week'
    if per_ac not in ["week", "season", "anticipated"]:
        print("invalid period")
        return
    proxy = input("Enter proxy URL (blank for none): ").strip()
    proxy_regex = r"^(?P<protocol>https?|socks[45]):\/\/(?:((?P<username>[^:@]+)(?::(?P<password>[^:@]+))?)@)?(?P<host>(?:[a-zA-Z\d.-]+|\[[a-fA-F\d:]+\])):(?P<port>\d{1,5})$"
    if proxy and not re.match(proxy_regex, proxy):
        print("invalid proxy url")
        return

    gogo = GoGoAnime(proxy_url=proxy)
    hi = HiAnime(proxy_url=proxy)
    ac = AnimeCorner(proxy_url=proxy)
    at = AniTrendz(proxy_url=proxy)

    gogo_popular = gogo.get_popular(page=p)
    hi_popular = hi.get_popular(period=per_hi)
    ac_popular = ac.get_popular(period=per_ac)
    at_popular = at.get_popular()

    print(f'\nGOGOANIME POPULAR (page {p}):')
    i = (p - 1) * 10 + 1
    for s in gogo_popular:
        print(f"{i}. {s['name']}")
        i += 1
    
    i = 1
    print(f'\nHIANIME TOP 10 ({per_hi}):')
    for s in hi_popular:
        print(f"{i}. {s['name']}")
        i += 1

    i = 1
    print(f"\nANIMECORNER RANKINGS ({per_ac}):")
    for s in ac_popular:
        print(f"{i} {s['score']}. {s['name']}")
        i += 1
    
    i = 1
    for s in at_popular:
        print(f"{i} ({s['score']}). {s['name']}")
        i += 1

if __name__ == '__main__':
    main()


    
