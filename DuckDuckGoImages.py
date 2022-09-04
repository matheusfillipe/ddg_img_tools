#!/usr/bin/env python3

from pprint import pp
import io
import json
import os
import random
import re
import shutil
import uuid

import requests
from joblib import Parallel, delayed
from PIL import Image


def download(
    query,
    folder=".",
    max_urls=None,
    thumbnails=False,
    parallel=False,
    shuffle=False,
    remove_folder=False,
):
    if thumbnails:
        urls = get_image_thumbnails_urls(query)
    else:
        urls = get_image_urls(query)

    if shuffle:
        random.shuffle(urls)

    if max_urls is not None and len(urls) > max_urls:
        urls = urls[:max_urls]

    if remove_folder:
        _remove_folder(folder)

    _create_folder(folder)
    if parallel:
        return _parallel_download_urls(urls, folder)
    else:
        return _download_urls(urls, folder)


def _download(url, folder, filename=None):
    try:
        filename = str(uuid.uuid4().hex) if filename is None else filename
        while os.path.exists("{}/{}.jpg".format(folder, filename)):
            filename = str(uuid.uuid4().hex)
        response = requests.get(url, stream=True, timeout=1.0, allow_redirects=True)
        with Image.open(io.BytesIO(response.content)) as im:
            with open("{}/{}.jpg".format(folder, filename), "wb") as out_file:
                im.save(out_file)
                return True
    except Exception:
        return False


def _download_urls(urls, folder):
    downloaded = 0
    for url in urls:
        if _download(url, folder):
            downloaded += 1
    return downloaded


def _parallel_download_urls(urls, folder):
    downloaded = 0
    with Parallel(n_jobs=os.cpu_count()) as parallel:
        results = parallel(delayed(_download)(url, folder) for url in urls)
        for result in results:
            if result:
                downloaded += 1
    return downloaded


def get_image_urls(query):
    token = _fetch_token(query)
    return _fetch_search_urls(query, token)


def get_image_thumbnails_urls(query):
    token = _fetch_token(query)
    return _fetch_search_urls(query, token, what="thumbnail")


def _fetch_token(query, URL="https://duckduckgo.com/"):
    res = requests.post(URL, data={"q": query})
    if res.status_code != 200:
        return ""
    match = re.search(r"vqd='([\d-]+)'", res.text, re.M | re.I)
    if match is None:
        return ""
    return match.group(1)


def _fetch_search_urls(query, token, URL="https://duckduckgo.com/", what="image"):

    headers = {
        'authority': 'duckduckgo.com',
        'accept': 'application/json, text/javascript, */* q=0.01',
        'sec-fetch-dest': 'empty',
        'x-requested-with': 'XMLHttpRequest',
        'user-agent': 'Mozilla/5.0 (Macintosh Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'referer': 'https://duckduckgo.com/',
        'accept-language': 'en-US,enq=0.9',
    }
    query = {"vqd": token, "q": query, "l": "en-us", "o": "json", "f": ",,,", "p": "2"}
    urls = []

    res = requests.get(URL + "i.js", params=query, headers=headers)
    if res.status_code != 200:
        return urls

    data = json.loads(res.text)
    for result in data["results"]:
        urls.append(result[what])

    while "next" in data:
        res = requests.get(URL + data["next"], params=query)
        if res.status_code != 200:
            return urls
        data = json.loads(res.text)
        for result in data["results"]:
            urls.append(result[what])
    return urls


def _remove_folder(folder):
    if os.path.exists(folder):
        shutil.rmtree(folder, ignore_errors=True)


def _create_folder(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)


if __name__ == "__main__":
    import sys

    imgs = get_image_urls(" ".join(sys.argv[1:]))
    for url in imgs:
        print(url)
    print(len(imgs))
