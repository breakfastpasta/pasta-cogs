import requests
import re

from abc import ABC, abstractmethod
from typing import Literal

from bs4 import BeautifulSoup

class AnimeScraper(ABC):
    @abstractmethod
    def get_popular(self, period, page) -> [dict()]:
        pass

class GoGoAnime(AnimeScraper):
    BASE_URL = "https://ajax.gogocdn.net/ajax"

    def get_popular(self, period=None, page=1):
        url = f"{self.BASE_URL}/page-recent-release-ongoing.html?page={str(page)}"

        response = requests.get(url)

        soup = BeautifulSoup(response.text, 'html.parser')

        table = soup.select_one('.added_series_body > ul:nth-child(1)')
        series = table.find_all('li')

        retval = []

        for item in series:
            name = item.find('a', title=True).attrs['title']
            name = re.sub(r'\(.*Dub\)', '', name).strip()

            ep = item.find_all('p')[-1].find('a').text
            ep_num = re.search(r'Episode (\d+)', ep).group(1)

            retval.append({
                "name": name,
                "episode": ep_num,
            })

        return retval

class HiAnime(AnimeScraper):
    BASE_URL = "https://hianime.to/top-airing"

    def get_popular(self, period: Literal["day", "week", "month"]="day", page=None):
        url = f"{self.BASE_URL}"

        response = requests.get(url)

        soup = BeautifulSoup(response.text, 'html.parser')

        table = soup.select_one(f'#top-viewed-{period} > ul:nth-child(1)')
        series = table.find_all('li')

        retval = []

        for item in series:
            h3 = item.find('h3', class_='film-name')
            name = h3.find('a').text.strip()
            
            retval.append({
                "name": name,
                "episode": None,
            })

        return retval


def main():
    p = int(input("Enter page num for gogo (1): ").strip() or "1")
    per = input("Enter period for hianime (DAY/week/month): ").strip() or 'day'

    gogo = GoGoAnime()
    hi = HiAnime()

    gogo_popular = gogo.get_popular(page=p)
    hi_popular = hi.get_popular(period=per)

    print(f'\nGOGOANIME POPULAR (page {p}):')
    i = (p - 1) * 10 + 1
    for s in gogo_popular:
        print(f"{i}. {s['name']} (ep {s['episode']})")
        i += 1
    
    i = 1
    print(f'\nHIANIME TOP 10 ({per}):')
    for s in hi_popular:
        print(f"{i}. {s['name']}")
        i += 1


if __name__ == '__main__':
    main()


    
