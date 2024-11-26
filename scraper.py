import logging
import gc
import psutil
import time
import random
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import urllib.parse
import traceback
from tqdm import tqdm
from retrying import retry
import signal
import sys
import os
import subprocess
import threading

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

base_url = 'https://www.mastersportal.com/search/master/united-states?page='

# Set the runtime limit (in seconds)
if len(sys.argv) > 1:
    runtime_limit = int(sys.argv[1])
else:
    runtime_limit = 60000  # Default to 100 minutes if no argument is provided

start_time = time.time()

progress_lock = threading.Lock()

def create_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--blink-settings=imagesEnabled=false')  # Disable images
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-features=VizDisplayCompositor')  # Disable compositor
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    options.add_argument('--window-size=1280x1024')  # Set a standard window size

    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

@retry(stop_max_attempt_number=3, wait_random_min=1000, wait_random_max=2000)
def get_html_with_retry(url):
    driver = create_driver()
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        time.sleep(random.uniform(2, 4))  # Increased delay
        html = driver.page_source
        if "No results found" in html:
            logging.warning(f"No results found on page: {url}")
        if "<title>Error" in html:
            logging.error(f"Error page encountered at {url}")
            return None
        return html
    except Exception as e:
        logging.error(f"Error retrieving {url}: {e}")
        return None
    finally:
        driver.quit()
        gc.collect()

def parse_programs(html):
    if html is None:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    programs = []

    study_names = soup.find_all('h2', class_='StudyName')
    organisation_names = soup.find_all('strong', class_='OrganisationName')

    if not study_names or not organisation_names:
        logging.warning("No listings found. Verify the HTML structure and class names.")
        return programs

    for study, organisation in zip(study_names, organisation_names):
        title = study.text.strip()
        university = organisation.text.strip()
        link = study.find_parent('a')['href']
        programs.append({'Title': title, 'University': university, 'Link': link})

    gc.collect()  # Manually trigger garbage collection
    return programs

