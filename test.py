from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
import pandas as pd
import time
import re


# Setup Chrome
chrome_options = Options()
chrome_options.add_argument("--headless")


def scrape_data(link):

    driver = webdriver.Chrome(options=chrome_options)

    # Navigate to the page
    driver.get(link)
    time.sleep(2)

    # Verify it's SignUpGenius
    try:
        site = driver.find_element(By.XPATH, f'/html/body/header/div/div[2]/a/img')
    except NoSuchElementException:
        return
    if site.get_attribute("alt") != 'SignUpGenius':
        return

    # Extract information
    date = driver.find_element(By.XPATH, f'//*[@id="signupcontainer"]/div[1]/div[2]/div[2]/div[2]/div/div[2]').text
    date = re.sub(r"\s*\([^)]*\)", "", date) # Remove day

    room = driver.find_element(By.XPATH, f'//*[@id="signupcontainer"]/div[1]/div[2]/div[2]/div[4]/div/div[2]/span').text

    bookings = []
    i = 1
    while True:
        try:
            time_slot = driver.find_element(By.XPATH, f'//*[@id="signupcontainer"]/div[3]/div/div[3]/div/table/tbody/tr/td[4]/ng-include/table/tbody/tr[{i}]/td/div/div[1]/div[2]/div[1]/div[1]/div[1]/span').text
            # Clean time slot value
            time_slot = re.sub(r"(\d{2})(\d{2})", r"\1 \2", time_slot)
            time_slot = re.sub(r"\s*-\s*", " - ", time_slot)

            x = 1
            while x:
                try:
                    name = driver.find_element(By.XPATH, f'//*[@id="signupcontainer"]/div[3]/div/div[3]/div/table/tbody/tr/td[4]/ng-include/table/tbody/tr[{i}]/td/div/div[2]/div/participant-summary/div/div[{x}]/div/p/span').text
                    admin_num = driver.find_element(By.XPATH, f'//*[@id="signupcontainer"]/div[3]/div/div[3]/div/table/tbody/tr/td[4]/ng-include/table/tbody/tr[{i}]/td/div/div[2]/div/participant-summary/div/div[{x}]/div/div/span[3]/span[1]').get_attribute("textContent")
                    bookings.append({
                        "date": date,
                        "room": room,
                        "time_slot": time_slot,
                        "name": name,
                        "admin_num": admin_num
                    })
                except NoSuchElementException:
                    break
                x += 1

        except NoSuchElementException:
            break
        i += 1

    df = pd.DataFrame(bookings)
    print(df)


def scrape_links():
    pass


scrape_data('https://www.signupgenius.com/go/10C0E49AEAA2EAAF5C07-57043421-theory')