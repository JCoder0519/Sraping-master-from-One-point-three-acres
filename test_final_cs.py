from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import os
import traceback
import random
import uuid

def generate_unique_id():
    return str(uuid.uuid4())

def random_delay(min_seconds=2, max_seconds=5):
    time.sleep(random.uniform(min_seconds, max_seconds))

def save_to_json(data, filename='program_data.json'):
    if os.path.exists(filename):
        with open(filename, 'r+', encoding='utf-8') as file:
            file_data = json.load(file)
            file_data.append(data)
            file.seek(0)
            json.dump(file_data, file, ensure_ascii=False, indent=4)
    else:
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump([data], file, ensure_ascii=False, indent=4)
    print(f"Data saved to {filename}")

def setup_driver():
    chrome_options = Options()
    user_data_dir = os.path.expanduser('~') + r'\AppData\Local\Google\Chrome\User Data'
    chrome_options.add_argument(f"user-data-dir={user_data_dir}")
    chrome_options.add_argument("profile-directory=Default")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def check_login(driver):
    try:
        login_url = "https://auth.1point3acres.com/login?url=https://offer.1point3acres.com/?from=discuz"
        driver.get(login_url)
        
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        if 'offer.1point3acres.com' in driver.current_url:
            print("Already logged in.")
            print("Waiting to ensure everything is loaded...")
            random_delay(8, 12)
            return True
        else:
            print("Not logged in. Please log in manually.")
            input("Press Enter after you've successfully logged in...")
            driver.refresh()
            WebDriverWait(driver, 10).until(EC.url_contains("offer.1point3acres.com"))
            
            if 'offer.1point3acres.com' in driver.current_url:
                print("Login successful.")
                print("Waiting to ensure everything is loaded...")
                random_delay(8, 12)
                return True
            else:
                print("Login failed. Please try again.")
                return False
    except Exception as e:
        print(f"An error occurred during login check: {e}")
        print(traceback.format_exc())
        return False

def save_program_data_json(program_info, filename='program_data.json'):
    try:
        if os.path.exists(filename):
            with open(filename, 'r+', encoding='utf-8') as file:
                data = json.load(file)
                data.append(program_info)
                file.seek(0)
                json.dump(data, file, ensure_ascii=False, indent=2)
                file.truncate()
        else:
            with open(filename, 'w', encoding='utf-8') as file:
                json.dump([program_info], file, ensure_ascii=False, indent=2)
        print(f"Saved program data to {filename}")
    except Exception as e:
        print(f"Error saving program data to JSON: {e}")

