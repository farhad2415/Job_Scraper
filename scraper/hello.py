import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

def scrape_jobs():
    # Initialize the WebDriver (Make sure to specify the path to your WebDriver)
    driver = webdriver.Chrome()

    # Navigate to the main job listings page
    base_url = 'https://www.olx.ro/oferte/q-%C3%AEngrijitor-de-animale/'
    driver.get(base_url)

    scraped_jobs = []

    try:
        # Loop through each job listing on the main page
        job_links = []
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        # Collect all job links on the page
        job_grid_elements = soup.find_all("div", class_='css-j0t2x2')
        for job_element in job_grid_elements:
            job_link_tag = job_element.find('a', href=True)
            if job_link_tag:
                job_links.append(job_link_tag['href'])

        # Now visit each job details page and collect data
        for job_link in job_links:
            # Navigate to the job details page
            driver.get(job_link)

            # Collect job data from the details page
            job_position = driver.find_element(By.CSS_SELECTOR, 'h1').text
            employer_name = driver.find_element(By.CLASS_NAME, 'css-1nj5a90').text

            print(f"Scraping job: {job_position} at {employer_name}")

            # Click to reveal phone number if necessary
            try:
                call_sms_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "css-qrbsyz"))
                )
                call_sms_button.click()
                time.sleep(2)
                phone_number_element = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.CLASS_NAME, "css-v1ndtc"))
                )
                phone_number = phone_number_element.text
            except:
                phone_number = "Phone number not available"

            # Store the data in a dictionary
            job_data = {
                "job_position": job_position,
                "employer_name": employer_name,
                "phone_number": phone_number,
                "job_link": job_link
            }

            # Append the job data to the list
            scraped_jobs.append(job_data)

            # Navigate back to the job listings page
            driver.back()
        time.sleep(10)  # Allow some time for the page to load before next iteration

    finally:
        # Close the WebDriver
        driver.quit()

    return scraped_jobs

# Example usage:
jobs = scrape_jobs()
for job in jobs:
    print(job)
