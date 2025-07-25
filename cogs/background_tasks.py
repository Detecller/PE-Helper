import discord
from discord.ext import commands, tasks
from utils.variables import SGT, last_update
import pandas as pd
from datetime import datetime, timezone
from datetime import timedelta
import re
import os
import csv
import asyncio
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
import functools
import time
import utils.audio_essentials as audio_essentials
from utils.channel_last_message_id_tracker import *
import cogs.music_bot as music_bot
from utils.variables import currently_playing, audio
import traceback


GUILD_ID = int(os.getenv("GUILD_ID"))
NEW_MESSAGES_PARQUET = "../data/new_messages.parquet"
ALL_MESSAGES_PARQUET = "../data/all_messages.parquet"

# Get logger
logger = logging.getLogger("pe_helper")


class BackgroundTasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.collect_links_task = None


    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("Starting background tasks.")
        logger.info("Running count_messages once on startup.", extra={"category": "on_ready"})
        await self.count_messages()
        
        if self.collect_links_task is None:
            logger.info("Starting collect_links_time loop.", extra={"category": "on_ready"})
            self.collect_links_task = self.bot.loop.create_task(self.collect_links_time())
        else:
            logger.info("collect_links_time loop already running.", extra={"category": "on_ready"})


    async def collect_links_time(self):
        try:
            logger.info("Starting initial collect_and_scrape on startup.")
            await self.collect_and_scrape()
        except Exception:
            logger.error("Error during collect_and_scrape", exc_info=True, extra={"category": ["background_tasks", "collect_and_scrape"]})

        try:
            logger.info("Starting initial count_messages on startup.")
            await self.count_messages()
        except Exception:
            logger.error("Error during count_messages", exc_info=True, extra={"category": ["background_tasks", "count_messages"]})

        try:
            logger.info("Starting initial collect_new_messages on startup.")
            await self.collect_new_messages()
        except Exception:
            logger.error("Error during collect_new_messages", exc_info=True, extra={"category": ["background_tasks", "collect_new_messages"]})

        try:
            logger.info("Starting initial count_piano_groups on startup.")
            await self.count_piano_groups()
        except Exception:
            logger.error("Error during count_piano_groups", exc_info=True, extra={"category": ["background_tasks", "count_piano_groups"]})

        try:
            logger.info("Starting initial get_summary_numbers on startup.")
            await self.get_summary_numbers()
        except Exception:
            logger.error("Error during get_summary_numbers", exc_info=True, extra={"category": ["background_tasks", "get_summary_numbers"]})

        while True:
            now = datetime.now(SGT).astimezone()

            # Set target to today at 5 PM
            target_time = now.replace(hour=17, minute=0, second=0, microsecond=0)


            # If it's already past 5 PM, schedule for 5 PM tomorrow
            if now >= target_time:
                target_time += timedelta(days=1)

            wait_seconds = (target_time - now).total_seconds()
            logger.info(f"collect_links_time sleeping for {wait_seconds:.2f} seconds until next 5 PM SGT.", extra={"category": ["background_tasks", "collect_links_time"]})
            await asyncio.sleep(wait_seconds)
            try:
                await self.collect_and_scrape()
                await self.count_messages()
                await self.collect_new_messages()
            except Exception as e:
                logger.error(f"Error during scheduled collect_and_scrape: %s\n%s", e, traceback.format_exc(), extra={"category": ["background_tasks", "collect_and_scrape"]})


    async def count_piano_groups(self):
        logger.info("Starting count_piano_groups task.")

        guild = self.bot.get_guild(GUILD_ID)

        count_dict = {"Advanced": 0, "Intermediate": 0, "Novice": 0, "Foundational": 0}

        for m in guild.members:
            if m.bot:
                continue
            roles = {r.name for r in m.roles}
            if "Member" in roles:  # Obtain current members only
                if "Advanced" in roles:
                    count_dict["Advanced"] += 1
                elif "Intermediate" in roles:
                    count_dict["Intermediate"] += 1
                elif "Novice" in roles:
                    count_dict["Novice"] += 1
                elif "Foundational" in roles:
                    count_dict["Foundational"] += 1

        logger.info(f"Counting of members in piano groups was successful.", extra={"category": ["background_tasks", "count_piano_groups"]})
        df_piano_groups = pd.DataFrame([count_dict])
        df_piano_groups.to_csv("../data/piano_groups.csv", index=False)
    

    async def get_summary_numbers(self):
        logger.info("Starting get_summary_numbers task.")
        
        guild = self.bot.get_guild(GUILD_ID)
        summary_dict = {}
        for m in guild.members:
            if m.bot:
                continue

            roles = {r.name for r in m.roles}
            join_date = m.joined_at

            # Determine AY: April 1st to March 31st
            if join_date.month >= 4:
                ay_year = join_date.year
            else:
                ay_year = join_date.year - 1
            ay_key = f"{ay_year}"

            if ay_key not in summary_dict:
                summary_dict[ay_key] = {"members_num": 0, "alumni_num": 0, "new_members_num": 0}

            # Role counts
            if "Member" in roles:
                summary_dict[ay_key]["members_num"] += 1
            elif "Alumni" in roles:
                summary_dict[ay_key]["alumni_num"] += 1

            # New member check: if joined during AY
            ay_start = datetime(ay_year, 4, 1, tzinfo=timezone.utc)
            ay_end = datetime(ay_year + 1, 4, 1, tzinfo=timezone.utc)
            if ay_start <= join_date < ay_end:
                summary_dict[ay_key]["new_members_num"] += 1

        summary_numbers = [
            {"AY": ay, **counts} for ay, counts in summary_dict.items()
        ]

        df = pd.DataFrame(summary_numbers)
        df = df.sort_values("AY")
        df.to_csv("../data/summary_numbers.csv", index=False)


    async def count_messages(self):
        logger.info("Starting count_messages task.")

        guild = self.bot.get_guild(GUILD_ID)
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
                logger.warning(f"Forbidden access to channel: {ch.name}, skipping.", extra={"category": ["background_tasks", "count_messages"]})
                continue
            except Exception as e:
                logger.error(f"Error reading messages from channel {ch.name}: %s\n%s", e, traceback.format_exc(), extra={"category": ["background_tasks", "count_messages"]})
                continue
            scanned.append(ch.name)

        try:
            df = pd.DataFrame([
                {"Name": n, "Message Count": message_counts[n], "Word Count": word_counts[n]}
                for n in message_counts
            ])
            
            df.sort_values("Message Count", ascending=False).head(10).drop('Word Count', axis=1).to_csv("../data/top_messages.csv", index=False)
            df.sort_values("Word Count", ascending=False).head(10).drop('Message Count', axis=1).to_csv("../data/top_words.csv", index=False)
            with open("../data/channels.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(scanned))

            global last_update
            last_update = datetime.now(SGT)
            logger.info("count_messages task completed and CSV files updated.", extra={"category": ["background_tasks", "count_messages"]})
        except Exception as e:
            logger.error(f"Error saving message stats CSV files: %s\n%s", e, traceback.format_exc(), extra={"category": ["background_tasks", "count_messages"]})


    async def collect_new_messages(self):
        logger.info("Starting collect_new_messages task.")

        guild = self.bot.get_guild(GUILD_ID)

        try:
            data = []
            last_seen_ids = load_last_seen_ids()

            for channel in guild.text_channels:
                blacklisted_category = 'Commands'
                if channel.category and channel.category.name == blacklisted_category:
                    logger.info(f"Skipping channel '{channel.name}' in excluded category '{blacklisted_category}'", extra={"category": ["background_tasks", "collect_new_messages"]})
                    continue

                logger.info(f"Processing channel: {channel.name} (ID: {channel.id})", extra={"category": ["background_tasks", "collect_new_messages"]})
                last_seen_id = last_seen_ids.get(str(channel.id))
                
                if last_seen_id is None:
                    logger.info("No last seen ID found, fetching full history...", extra={"category": ["background_tasks", "collect_new_messages"]})
                    history = channel.history(limit=None)
                else:
                    logger.info(f"Fetching messages after ID: {last_seen_id}", extra={"category": ["background_tasks", "collect_new_messages"]})
                    history = channel.history(limit=None, after=discord.Object(id=last_seen_id))
                    
                latest_id = last_seen_id or 0
                channel_name = channel.name
                message_count = 0

                async for message in history:
                    message_count += 1
                    name = message.author.display_name
                    created_at = message.created_at
                    content = message.content

                    for user in message.mentions:
                        content = content.replace(f"<@{user.id}>", f"@{user.display_name}")
                        content = content.replace(f"<@!{user.id}>", f"@{user.display_name}")

                    for role in message.role_mentions:
                        content = content.replace(f"<@&{role.id}>", f"@{role.name}")

                    for mentioned_channel in message.channel_mentions:
                        content = content.replace(f"<#{mentioned_channel.id}>", f"#{mentioned_channel.name}")

                    if message.mention_everyone:
                        content = content.replace("@everyone", "@everyone")
                        content = content.replace("@here", "@here")

                    data.append({
                        "message_id": message.id,
                        "author": name,
                        "channel": channel_name,
                        "timestamp": created_at,
                        "content": content
                    })

                    if message.id > latest_id:
                        latest_id = message.id
                
                logger.info(f"Collected {message_count} messages from channel '{channel_name}'", extra={"category": ["background_tasks", "collect_new_messages"]})
                last_seen_ids[str(channel.id)] = latest_id

            save_last_seen_ids(last_seen_ids)
            logger.info("Saved last seen message IDs.")

            if data:
                df = pd.DataFrame(data)
                df.to_parquet(NEW_MESSAGES_PARQUET, index=False)
                logger.info(f"Saved {len(data)} new messages to {NEW_MESSAGES_PARQUET}", extra={"category": ["background_tasks", "collect_new_messages"]})

            if os.path.exists(ALL_MESSAGES_PARQUET):
                old_df = pd.read_parquet(ALL_MESSAGES_PARQUET)
                new_df = pd.read_parquet(NEW_MESSAGES_PARQUET)
                combined = pd.concat([old_df, new_df]).drop_duplicates(subset="message_id")
            else:
                combined = pd.read_parquet(NEW_MESSAGES_PARQUET)

            combined.to_parquet(ALL_MESSAGES_PARQUET, index=False)
            logger.info("Updated combined messages saved to all_messages.parquet", extra={"category": ["background_tasks", "collect_new_messages"]})
            
            os.remove(NEW_MESSAGES_PARQUET)
            logger.info("Temporary file new_messages.parquet removed.", extra={"category": ["background_tasks", "collect_new_messages"]})
        
        except Exception as e:
            logger.error(f"Error in collect_new_messages: %s\n%s", e, traceback.format_exc(), extra={"category": ["background_tasks", "collect_new_messages"]})


    async def collect_links(self):
        guild = self.bot.get_guild(GUILD_ID)
        target_channel = discord.utils.get(guild.text_channels, name="🎹┃weekly-sessions")

        # Check if weekly session channel exists
        if not target_channel:
            logger.error("Channel not found.")
            return

        url_pattern = r'https?://\S+'
        csv_path = "../data/links.csv"

        # Load existing URLs
        existing_urls = set()
        if os.path.exists(csv_path):
            try:
                with open(csv_path, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    existing_urls = {row["url"] for row in reader}
                logger.info(f"Loaded {len(existing_urls)} existing URLs from links.csv.", extra={"category": ["background_tasks", "collect_links"]})
            except Exception as e:
                logger.error(f"Error reading links.csv: %s\n%s", e, traceback.format_exc(), extra={"category": ["background_tasks", "collect_links"]})

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
            logger.error(f"Error scanning messages in channel '{target_channel.name}': %s\n%s", e, traceback.format_exc(), extra={"category": ["background_tasks", "collect_links"]})


        if new_links:
            try:
                file_exists = os.path.exists(csv_path)
                with open(csv_path, mode="a", encoding="utf-8", newline="") as f:
                    fieldnames = ["url", "scanned", "state"]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)

                    if not file_exists:
                        writer.writeheader()
                    writer.writerows(new_links)

                logger.info(f"Added {len(new_links)} new links to links.csv.", extra={"category": ["background_tasks", "collect_links"]})
            except Exception as e:
                logger.error(f"Error writing to links.csv: %s\n%s", e, traceback.format_exc(), extra={"category": ["background_tasks", "collect_links"]})
        else:
            logger.info("No new links found to add.", extra={"category": ["background_tasks", "collect_links"]})


    async def scrape_link(self, driver, link: str, df_existing: pd.DataFrame, df_links: pd.DataFrame):
        loop = asyncio.get_running_loop()
        partial_func = functools.partial(self.scrape_link_sync, driver, link, df_existing, df_links)
        return await loop.run_in_executor(None, partial_func)


    # Function to scrape details from SignUpGenius
    def scrape_link_sync(self, driver, link: str, df_existing: pd.DataFrame, df_links: pd.DataFrame):
        logger.info(f"Scraping link: {link}", extra={"category": ["background_tasks", "collect_links"]})

        # Navigate to the page
        driver.get(link)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "signupcontainer"))
        )
        
        scrapable = True
        try:
            # Extract information
            date = driver.find_element(By.XPATH, f'//*[@id="signupcontainer"]/div[1]/div[2]/div[2]/div[2]/div/div[2]').text
            date = re.sub(r"\s*\([^)]*\)", "", date).strip() # Remove day
            date = datetime.strptime(date, "%m/%d/%Y").date()
            
            today = datetime.now(SGT).date()

            if today > date and df_links.loc[df_links["url"] == link, "scanned"].values[0] == 1:
                logger.info(f"Session date passed and already scanned for link: {link}")
                df_links.loc[df_links["url"] == link, "state"] = 2  # Indicate weekly session has passed
                return df_existing, df_links

            room = driver.find_element(By.XPATH, f'//*[@id="signupcontainer"]/div[1]/div[2]/div[2]/div[4]/div/div[2]/span').text

            # Remove existing records related to this session
            if not df_existing.empty:
                df_existing = df_existing[~((df_existing["date"] == date) & (df_existing["room"] == room))]

        except NoSuchElementException:
            scrapable = False
            logger.warning(f"Scrape failed - necessary elements not found for link: {link}", extra={"category": ["sheet_retriever", "scrape_link_sync"]})
        

        if scrapable == False:
            df_links.loc[df_links["url"] == link, "state"] = 0  # Indicate link is unscrapable
            logger.warning('Link cannot be scrapped.')
            return df_existing, df_links

        bookings = []
        i = 1
        def find_with_fallback(driver, xpath_variants):
            for xpath in xpath_variants:
                try:
                    return driver.find_element(By.XPATH, xpath)
                except NoSuchElementException:
                    continue
            raise NoSuchElementException(f"None of the XPaths matched: {xpath_variants}")
        
        while True:
            try:
                time_slot_xpath_3 = f'//*[@id="signupcontainer"]/div[3]/div/div[3]/div/table/tbody/tr/td[4]/ng-include/table/tbody/tr[{i}]/td/div/div[1]/div[2]/div[1]/div[1]/div[1]/span'
                time_slot_xpath_4 = f'//*[@id="signupcontainer"]/div[3]/div/div[4]/div/table/tbody/tr/td[4]/ng-include/table/tbody/tr[{i}]/td/div/div[1]/div[2]/div[1]/div[1]/div[1]/span'
                time_slot = find_with_fallback(driver, [time_slot_xpath_3, time_slot_xpath_4]).text

                # Clean time slot value
                time_slot = re.sub(r"(\d{2})(\d{2})", r"\1 \2", time_slot)
                time_slot = re.sub(r"\s*-\s*", " - ", time_slot)

                details_found = True
                try:
                    details = '//*[@id="signupcontainer"]/div[3]/div/div[3]/div/table/tbody/tr/td[4]/ng-include/table/tbody/tr/td/div/div[2]/div/participant-summary/div/div[11]/a'
                    details_elem = driver.find_element(By.XPATH, details)
                except NoSuchElementException:
                    details_found = False
                else:
                    details_elem = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, details))
                    )
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", details_elem)
                    time.sleep(0.5)
                    details_elem.click()
                    show_50 = "/html/body/div[13]/div/div/div/div/div[2]/div[5]/div/items-per-page/ul/li[4]"
                    WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, show_50))
                    )
                    show_50_elem = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, show_50))
                    )
                    show_50_elem = driver.find_element(By.XPATH, show_50)
                    show_50_elem.click()

                x = 1
                while True:
                    try:
                        if details_found == False:  # If the details do not exist, use the default scraping method
                            name_xpath_3 = f'//*[@id="signupcontainer"]/div[3]/div/div[3]/div/table/tbody/tr/td[4]/ng-include/table/tbody/tr[{i}]/td/div/div[2]/div/participant-summary/div/div[{x}]/div/p/span'
                            name_xpath_4 = f'//*[@id="signupcontainer"]/div[3]/div/div[4]/div/table/tbody/tr/td[4]/ng-include/table/tbody/tr[{i}]/td/div/div[2]/div/participant-summary/div/div[{x}]/div/p/span'
                            admin_num_xpath_3 = f'//*[@id="signupcontainer"]/div[3]/div/div[3]/div/table/tbody/tr/td[4]/ng-include/table/tbody/tr[{i}]/td/div/div[2]/div/participant-summary/div/div[{x}]/div/div/span[3]/span[1]'
                            admin_num_xpath_4 = f'//*[@id="signupcontainer"]/div[3]/div/div[4]/div/table/tbody/tr/td[4]/ng-include/table/tbody/tr[{i}]/td/div/div[2]/div/participant-summary/div/div[{x}]/div/div/span[3]/span[1]'
                            name = find_with_fallback(driver, [name_xpath_3, name_xpath_4]).text
                            try:
                                admin_num = find_with_fallback(driver, [admin_num_xpath_3, admin_num_xpath_4]).get_attribute("textContent")
                            except NoSuchElementException:
                                admin_num = ""

                        else:  # If the details exist, use it to scrape
                            first_name_xpath = f'/html/body/div[13]/div/div/div/div/div[2]/div[4]/div/table/tbody/tr[{x}]/td[1]'
                            last_name_xpath = f'/html/body/div[13]/div/div/div/div/div[2]/div[4]/div/table/tbody/tr[{x}]/td[2]'
                            admin_num_xpath = f'/html/body/div[13]/div/div/div/div/div[2]/div[4]/div/table/tbody/tr[{x}]/td[4]/span[1]'

                            first_name = driver.find_element(By.XPATH, first_name_xpath).text
                            last_name = driver.find_element(By.XPATH, last_name_xpath).text
                            name = first_name + ' ' + last_name
                            try:
                                admin_num = driver.find_element(By.XPATH, admin_num_xpath).text
                            except NoSuchElementException:
                                admin_num = ""
                    except NoSuchElementException:
                        break

                    df_links.loc[df_links["url"] == link, "scanned"] = 1  # Flag that link has been scrapped successfully
                    df_links.loc[df_links["url"] == link, "state"] = 1  # Indicate weekly session has not passed
                    bookings.append({
                        "date": date,
                        "room": room,
                        "time_slot": time_slot,
                        "name": name,
                        "admin_num": admin_num
                    })
                    x += 1

            except NoSuchElementException:
                break
            i += 1

        df_new = pd.DataFrame(bookings)
        df_existing = pd.concat([df_new, df_existing], ignore_index=True)
        df_existing['admin_num'] = df_existing['admin_num'].str.extract(r'(\b\d{6}[A-Za-z]\b)')[0].str.upper()
        logger.info(f"Scraping complete for link: {link}", extra={"category": ["background_tasks", "scrape_link_sync"]})
        return df_existing, df_links


    async def collect_and_scrape(self):
        logger.info("Starting collect_and_scrape process.", extra={"category": ["background_tasks", "collect_and_scrape"]})
        await self.collect_links()

        links_path = "../data/links.csv"
        df_links = pd.read_csv(links_path)

        # Filter out unscrapable links
        links_to_scan = df_links[df_links["state"] != 0]["url"].tolist()

        if not links_to_scan:
            logger.info("No unscanned links to scrape.", extra={"category": ["background_tasks", "collect_and_scrape"]})
            return

        df_path = "../data/all_bookings.csv"
        df_existing = pd.read_csv(df_path) if os.path.exists(df_path) else pd.DataFrame(columns=["date", "room", "time_slot", "name", "admin_num"])
        df_existing["date"] = pd.to_datetime(df_existing["date"]).dt.date

        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
            driver = webdriver.Chrome(options=chrome_options)
            logger.info('Chrome WebDriver started successfully in headless mode.', extra={"category": ["background_tasks", "collect_and_scrape"]})

            for url in links_to_scan:
                df_existing, df_links = await self.scrape_link(driver, url, df_existing, df_links)
                
        except WebDriverException as e:
            logger.error(f"Failed to start Chrome WebDriver: %s\n%s", e, traceback.format_exc(), extra={"category": ["background_tasks", "collect_and_scrape"]})
            return df_existing, df_links
        
        finally:
            if driver:
                driver.quit()
            

        # Get academic year for each date
        def get_academic_year(date):
            ay_start = datetime(date.year, 4, 1).date()
            if date >= ay_start:
                return date.year
            else:
                return date.year - 1

        df_existing['AY'] = df_existing['date'].apply(get_academic_year)

        # Update CSVs
        try:
            df_existing.to_csv(df_path, index=False)
            df_links.to_csv(links_path, index=False)
            logger.info("Scraped data saved successfully.")
        except Exception as e:
            logger.error(f"Failed to save scraped data CSV files: %s\n%s", e, traceback.format_exc(), extra={"category": ["background_tasks", "collect_and_scrape"]})


    @tasks.loop(seconds=5)
    async def loop_files(self):
        instance = [i for i in music_bot.VoteSkip.instances if i['id'] == currently_playing['id']]
        if instance:
            instance = instance[0]
            VoteInstance = instance['instance']
            if len(VoteInstance.voted_skip) > len(VoteInstance.currently_playing['members']) / 2:
                voice_client = self.bot.get_guild(GUILD_ID).voice_client
                voice_client.stop()
                audio.cleanup()
        audio_essentials.refresh_song()


async def setup(bot: commands.Bot):
    await bot.add_cog(BackgroundTasks(bot))