import discord
from discord.ext import commands, tasks
from utils.variables import SGT, last_update
import pandas as pd
from datetime import datetime
import re
import os
import csv
import asyncio
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, WebDriverException
import time
import logging


# Get logger
logger = logging.getLogger("pe_helper")


class BackgroundTasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.count_messages_task = None
        self.collect_links_task = None


    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("Starting background tasks.")
        if self.count_messages_task is None or not self.count_messages_task.is_running():
            self.count_messages_task = self.count_messages.start()
        else:
            logger.info("count_messages task already running.")
        
        if self.collect_links_task is None:
            logger.info("Starting collect_links_time loop.")
            self.collect_links_task = self.bot.loop.create_task(self.collect_links_time())
        else:
            logger.info("collect_links_time loop already running.")

    
    async def collect_links_time(self):
        try:
            logger.info("Running initial collect_and_scrape on startup.")
            await self.collect_and_scrape()
        except Exception as e:
            logger.error(f"Error during initial collect_and_scrape: {e}")

        while True:
            now = datetime.datetime.now(datetime.timezone.utc).astimezone()

            # Set target to today at 5 PM
            target_time = now.replace(hour=17, minute=0, second=0, microsecond=0)

            # If it's already past 5 PM, schedule for 5 PM tomorrow
            if now >= target_time:
                target_time += datetime.timedelta(days=1)

            wait_seconds = (target_time - now).total_seconds()
            logger.info(f"collect_links_time sleeping for {wait_seconds:.2f} seconds until next 5 PM SGT.")
            await asyncio.sleep(wait_seconds)
            try:
                await self.collect_and_scrape()
            except Exception as e:
                logger.error(f"Error during scheduled collect_and_scrape: {e}", exc_info=True)


    @tasks.loop(hours=1)
    async def count_messages(self):
        logger.info("Starting count_messages task.")

        guild = discord.utils.get(self.bot.guilds, name="NYP Piano Ensemble")
        message_counts: dict[str, int] = {}
        word_counts: dict[str, int] = {}
        target_roles = ['Member', 'Alumni']
        role_objs = [discord.utils.get(guild.roles, name=r) for r in target_roles]

        scanned = []
        for ch in guild.text_channels:
            if not any(ch.permissions_for(role).view_channel for role in role_objs if role):
                continue
            try:
                async for msg in ch.history(limit=None):
                    if not isinstance(msg.author, discord.Member) or msg.author.bot:
                        continue
                    name = msg.author.display_name
                    message_counts.setdefault(name, 0)
                    word_counts.setdefault(name, 0)
                    message_counts[name] += 1
                    word_counts[name] += len(msg.content.split())
            except discord.Forbidden:
                logger.warning(f"Forbidden access to channel: {ch.name}, skipping.")
                continue
            except Exception as e:
                logger.error(f"Error reading messages from channel {ch.name}: {e}", exc_info=True)
                continue
            scanned.append(ch.name)

        try:
            df = pd.DataFrame([
                {"Name": n, "Message Count": message_counts[n], "Word Count": word_counts[n]}
                for n in message_counts
            ])
            
            df.sort_values("Message Count", ascending=False).head(10).to_csv("data/top_messages.csv", index=False)
            df.sort_values("Word Count", ascending=False).head(10).to_csv("data/top_words.csv", index=False)
            with open("data/channels.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(scanned))

            global last_update
            last_update = datetime.now(SGT)
            logger.info("count_messages task completed and CSV files updated.")
        except Exception as e:
            logger.error(f"Error saving message stats CSV files: {e}")
    

    async def collect_links(self):
        guild = discord.utils.get(self.bot.guilds, name="NYP Piano Ensemble")
        target_channel = discord.utils.get(guild.text_channels, name="🎹┃weekly-sessions")

        # Check if weekly session channel exists
        if not target_channel:
            logger.error("Channel not found.")
            return

        url_pattern = r'https?://\S+'
        csv_path = "data/links.csv"

        # Load existing URLs
        existing_urls = set()
        if os.path.exists(csv_path):
            try:
                with open(csv_path, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    existing_urls = {row["url"] for row in reader}
                logger.info(f"Loaded {len(existing_urls)} existing URLs from links.csv.")
            except Exception as e:
                logger.error(f"Error reading links.csv: {e}")

        new_links = []
        try:
            async for msg in target_channel.history(limit=None):
                if not isinstance(msg.author, discord.Member) or msg.author.bot:
                    continue

                links = re.findall(url_pattern, msg.content)
                for url in links:
                    if "www.signupgenius.com" in url and url not in existing_urls:
                        new_links.append({"url": url, "scanned": 0, "state": -1})
                        existing_urls.add(url)
        except Exception as e:
            logger.error(f"Error scanning messages in channel '{target_channel.name}': {e}")


        if new_links:
            try:
                file_exists = os.path.exists(csv_path)
                with open(csv_path, mode="a", encoding="utf-8", newline="") as f:
                    fieldnames = ["url", "scanned", "state"]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)

                    if not file_exists:
                        writer.writeheader()
                    writer.writerows(new_links)

                logger.info(f"Added {len(new_links)} new links to links.csv.")
            except Exception as e:
                logger.error(f"Error writing to links.csv: {e}", exc_info=True)
        else:
            logger.info("No new links found to add.")

    

    # Function to scrape details from SignUpGenius
    async def scrape_link(self, link: str, df_existing: pd.DataFrame, df_links: pd.DataFrame):
        logger.info(f"Scraping link: {link}")
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

        try:
            driver = webdriver.Chrome(options=chrome_options)
        except WebDriverException as e:
            logger.error(f"Failed to start Chrome WebDriver: {e}", exc_info=True)
            return df_existing, df_links

        # Navigate to the page
        driver.get(link)
        time.sleep(3)
        
        scrapable = True
        try:
            # Extract information
            date = driver.find_element(By.XPATH, f'//*[@id="signupcontainer"]/div[1]/div[2]/div[2]/div[2]/div/div[2]').text
            date = re.sub(r"\s*\([^)]*\)", "", date).strip() # Remove day
            date = datetime.strptime(date, "%m/%d/%Y").date()
            
            today = datetime.now(SGT).date()

            if today > date:
                df_links.loc[df_links["url"] == link, "state"] = 2  # Indicate weekly session has passed
                if df_links.loc[df_links["url"] == link, "scanned"].values[0] == 1:
                    logger.info(f"Session date passed and already scanned for link: {link}")
                    return df_existing, df_links

            room = driver.find_element(By.XPATH, f'//*[@id="signupcontainer"]/div[1]/div[2]/div[2]/div[4]/div/div[2]/span').text

            # Remove existing records related to this session
            if not df_existing.empty:
                df_existing = df_existing[~((df_existing["date"] == date) & (df_existing["room"] == room))]


        except NoSuchElementException:
            scrapable = False
            logger.warning(f"Scrape failed - necessary elements not found for link: {link}")
        
        if scrapable == False:
            df_links.loc[df_links["url"] == link, "state"] = 0  # Indicate link is unscrapable
            return df_existing, df_links

        df_links.loc[df_links["url"] == link, "state"] = 1

        bookings = []
        i = 1
        while True:
            try:
                def find_with_fallback(driver, xpath_variants):
                    for xpath in xpath_variants:
                        try:
                            return driver.find_element(By.XPATH, xpath)
                        except NoSuchElementException:
                            continue
                    raise NoSuchElementException(f"None of the XPaths matched: {xpath_variants}")
                time_slot_xpath_3 = f'//*[@id="signupcontainer"]/div[3]/div/div[3]/div/table/tbody/tr/td[4]/ng-include/table/tbody/tr[{i}]/td/div/div[1]/div[2]/div[1]/div[1]/div[1]/span'
                time_slot_xpath_4 = f'//*[@id="signupcontainer"]/div[3]/div/div[4]/div/table/tbody/tr/td[4]/ng-include/table/tbody/tr[{i}]/td/div/div[1]/div[2]/div[1]/div[1]/div[1]/span'
                time_slot = find_with_fallback(driver, [time_slot_xpath_3, time_slot_xpath_4]).text

                # Clean time slot value
                time_slot = re.sub(r"(\d{2})(\d{2})", r"\1 \2", time_slot)
                time_slot = re.sub(r"\s*-\s*", " - ", time_slot)

                x = 1
                while x:
                    try:
                        name_xpath_3 = f'//*[@id="signupcontainer"]/div[3]/div/div[3]/div/table/tbody/tr/td[4]/ng-include/table/tbody/tr[{i}]/td/div/div[2]/div/participant-summary/div/div[{x}]/div/p/span'
                        name_xpath_4 = f'//*[@id="signupcontainer"]/div[3]/div/div[4]/div/table/tbody/tr/td[4]/ng-include/table/tbody/tr[{i}]/td/div/div[2]/div/participant-summary/div/div[{x}]/div/p/span'
                        admin_num_xpath_3 = f'//*[@id="signupcontainer"]/div[3]/div/div[3]/div/table/tbody/tr/td[4]/ng-include/table/tbody/tr[{i}]/td/div/div[2]/div/participant-summary/div/div[{x}]/div/div/span[3]/span[1]'
                        admin_num_xpath_4 = f'//*[@id="signupcontainer"]/div[3]/div/div[4]/div/table/tbody/tr/td[4]/ng-include/table/tbody/tr[{i}]/td/div/div[2]/div/participant-summary/div/div[{x}]/div/div/span[3]/span[1]'
                        name = find_with_fallback(driver, [name_xpath_3, name_xpath_4]).text
                        admin_num = find_with_fallback(driver, [admin_num_xpath_3, admin_num_xpath_4]).get_attribute("textContent")

                        df_links.loc[df_links["url"] == link, "scanned"] = 1  # Flag that link has been scrapped successfully
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

        df_new = pd.DataFrame(bookings)
        df_existing = pd.concat([df_existing, df_new], ignore_index=True)
        logger.info(f"Scraping complete for link: {link}")
        return df_existing, df_links


    async def collect_and_scrape(self):
        logger.info("Starting collect_and_scrape process.")
        await self.collect_links()

        links_path = "data/links.csv"
        df_links = pd.read_csv(links_path)

        # Filter out unscrapable and passed sessions
        links_to_scan = df_links[df_links["state"].isin([-1, 1])]["url"].tolist()

        if not links_to_scan:
            logger.info("No unscanned links to scrape.")
            return

        df_path = "data/all_bookings.csv"
        df_existing = pd.read_csv(df_path) if os.path.exists(df_path) else pd.DataFrame(columns=["date", "room", "time_slot", "name", "admin_num"])
        df_existing["date"] = pd.to_datetime(df_existing["date"]).dt.date

        for url in links_to_scan:
            df_existing, df_links = await self.scrape_link(url, df_existing, df_links)

        # Update CSVs
        try:
            df_links.to_csv(df_path, index=False)
            df_existing.to_csv(links_path, index=False)
            logger.info("Scraped data saved successfully.")
        except Exception as e:
            logger.error(f"Failed to save scraped data CSV files: {e}", exc_info=True)


async def setup(bot: commands.bot):
    await bot.add_cog(BackgroundTasks(bot))