import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote
import json


def __extract_id__(id:str) -> str:
    if id.__contains__('/'):
        return id[id.rindex('/')+1:]
    elif id.__contains__(':'):
        return id[id.rindex(':')+1:]
    else:
        return id

def track(id: str) -> json:
    id = __extract_id__(id)
    page = requests.get('https://open.spotify.com/embed/track/' + id)
    soup = BeautifulSoup(page.content, 'html.parser')
    rawResource = str.strip(soup.find("script", {"id": "resource"}).contents[0])
    resource = unquote(rawResource)
    return json.loads(resource)

def album(id:str) -> json:
    id = __extract_id__(id)
    page = requests.get('https://open.spotify.com/embed/album/' + id)
    soup = BeautifulSoup(page.content, 'html.parser')
    rawResource = str.strip(soup.find("script", {"id": "resource"}).contents[0])
    resource = unquote(rawResource)
    return json.loads(resource)

def playlist(id:str) -> json:
    id = __extract_id__(id)
    page = requests.get('https://open.spotify.com/embed/playlist/' + id)
    soup = BeautifulSoup(page.content, 'html.parser')
    rawResource = str.strip(soup.find("script", {"id": "resource"}).contents[0])
    resource = unquote(rawResource)
    return json.loads(resource)