from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time
from selenium.webdriver.common.action_chains import ActionChains
import json
import os
import traceback
import csv
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

def save_to_csv(program_info, filename='program_data.csv'):
    file_exists = os.path.isfile(filename)
    
    with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Program ID', 'Program Name', 'University', 'Department', 'Tags', 'Admissions', 
                      'Applicants', 'Median GPA', 'TOEFL', 'GRE', 'US News Ranking', 
                      'Cost of Living', 'General Ranking', 'Admissions Statistics']
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        row = {
            'Program ID': program_info.get('Program ID', ''),
            'Program Name': program_info.get('Program Name', ''),
            'University': program_info.get('University', ''),
            'Department': program_info.get('Department', ''),
            'Tags': ', '.join(program_info.get('Tags', [])),
            'Admissions': program_info.get('Admissions', ''),
            'Applicants': program_info.get('Applicants', ''),
            'Median GPA': program_info.get('Median GPA', ''),
            'TOEFL': program_info.get('TOEFL', ''),
            'GRE': program_info.get('GRE', ''),
            'US News Ranking': program_info.get('US News Ranking', ''),
            'Cost of Living': program_info.get('Cost of Living', ''),
            'General Ranking': json.dumps(program_info.get('General Ranking', []), ensure_ascii=False),
            'Admissions Statistics': json.dumps(program_info.get('Admissions Statistics', []), ensure_ascii=False)
        }
        
        writer.writerow(row)
    
    print(f"Data saved to {filename}")

    # Save admission reports to a separate CSV file
    if 'admission_reports' in program_info:
        reports_filename = 'admission_reports.csv'
        reports_file_exists = os.path.isfile(reports_filename)
        
        with open(reports_filename, 'a', newline='', encoding='utf-8') as csvfile:
            all_fieldnames = ['Program ID', 'Program Name']
            for report in program_info['admission_reports']:
                for key in report.keys():
                    if key not in all_fieldnames:
                        all_fieldnames.append(key)

            report_writer = csv.DictWriter(csvfile, fieldnames=all_fieldnames)
            
            if not reports_file_exists:
                report_writer.writeheader()
            
            for report in program_info.get('admission_reports', []):
                report_row = {
                    'Program ID': program_info.get('Program ID', ''),
                    'Program Name': program_info.get('Program Name', '')
                }
                report_row.update(report)
                report_writer.writerow(report_row)
        
        print(f"Admission reports saved to {reports_filename}")

def extract_program_info(driver, program):
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
                        detail_link = columns[6].find_element(By.CSS_SELECTOR, "div.jsx-2980137639 a")
                        driver.execute_script("arguments[0].scrollIntoView(true);", detail_link)
                        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(detail_link))
                        driver.execute_script("arguments[0].click();", detail_link)
                        print("Clicked '详情' link using JavaScript")

                        # Wait for the modal to appear
                        modal = WebDriverWait(driver, 20).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".ant-modal-content"))
                        )

                        # Extract modal content
                        modal_rows = modal.find_elements(By.CSS_SELECTOR, ".ant-descriptions-row")
                        for modal_row in modal_rows:
                            labels = modal_row.find_elements(By.CSS_SELECTOR, ".ant-descriptions-item-label")
                            contents = modal_row.find_elements(By.CSS_SELECTOR, ".ant-descriptions-item-content")
                            for label, content in zip(labels, contents):
                                key = label.text.strip()
                                value = content.text.strip()
                                report[key] = value

                        program_info['admission_reports'].append(report)
                        print(f"Added report to program_info: {report['报告时间']}")

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
        save_to_csv(program_info)

        return program_info
    except Exception as e:
        print(f"An error occurred while extracting program info: {e}")
        return {}

def check_program_page_html(driver):
    try:
        # Verify the presence of key elements on the program page
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".text-\\#5BAE93.bg-\\#D3F4EA.rounded-lg.text-xs.px-2.py-px.font-medium")))
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".text-\\#4E4E4E.font-bold.text-xs.lg\\:text-sm.mr-3 + div")))
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#rank .flex.space-x-4.items-center")))
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".flex.mt-1.space-x-7 div")))
        return True
    except TimeoutException:
        print("Program page HTML structure is not as expected.")
        return False

def save_program_data(program_info, filename='program_data.csv'):
    with open(filename, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        row = [
            program_info.get('Program Name', ''),
            program_info.get('University', ''),
            program_info.get('Department', ''),
            ', '.join(program_info.get('Tags', [])),
            program_info.get('Admissions', ''),
            program_info.get('Applicants', ''),
            program_info.get('Median GPA', ''),
            program_info.get('TOEFL', ''),
            program_info.get('GRE', ''),
            program_info.get('US News Ranking', ''),
            program_info.get('Cost of Living', ''),
            json.dumps(program_info.get('General Ranking', []), ensure_ascii=False),
            json.dumps(program_info.get('Admissions Statistics', []), ensure_ascii=False)
        ]
        writer.writerow(row)

    # Save admission reports to a separate CSV file
    if 'admission_reports' in program_info:
        reports_filename = 'admission_reports.csv'
        reports_file_exists = os.path.exists(reports_filename)
        
        with open(reports_filename, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            if not reports_file_exists:
                headers = ['Program Name'] + list(program_info['admission_reports'][0].keys())
                writer.writerow(headers)
            
            for report in program_info['admission_reports']:
                row = [program_info.get('Program Name', '')] + list(report.values())
                writer.writerow(row)

def scrape_programs(driver, base_url):
    try:
        driver.get(base_url)
        print("Waiting for the page to load completely...")
        random_delay(30, 40)

        page_number = 1

        while True:
            retry_count = 0
            while retry_count < 3:
                try:
                    WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.bg-white.text-\\#5E5E5E.shadow-card')))
                    programs = driver.find_elements(By.CSS_SELECTOR, '.bg-white.text-\\#5E5E5E.shadow-card')
                    
                    for program in programs:
                        program_info = extract_program_info(driver, program)
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
            base_url = "https://offer.1point3acres.com/db/programs/DataScience-Analytics-MS-"
            scrape_programs(driver, base_url)
            
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