def get_additional_info(program):
    driver = create_driver()

    try:
        driver.get(program['Link'])
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        time.sleep(random.uniform(0.5, 2))  # Random delay between 0.5 and 2 seconds
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        about_section = soup.find('h2', string='About')
        about_text = about_section.find_next('p').text.strip() if about_section else ''

        degree_tags = [tag.text.strip() for tag in soup.find_all('span', class_='Tag js-tag')]

        fee_element = soup.find('div', class_='TuitionFeeContainer')
        tuition_fee = fee_element.find('span', class_='Title').text.strip() if fee_element else ''

        link_element = soup.find('a', class_='StudyLink TextLink TrackingExternalLink ProgrammeWebsiteLink')
        program_website_link = urllib.parse.unquote(link_element['href'].split('target=')[1].split('&')[0]) if link_element else ''

        duration_element = soup.find('span', class_='js-duration')
        duration = duration_element.text.strip() if duration_element else ''

        ranking_element = soup.find('span', class_='Value')
        ranking = ranking_element.text.strip() if ranking_element else ''

        location_element = soup.find('span', class_='Location')
        location = location_element.text.strip() if location_element else ''

        program_type_element = soup.find('div', class_='FactItemInformation FactListTitle js-durationFact')
        program_type = program_type_element.text.strip() if program_type_element else ''

        start_dates = []
        startdate_container = soup.find('div', id='js-StartdateContainer')
        if startdate_container:
            startdate_items = startdate_container.find_all('li', class_='StartDateItem')
            for item in startdate_items:
                start_date_element = item.find('div', class_='FactItemInformation StartDateItemTime js-deadlineFact')
                if start_date_element:
                    start_date = start_date_element.text.strip()
                    deadline_list = item.find_all('li', class_='ApplicationDeadline')
                    deadlines_list = [deadline.find('div', class_='FactItemInformation Deadline').text.strip() for deadline in deadline_list if deadline.find('div', class_='FactItemInformation Deadline')]
                    start_dates.append({'Start Date': start_date, 'Deadlines': deadlines_list})

        program_structure = []
        structure_section = soup.find('h2', string='Programme Structure')
        if structure_section:
            courses = structure_section.find_next('ul').find_all('li') if structure_section.find_next('ul') else []
            program_structure = [course.text.strip() for course in courses]

        gpa_container = soup.find('div', class_='CardContents GPACard js-CardGPA')
        gpa_element = gpa_container.find('div', class_='Score').find('span') if gpa_container else None
        gpa = gpa_element.text.strip() if gpa_element else ''

        ielts_container = soup.find('div', class_='CardContents EnglishCardContents IELTSCard js-CardIELTS')
        ielts_element = ielts_container.find('div', class_='Score').find('span') if ielts_container else None
        ielts = ielts_element.text.strip() if ielts_element else ''

        toefl_container = soup.find('div', class_='CardContents EnglishCardContents TOEFLCard js-CardTOEFL')
        toefl_element = toefl_container.find('div', class_='Score').find('span') if toefl_container else None
        toefl = toefl_element.text.strip() if toefl_element else ''

        other_requirements_section = soup.find('article', id='OtherRequirements')
        other_requirements = [req.text.strip() for req in other_requirements_section.find_all('li')] if other_requirements_section else []

        cost_of_living_section = soup.find('section', id='CostOfLivingContainer')
        if cost_of_living_section:
            amount_elements = cost_of_living_section.find_all('span', class_='Amount')
            if len(amount_elements) >= 2:
                low_amount = amount_elements[0].text.strip()
                high_amount = amount_elements[1].text.strip()
                cost_of_living = f"{low_amount} - {high_amount} USD/month"
            else:
                cost_of_living = ''
        else:
            cost_of_living = ''

        discipline_section = soup.find('article', class_='FactItem Disciplines')
        disciplines = [disc.text.strip() for disc in discipline_section.find_all('a', class_='TextOnly')] if discipline_section else []

        program.update({
            'About': about_text,
            'Degree Tags': degree_tags,
            'Tuition Fee': tuition_fee,
            'Program Website': program_website_link,
            'Duration': duration,
            'Ranking': ranking,
            'Location': location,
            'Program Type': program_type,
            'Start Dates and Deadlines': start_dates,
            'Program Structure': program_structure,
            'GPA': gpa,
            'IELTS': ielts,
            'TOEFL': toefl,
            'Other Requirements': other_requirements,
            'Cost of Living': cost_of_living,
            'Disciplines': disciplines
        })
        logging.info(f"Processed program: {program['Title']}")
    except Exception as e:
        logging.error(f"Exception occurred while processing program {program['Title']}: {traceback.format_exc()}")
    finally:
        driver.quit()
        gc.collect()  # Manually trigger garbage collection
    
    return program

