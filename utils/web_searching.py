from googleapiclient.discovery import build
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import os
import pandas as pd
import logging


google_key = os.getenv('GOOGLE_API')
cse_id =  os.getenv('CSE_ID')
logger = logging.getLogger("pe_helper")

def google_search(search_term, api_key, cse_id, **kwargs):
    limit=5
    logger.info(f"Calling Google API with search term: '{search_term}'")
    service = build("customsearch", "v1", developerKey=api_key)
    result = service.cse().list(q=search_term, cx=cse_id, num=limit, **kwargs).execute()
    file_path = 'data/api_count.csv'
    api_count = pd.read_csv(file_path)
    api_count.loc[api_count['api_name'] == 'google-custom-search-api', 'count'] += 1
    api_count.to_csv(file_path, index=False)
    logger.info("Google API count incremented and saved.")
    return result['items']


def search_imslp_scores(link):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(link)
    scores = driver.find_element(By.ID, "wpscoresection")
    div_elements = scores.find_elements(By.CLASS_NAME, 'we')
    links = []
    for element in div_elements:
        link = element.find_element(By.TAG_NAME, 'a')
        href = link.get_attribute('href')
        file_info_2 = element.find_element(By.CLASS_NAME, 'we_file_info2')
        info = file_info_2.find_element(By.TAG_NAME, 'a').get_attribute('title')
        downloads = file_info_2.find_elements(By.CSS_SELECTOR, "span[title]")
        if downloads:
            downloads = downloads[0].text
            try:
                amount_downloads = int(''.join(filter(str.isdigit, downloads)))
            except:
                amount_downloads = 0
        else:
            amount_downloads = 0
        data = {'name': info, 'link': href, 'points': amount_downloads}
        links.append(data)

    driver.quit()
    
    links = [i for i in links if i['points'] != 0]
    links = sorted(links, key=lambda k: k['points'])[::-1][:10]
    return links


def search_scores(search_term: str):
    searches = google_search(search_term, google_key, cse_id)
    main_page = searches[0]
    title = main_page['title']
    link = main_page['link']
    imslp_scores = search_imslp_scores(link)
    return {'title': title, 'link': link, 'imslp_scores': imslp_scores}