def extract_favorite_program_info(driver, program):
    try:
        program_info = {}
        program_id = generate_unique_id()
        program_info['Program ID'] = program_id

        # Extract basic program information
        program_name_element = WebDriverWait(program, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".text-lg.font-bold a"))
        )
        program_info['Program Name'] = program_name_element.text.strip()
        program_url = program_name_element.get_attribute("href")

        # University and Department
        try:
            university_element = program.find_element(By.CSS_SELECTOR, "div.md\\:ml-5.flex-1 > div:nth-child(2)")
            university_text = university_element.text.strip()
            program_info['University'] = university_text.split('@')[-1].strip()
            program_info['Department'] = university_text.split('@')[0].strip()
        except NoSuchElementException:
            program_info['University'] = "N/A"
            program_info['Department'] = "N/A"

        # Tags
        program_info['Tags'] = [tag.text.strip() for tag in program.find_elements(By.CSS_SELECTOR, ".ant-tag")]

        # Statistics
        stats = program.find_elements(By.CSS_SELECTOR, '.flex.flex-col.text-center')
        if len(stats) >= 5:
            program_info['Admissions'] = stats[0].find_element(By.CSS_SELECTOR, "div").text.strip()
            program_info['Applicants'] = stats[1].find_element(By.CSS_SELECTOR, "div").text.strip()
            program_info['Median GPA'] = stats[2].find_element(By.CSS_SELECTOR, "div").text.strip()
            program_info['TOEFL'] = stats[3].find_element(By.CSS_SELECTOR, "div").text.strip()
            program_info['GRE'] = stats[4].find_element(By.CSS_SELECTOR, "div").text.strip()

            # Check number of applicants and skip if 3 or fewer
            try:
                applicants = int(program_info['Applicants'])
                if applicants <= 3:
                    print(f"Skipping program {program_info['Program Name']} due to low number of applicants: {applicants}")
                    return None
            except ValueError:
                print(f"Could not parse number of applicants for {program_info['Program Name']}: {program_info['Applicants']}")

        # Navigate to the program's detailed page
        if program_url:
            random_delay()
            driver.execute_script("window.open('');")
            driver.switch_to.window(driver.window_handles[-1])
            driver.get(program_url)
            random_delay(5, 8)

            # Extract additional information from the detailed page
            try:
                program_info['US News Ranking'] = driver.find_element(By.CSS_SELECTOR, ".text-\\#5BAE93.bg-\\#D3F4EA.rounded-lg.text-xs.px-2.py-px.font-medium").text.strip()
            except NoSuchElementException:
                program_info['US News Ranking'] = "N/A"

            try:
                program_info['Cost of Living'] = driver.find_element(By.CSS_SELECTOR, ".text-\\#4E4E4E.font-bold.text-xs.lg\\:text-sm.mr-3 + div").text.strip()
            except NoSuchElementException:
                program_info['Cost of Living'] = "N/A"

            try:
                program_info['General Ranking'] = [
                    {
                        "Ranking Source": rank.find_element(By.CSS_SELECTOR, "div:nth-child(2)").text.strip(),
                        "Ranking Description": rank.find_element(By.CSS_SELECTOR, "div:nth-child(3)").text.strip(),
                        "Ranking Value": rank.find_element(By.CSS_SELECTOR, "div:nth-child(1)").text.strip()
                    }
                    for rank in driver.find_elements(By.CSS_SELECTOR, "#rank .flex.space-x-4.items-center")
                ]
            except NoSuchElementException:
                program_info['General Ranking'] = []

            try:
                program_info['Admissions Statistics'] = [stat.text.strip() for stat in driver.find_elements(By.CSS_SELECTOR, ".flex.mt-1.space-x-7 div")]
            except NoSuchElementException:
                program_info['Admissions Statistics'] = []

            # Scrape admission reports directly from the program detail page
            try:
                program_info['admission_reports'] = []
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".ant-table-tbody"))
                )

                report_table = driver.find_element(By.CSS_SELECTOR, ".ant-table-tbody")
                print("Report Table HTML:\n", report_table.get_attribute('outerHTML'))

                report_rows = report_table.find_elements(By.CSS_SELECTOR, "tr")
                print(f"Found {len(report_rows)} rows in the report table")

                for row in report_rows:  # Process all rows
                    report = {}
                    columns = row.find_elements(By.CSS_SELECTOR, "td")

                    # Log the number of columns found and print the HTML of the row
                    print(f"Number of columns found: {len(columns)}")
                    print(f"Row HTML: {row.get_attribute('outerHTML')}")

                    # Ensure there are enough columns before accessing them
                    if len(columns) >= 7:
                        report['报告时间'] = columns[0].text
                        report['学位/专业'] = columns[1].text
                        report['项目'] = columns[2].text
                        report['标题'] = columns[3].text
                        report['学期'] = columns[4].text
                        report['录取结果'] = columns[5].text

                        # Ensure the link is clickable and click it using JavaScript
                        detail_link = columns[-1].find_element(By.CSS_SELECTOR, "a")
                        driver.execute_script("arguments[0].click();", detail_link)
                        print("Clicked '详情' link")

                        # Wait for the modal to appear
                        modal = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".ant-modal-content"))
                        )

                        time.sleep(1)  # Wait for the modal content to be fully loaded
                        # Extract modal content
                        descriptions = modal.find_elements(By.CSS_SELECTOR, ".ant-descriptions-item-label, .ant-descriptions-item-content")
                        for i in range(0, len(descriptions), 2):
                            key = descriptions[i].text.strip()
                            value = descriptions[i+1].text.strip()
                            if key and value:  # Only add non-empty keys and values
                                report[key] = value

                        time.sleep(1)  # Wait for the modal content to be fully loaded
                        program_info['admission_reports'].append(report)
                        print(report)
                        print(f"Added report to program_info: {report['报告时间']}")
                        time.sleep(2)  # Wait for the modal content to be fully loaded
                        
                        # Close the modal by clicking outside of it
                        actions = ActionChains(driver)
                        actions.move_by_offset(0, 0).click().perform()
                        print("Clicked outside the modal to close it")

                        # Wait for the modal to disappear
                        WebDriverWait(driver, 10).until(
                            EC.invisibility_of_element_located((By.CSS_SELECTOR, ".ant-modal-content"))
                        )
                        print("Modal closed successfully")

                        time.sleep(1)  # Short pause after closing modal
                    else:
                        print(f"Skipping incomplete report row with {len(columns)} columns: {row.text}")

            except Exception as e:
                print(f"Error scraping admission reports: {e}")

            # Close the program details window and switch back to the main window
            driver.close()
            driver.switch_to.window(driver.window_handles[0])

        # Save the scraped data to JSON
        save_to_json(program_info)

        return program_info
    except Exception as e:
        print(f"An error occurred while extracting program info: {e}")
        return {}

