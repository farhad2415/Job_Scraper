from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

def scrape_job_details(url, max_pages):
    base_url = url.strip()
    service1 = Service(ChromeDriverManager().install())
    options = Options()
    
    # options.add_argument('--headless') 
    driver = webdriver.Chrome(service=service1, options=options)

    data = {
        "is_success": False,
        'url': url,
        'total_jobs': 0,
        'total_skipped_jobs': 0
    }
    total_skipped_jobs = 0

    if base_url == "https://jobsinmalta.com/jobs":
        try:
            for page_number in range(1, max_pages + 1):
                url = f"{base_url}/page:{page_number}/"
                print(f"Scraping URL: {url}") 

                driver.get(url)
                if "No results found" in driver.page_source:
                    print(f"No more pages found after page {page_number-1}.")
                    break
                
                job_grid_elements = driver.find_elements(By.CLASS_NAME, 'mobile-job-grid')
                if job_grid_elements:
                    for job_element in job_grid_elements:
                        position = job_element.find_element(By.TAG_NAME, 'h2').text
                        company = job_element.find_element(By.CLASS_NAME, 'job-sub-title').text
                        print(f"Position: {position}")

                        # Example of saving logic:
                        # if not Job.objects.filter(position=position, company=company).exists():
                        #     scraped_data = Job(position=position, company=company)
                        #     scraped_data.save()
                        # else:
                        #     total_skipped_jobs += 1
                    
                    # Update the data dictionary after processing job elements
                    data["is_success"] = True
                    data['total_jobs'] = len(job_grid_elements)
                    data['total_skipped_jobs'] = total_skipped_jobs
                else:
                    print(f"No job elements found on page {page_number}.")

            time.sleep(15)

        except Exception as e:
            print(f"An error occurred: {e}")
        
        finally:
            driver.quit()
    
    return data  # Return the data dictionary

# Call the function and print the result
output = scrape_job_details("https://jobsinmalta.com/jobs", 1)
print(output)
