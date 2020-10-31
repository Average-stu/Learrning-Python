from pathlib import Path
import requests
import time
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from multiprocessing.dummy import Pool
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from typing import *
import argparse
from temp_account import username , passwd


class PrivateException(Exception):
    pass

class InstagramPV:

    def __init__(self, username: str, password: str, folder: Path, profile_name: str):
        """
        :param folder: Folder name that will save the posts
        :param profile_name: The profile name that will search
        """

        self.username = username
        self.password = password
        self.folder = folder
        self.http_base = requests.Session()
        self.profile_name = profile_name
        self.links: List[str] = []
        self.pictures: List[str] = []
        self.videos: List[str] = []
        self.url: str = 'https://www.instagram.com/{name}/'
        self.posts: int = 0
        self.MAX_WORKERS: int = 8
        self.N_PROCESSES: int = 8
        self.driver = webdriver.Firefox()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.http_base.close()
        self.driver.close()

    def check_availability(self) -> None:
        """
        Checking Status code, Taking number of posts, Privacy and followed by viewer
        Raise Error if the Profile is private and not following by viewer
        :return: None
        """
        search = self.http_base.get(self.url.format(name=self.profile_name), params={'__a': 1})
        search.raise_for_status()

        load_and_check = search.json()
        self.posts = load_and_check.get('graphql').get('user').get('edge_owner_to_timeline_media').get('count')
        privacy = load_and_check.get('graphql').get('user').get('is_private')
        followed_by_viewer = load_and_check.get('graphql').get('user').get('followed_by_viewer')
        if privacy and not followed_by_viewer:
            raise PrivateException('[!] Account is private')

    def create_folder(self) -> None:
        """Create the folder name"""
        self.folder.mkdir(exist_ok=True)

    def login(self) -> None:
        """Login To Instagram"""
        self.driver.get('https://www.instagram.com/accounts/login')
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'form')))
        self.driver.find_element_by_name('username').send_keys(self.username)
        self.driver.find_element_by_name('password').send_keys(self.password)
        submit = self.driver.find_element_by_tag_name('form')
        submit.submit()

        """Check For Invalid Credentials"""
        try:
            var_error = WebDriverWait(self.driver, 4).until(EC.presence_of_element_located((By.CLASS_NAME, 'eiCW-')))
            raise ValueError(var_error.text)
        except TimeoutException:
            pass

        try:
            """Close Notifications"""
            notifications = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//button[text()="Not Now"]')))
            notifications.click()
        except NoSuchElementException:
            pass

        """Taking cookies"""
        cookies = {
            cookie['name']: cookie['value']
            for cookie in self.driver.get_cookies()
        }

        self.http_base.cookies.update(cookies)

        """Check for availability"""
        self.check_availability()

        self.driver.get(self.url.format(name=self.profile_name))

        self.scroll_down()

    def posts_urls(self) -> None:
        """Taking the URLs from posts and appending in self.links"""
        elements = self.driver.find_elements_by_xpath('//a[@href]')
        for elem in elements:
            urls = elem.get_attribute('href')
            if 'p' in urls.split('/'):
                if urls not in self.links:
                    self.links.append(urls)

    def scroll_down(self) -> None:
        """Scrolling down the page and taking the URLs"""
        last_height = self.driver.execute_script('return document.body.scrollHeight')
        while True:
            self.driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
            time.sleep(1)
            self.posts_urls()
            time.sleep(1)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        self.submit_links()

    def submit_links(self) -> None:
        """Gathering Images and Videos and pass to function <fetch_url> Using ThreadPoolExecutor"""

        self.create_folder()

        print('[!] Ready for video - images'.title())
        print(f'[*] extracting {len(self.links)} posts , please wait...'.title())

        new_links = (urllib.parse.urljoin(link, '?__a=1') for link in self.links)
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            for link in new_links:
                executor.submit(self.fetch_url, link)

    def get_fields(self, nodes: Dict, *keys) -> Any:
        """
        :param nodes: The json data from the link using only the first two keys 'graphql' and 'shortcode_media'
        :param keys: Keys that will be add to the nodes and will have the results of 'type' or 'URL'
        :return: The value of the key <fields>
        """
        fields = nodes['graphql']['shortcode_media']
        for key in keys:
            fields = fields[key]
        return fields

    def fetch_url(self, url: str) -> None:
        """
        This function extracts images and videos
        :param url: Taking the url
        :return None
        """
        logging_page_id = self.http_base.get(url.split()[0]).json()
        if self.get_fields(logging_page_id, '__typename') == 'GraphImage':
            image_url = self.get_fields(logging_page_id, 'display_url')
            self.pictures.append(image_url)

        elif self.get_fields(logging_page_id, '__typename') == 'GraphVideo':
            video_url = self.get_fields(logging_page_id, 'video_url')
            self.videos.append(video_url)

        elif self.get_fields(logging_page_id, '__typename') == 'GraphSidecar':
            for sidecar in self.get_fields(logging_page_id, 'edge_sidecar_to_children', 'edges'):
                if sidecar['node']['__typename'] == 'GraphImage':
                    image_url = sidecar['node']['display_url']
                    self.pictures.append(image_url)
                else:
                    video_url = sidecar['node']['video_url']
                    self.videos.append(video_url)
        else:
            print(f'Warning {url}: has unknown type of {self.get_fields(logging_page_id,"__typename")}')

    def download_video(self, new_videos: Tuple[int, str]) -> None:
        """
        Saving the video content
        :param new_videos: Tuple[int,str]
        :return: None
        """
        number, link = new_videos

        with open(self.folder / f'Video{number}.mp4', 'wb') as f:
            content_of_video = self.http_base.get(link).content
            f.write(content_of_video)

    def images_download(self, new_pictures: Tuple[int, str]) -> None:
        """
        Saving the picture content
        :param new_pictures: Tuple[int, str]
        :return: None
        """

        number, link = new_pictures
        with open(self.folder / f'Image{number}.jpg', 'wb') as f:
            content_of_picture = self.http_base.get(link).content
            f.write(content_of_picture)

    def downloading_video_images(self) -> None:
        """Using multiprocessing for Saving Images and Videos"""
        print('[*] ready for saving images and videos!'.title())
        picture_data = enumerate(self.pictures)
        video_data = enumerate(self.videos)
        pool = Pool(self.N_PROCESSES)
        pool.map(self.images_download, picture_data)
        pool.map(self.download_video, video_data)
        print('[+] Done')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-F', '--filename', help='Filename for storing data', action='store', required=True)
    parser.add_argument('-T', '--target', help='Profile name to search', action='store', required=True)
    args = parser.parse_args()
    with InstagramPV(username, passwd, Path(args.filename), args.target) as pv:
        pv.login()
        pv.downloading_video_images()

if __name__ == '__main__':
    main()