#!/usr/bin/env python3

import os
import json

import requests
from bs4 import BeautifulSoup

from warc import WarcHost, WarcDescriptor, warc_url

# For each descriptor
# check error code?
# get username
# get content URL? Easy for video, dunno for screenshots

def handle_descriptor(desc, res):
    if desc.kind != "text/html":
        return

    url = warc_url(desc.url)
    if not url:
        return

    print(desc.kind, desc.url, url)

    attempts = 1
    response = requests.get(url)

    while not response and attempts < 5:
        print(response)
        response = requests.get(url)
        attempts += 1

    soup = BeautifulSoup(response.text, features="html.parser")
    username, content = None, None

    if "video" in url:
        username, content = handle_video_page(url, soup)

    if not username or not content:
        return

    if username not in res:
        res[username] = []

    res[username].append(content)

def handle_video_page(url, page):
    table = page.find("table", class_="video_info")

    # Archived video was actually deleted
    if not table:
        return None, None

    # User info is in first row
    row = table.find("tr")
    # And in second column
    col = row.findAll("td")[1]
    profile_url = col.find("a")["href"]
    username = profile_url.rstrip("/").split("/")[-1]

    video_id = url.rstrip("/").split("/")[-1]
    video = warc_url("http://video.xfire.com/{}.mp4".format(video_id))

    return username, video

def main():
    url = "https://archive.org/details/archiveteam_xfire"
    wh = WarcHost(url)

    local = os.path.dirname(os.path.realpath(__file__))
    res_dir = os.path.join(local, "results")

    if not os.path.exists(res_dir):
        os.mkdir(res_dir)

    for archive_url in wh.iter_archive_pages():
        archive_name = archive_url.split("/")[-1]
        archive_dir = os.path.join(res_dir, archive_name)

        if not os.path.exists(archive_dir):
            os.mkdir(archive_dir)

        descriptors = WarcDescriptor.iter_from_url(wh.get_archive_descriptor(archive_url))
        count = 0
        done = False

        # There seems to be about 30k descriptors per archive file, doing
        # a backup every 1k seems sensible enough
        while not done:
            user_content = {}
            backup_file = os.path.join(archive_dir, "bak{}.json".format(count))

            # If file is already there, just consume 1k items from the iterator
            if os.path.exists(backup_file):
                for _ in range(int(1e3)):
                    next(descriptors, None)
            else:
                for _ in range(int(1e3)):
                    desc = next(descriptors, None)
                    if not desc:
                        done = True
                        break

                    handle_descriptor(desc, user_content)

                with open(backup_file, "w") as fh:
                    json.dump(user_content, fh)

            count += 1

        # Now do a K-way merge of all the dicts
        # user_content = {}
        # for count, desc in enumerate(WarcDescriptor.iter_from_url(wh.get_archive_descriptor(archive_url))):
        #     handle_descriptor(desc, user_content)

        # with open(archive_file, "w") as fh:
        #     print("dumping {} - {} users found".format(archive_file, len(user_content)))
        #     json.dump(user_content, fh)


if __name__ == "__main__":
    main()