def monitor_cpu_usage():
    high_usage_start = None
    while True:
        cpu_usage = psutil.cpu_percent(interval=1)
        if cpu_usage >= 99:
            if high_usage_start is None:
                high_usage_start = time.time()
            elif time.time() - high_usage_start >= 15:
                logging.warning("CPU usage has been at 100% for 15 seconds. Triggering restart...")
                save_progress(all_programs, current_page, scraped_count)
                # Create a flag file to indicate a restart is in progress
                with open('restart_flag.txt', 'w') as f:
                    f.write('restarting')
                # Execute the batch file to restart in a new command prompt
                subprocess.Popen(['restart_scraper.bat'], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
                # Exit the current Python process
                sys.exit(0)
        else:
            high_usage_start = None
        time.sleep(1)

def check_cpu_usage():
    cpu_usage = psutil.cpu_percent(interval=1)
    logging.debug(f"CPU usage check: {cpu_usage}%")
    if cpu_usage > 99:  # Set a threshold for CPU usage
        logging.warning("CPU usage is high. Pausing for a while...")
        time.sleep(6)  # Pause for 6 seconds to allow CPU usage to drop

def save_progress(all_programs, current_page, scraped_count):
    with progress_lock:
        logging.info(f"Saving progress at page {current_page}, scraped count {scraped_count}")
        try:
            pd.DataFrame(all_programs).to_csv('master_programs_progress.csv', index=False)
            with open('scraper_state.json', 'w') as f:
                json.dump({'current_page': current_page, 'scraped_count': scraped_count}, f)
            logging.info(f"Progress saved. Current page: {current_page}, Programs scraped: {scraped_count}")
        except Exception as e:
            logging.error(f"Error saving progress: {e}")

def load_progress():
    try:
        with progress_lock:
            logging.info("Loading progress")
            df = pd.read_csv('master_programs_progress.csv')
            with open('scraper_state.json', 'r') as f:
                state = json.load(f)
            # Validate state
            if 'current_page' not in state or 'scraped_count' not in state:
                raise ValueError("Invalid state in scraper_state.json")
            logging.info(f"Progress loaded. Current page: {state['current_page']}, Programs scraped: {state['scraped_count']}")
        return df.to_dict('records'), state['current_page'], state['scraped_count']
    except (FileNotFoundError, ValueError) as e:
        logging.error(f"Error loading progress: {e}")
        return [], 1, 0

def scrape_programs(base_url, num_pages=1980, limit=40000):
    global all_programs, current_page, scraped_count
    all_programs, current_page, scraped_count = load_progress()

    with tqdm(total=limit, initial=scraped_count, desc="Scraping Progress") as pbar:
        with ThreadPoolExecutor(max_workers=25) as executor:
            while current_page <= num_pages and scraped_count < limit:
                if time.time() - start_time > runtime_limit:
                    logging.info(f"Runtime limit of {runtime_limit} seconds reached. Saving progress and exiting.")
                    save_progress(all_programs, current_page, scraped_count)
                    return all_programs

                future = executor.submit(get_html_with_retry, f"{base_url}{current_page}")
                
                try:
                    html = future.result()
                    if html:
                        programs = parse_programs(html)
                        new_programs = [p for p in programs if not any(existing_p['Link'] == p['Link'] for existing_p in all_programs)]
                        
                        with ThreadPoolExecutor(max_workers=25) as inner_executor:
                            inner_futures = {inner_executor.submit(get_additional_info, program): program for program in new_programs}
                            for inner_future in as_completed(inner_futures):
                                program = inner_futures[inner_future]
                                try:
                                    detailed_program = inner_future.result()
                                    all_programs.append(detailed_program)
                                    scraped_count += 1
                                    pbar.update(1)
                                    
                                    if scraped_count % 20 == 0:
                                        save_progress(all_programs, current_page, scraped_count)
                                    
                                    if scraped_count >= limit:
                                        break
                                except Exception as e:
                                    logging.error(f"Exception occurred while processing additional info for program {program['Title']}: {traceback.format_exc()}")
                    else:
                        logging.error(f"Failed to retrieve or parse page {current_page}")
                
                except Exception as e:
                    logging.error(f"Exception occurred while processing page {current_page}: {traceback.format_exc()}")
                
                current_page += 1
                gc.collect()
                time.sleep(5)
                check_cpu_usage()
                if scraped_count >= limit:
                    break
        
    save_progress(all_programs, current_page, scraped_count)
    return all_programs

def signal_handler(signum, frame):
    logging.info("Received interrupt signal. Saving progress and exiting...")
    save_progress(all_programs, current_page, scraped_count)
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def main():
    if os.path.exists('restart_flag.txt'):
        os.remove('restart_flag.txt')
        time.sleep(5)  # Wait a bit to ensure the old instance has closed

    global all_programs, current_page, scraped_count
    
    #cpu_monitor_thread = threading.Thread(target=monitor_cpu_usage, daemon=True)
    #cpu_monitor_thread.start()
    
    try:
        programs = scrape_programs(base_url, num_pages=1980, limit=40000)

        if programs:
            df = pd.DataFrame(programs)
            df.to_csv('master_programs_final.csv', index=False)
            gc.collect()
            logging.info(f"Data saved to master_programs_final.csv. Total programs scraped: {len(programs)}")
        else:
            logging.info("No programs scraped. Verify the scraping logic.")
    finally:
        stop_event.set()
        #cpu_monitor_thread.join(timeout=5)
        logging.info("CPU monitoring thread stopped.")
        gc.collect()

if __name__ == "__main__":
    main()
    gc.collect()