def scrape_favorite_programs(driver, base_url):
    try:
        driver.get(base_url)
        print("Waiting for the page to load completely...")
        random_delay(30, 40)

        page_number = 1

        while True:
            retry_count = 0
            while retry_count < 3:
                try:
                    WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.bg-\#E7EDEA\\/30.text-\#5E5E5E.rounded-md')))
                    programs = driver.find_elements(By.CSS_SELECTOR, '.bg-\#E7EDEA\\/30.text-\#5E5E5E.rounded-md')
                    
                    for program in programs:
                        program_info = extract_favorite_program_info(driver, program)
                        if program_info:
                            save_program_data_json(program_info)
                            print(f"Scraped and saved program: {program_info.get('Program Name', 'Unknown')}")
                        random_delay(3, 6)

                    print(f"Scraped page {page_number} - Total programs on this page: {len(programs)}")
                    break
                except (TimeoutException, StaleElementReferenceException) as e:
                    print(f"Error on page {page_number}, retry {retry_count + 1}: {e}")
                    retry_count += 1
                    if retry_count == 3:
                        print(f"Failed to scrape page {page_number} after 3 attempts. Moving to next page.")
                    random_delay(3, 5)
            
            # Check if there's a next page
            next_button = driver.find_elements(By.CSS_SELECTOR, '.ant-pagination-next:not(.ant-pagination-disabled)')
            if next_button:
                random_delay()
                next_button[0].click()
                print("Waiting for the next page to load...")
                random_delay(8, 12)
                page_number += 1
            else:
                print("No more pages to scrape.")
                break

    except Exception as e:
        print(f"An error occurred during scraping: {e}")
        print(traceback.format_exc())

def main():
    driver = setup_driver()
    
    try:
        if check_login(driver):
            favorites_url = "https://offer.1point3acres.com/my/favorites"
            scrape_favorite_programs(driver, favorites_url)
            
            if os.path.exists('program_data.json'):
                with open('program_data.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"Scraped data for {len(data)} programs. Data saved to program_data.json")
            else:
                print("No data was scraped.")
        else:
            print("Could not proceed with scraping due to login failure.")
    except Exception as e:
        print(f"An error occurred in the main function: {e}")
        print(traceback.format_exc())
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
