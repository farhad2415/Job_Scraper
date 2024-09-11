from urllib import request
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from .models import AvilableUrl, Job
from django.http import JsonResponse
from django.shortcuts import render
from django.core.paginator import Paginator
from django.contrib import messages
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException

def scrape_job_details(url, max_pages):
    base_url = url.strip()
    # service = Service('/usr/bin/chromedriver')
    service1 = Service(ChromeDriverManager().install())
    options = Options()
    options.add_argument('--headless') 
    driver = webdriver.Chrome(service=service1, options=options)

    data = {
        "is_success": False,
        'url': url,
        'total_jobs_found': 0,
        'total_skipped_jobs': 0
    }
    total_skipped_jobs = 0
    if base_url == "https://jobsinmalta.com/jobs":
        try:
            for page_number in range(1 , max_pages + 1):
                url = f"{base_url}/page:{page_number}/"
                print(f"Scraping URL: {url}") 

                driver.get(url)
                if "No results found" in driver.page_source:
                    print(f"No more pages found after page {page_number-1}.")
                    break
                job_grid_elements = driver.find_elements(By.CLASS_NAME, 'mobile-job-grid')
                if job_grid_elements:
                    for job_element in job_grid_elements:
                        position = job_element.find_element(By.TAG_NAME, 'h2').text if job_element.find_element(By.TAG_NAME, 'h2') else "Position not found"
                        company = job_element.find_element(By.CLASS_NAME, 'job-sub-title').text if job_element.find_element(By.CLASS_NAME, 'job-sub-title') else "Company not found"
                        job_salary = job_element.find_element(By.CLASS_NAME, 'job-sub-details-title')[0].text if job_element.find_element(By.CLASS_NAME, 'job-sub-details-title')[0] else "Salary not found"
                        job_type = job_element.find_element(By.CLASS_NAME, 'job-sub-details-title')[1].text if job_element.find_element(By.CLASS_NAME, 'job-sub-details-title')[1] else "Type not found"
                        experience = job_element.find_element(By.CLASS_NAME, 'job-sub-details-title')[2].text if job_element.find_element(By.CLASS_NAME, 'job-sub-details-title')[2] else "Experience not found"
                        print(f"Position: {position}, Company: {company}, Salary: {job_salary}, Type: {job_type}, Experience: {experience}")
                        # scraped_data = Job(position=position, company=company)
                        # scraped_data.save()
                        if not Job.objects.filter(position=position, company=company, salary=job_salary).exists():
                            scraped_data = Job(position=position, company=company, salary=job_salary)
                            scraped_data.save()
                        else:
                            total_skipped_jobs += 1
                        data = {
                        "is_success": True,
                        'url': url,
                        'total_jobs_found': len(job_grid_elements),
                        'total_skipped_jobs': total_skipped_jobs
                        }
                else:
                    print(f"No job elements found on page {page_number}.")
            time.sleep(15)
            return data
        # if an error occurs while permission denied
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            driver.quit()

    if base_url == "https://www.olx.ro/oferte/q-%C3%AEngrijitor-de-animale/":
        data = {
            "is_success": False,
            'url': url,
            'total_jobs_found': 0,
            'total_skipped_jobs': 0
        }
        try:
            for page_number in range(1, max_pages + 1):
                url = f"{base_url}?page={page_number}"
                print(f"Scraping URL: {url}")

                driver.get(url)
                page_source = driver.page_source
                if "Nu am găsit niciun rezultat" in page_source:
                    print(f"No more pages found after page {page_number-1}.")
                    break
                page_source = BeautifulSoup(page_source, 'html.parser')
                job_grid_elements = page_source.find_all("div", class_='css-j0t2x2')
                
                if not job_grid_elements:
                    print(f"No job elements found on page {page_number}.")
                    continue
                job_element = job_grid_elements[0]
                data_processed = False
                for index, content in enumerate(job_element.contents):
                    if index % 4 == 0:  # Skip index 0, 4, 8, etc.
                        continue
                    
                    job_position = content.find("h6").get_text(strip=True) if content.find("h6") else "Position not found"
                    job_salary = content.find_all("p")[0].get_text(strip=True) if content.find("p") else "Salary not found"
                    job_location = content.find_all("p")[1].get_text(strip=True) if len(content.find_all("p")) > 1 else "Location not found"
                    job_type = content.find_all("p")[2].get_text(strip=True) if len(content.find_all("p")) > 2 else "Type not found"
                        

                    if not Job.objects.filter(position=job_position, salary=job_salary, location=job_location, job_type=job_type).exists():
                        scraped_data = Job(position=job_position, salary=job_salary, location=job_location, job_type=job_type)
                        scraped_data.save()
                        data_processed = True  # Set flag to True if data is processed
                    # Show a message if any data was processed
                    if data_processed:
                        print("Data has been processed and saved.")
                    else:
                        total_skipped_jobs += 1
            data = {
                "is_success": True,
                'url': url,
                'total_jobs_found': len(job_element),
                'total_skipped_jobs': total_skipped_jobs
            }
            return data     
        finally:
            try:
                driver.quit()
            except WebDriverException as e:
                print(f"WebDriverException: {e}")
            except PermissionError as e:
                print(f"PermissionError: {e}. Unable to terminate the WebDriver process.")
            except Exception as e:
                print(f"An unexpected error occurred while quitting the driver: {e}")


    if base_url == "https://www.romjob.ro/anunturi/locuri-de-munca/":
        data = {
            "is_success": False,
            'url': base_url,
            'total_jobs_found': 0,
            'total_skipped_jobs': 0,
            'job_details': []
        }

        try:
            for page_number in range(1, max_pages + 1):
                url = f"{base_url}?page={page_number}"
                print(f"Scraping URL: {url}")
                driver.get(url)
                page_source = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Check for end of pages
                if "Nu am găsit niciun rezultat" in page_source.get_text():
                    print(f"No more pages found after page {page_number-1}.")
                    break

                job_grid_elements = page_source.find_all("div", class_='article-txt-wrap')

                if not job_grid_elements:
                    print(f"No job elements found on page {page_number}.")
                    break

                for job_element in job_grid_elements:
                    job_title = job_element.find("h2").get_text(strip=True) if job_element.find("h2") else "Position not found"
                    job_url = job_element.find("a", href=True)['href'] if job_element.find("a", href=True) else None

                    if not job_url:
                        print("Job URL not found, skipping.")
                        data['total_skipped_jobs'] += 1
                        continue

                    job_details_url = f"{job_url}"
                    driver.get(job_details_url)

                    # Parse job details page
                    job_details_page = BeautifulSoup(driver.page_source, 'html.parser')

                    # Extract job details
                    job_title_detail = job_details_page.find("h1", itemprop="name").get_text(strip=True) if job_details_page.find("h1", itemprop="name") else "Title not found"
                    # medium-5 columns location
                    job_location = job_details_page.find("div", class_="medium-5 columns").get_text(strip=True) if job_details_page.find("div", class_="medium-5 columns") else "Location not found"
                    source = "RomJob.ro"
                    job_posting_date = job_details_page.find("i", itemprop="validFrom").get_text(strip=True) if job_details_page.find("i", itemprop="validFrom") else "Date not found"
                    company_name = job_details_page.find("div", class_="attribute-value").get_text(strip=True) if job_details_page.find("div", class_="attribute-value") else "Company not found"
                    # job_type get from attribute-value but 2nd index
                    job_type = job_details_page.find_all("div", class_="attribute-value")[1].get_text(strip=True) if job_details_page.find_all("div", class_="attribute-value") else "Type not found"
                    # description = job_details_page.find("span", itemprop="description").get_text(strip=True) if job_details_page.find("span", itemprop="description") else "Description not found"
                    description_element = job_details_page.find("span", itemprop="description")
                    if description_element:
                        for br in description_element.find_all("br"):
                            br.replace_with("\n")
                        description = description_element.get_text(strip=True)
                        formatted_description = f"Job Description:\n\n{description}"
                    else:
                        formatted_description = "Description not found"
                    description = formatted_description
                    # save to Job model
                    if not Job.objects.filter(position=job_title_detail, company=company_name, location=job_location, job_type=job_type).exists():
                        scraped_data = Job(position=job_title_detail, company=company_name, location=job_location, job_type=job_type, description=description, job_posted=job_posting_date, job_link=job_details_url, source=source)
                        scraped_data.save()

                else:
                    total_skipped_jobs += 1
                data = {
                    "is_success": True,
                    'url': url,
                    'total_jobs_found': len(job_grid_elements),
                    'total_skipped_jobs': total_skipped_jobs
                }
            return data
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            try:
                driver.quit()
            except WebDriverException as e:
                print(f"WebDriverException: {e}")
            except PermissionError as e:
                print(f"PermissionError: {e}. Unable to terminate the WebDriver process.")
            except Exception as e:
                print(f"An unexpected error occurred while quitting the driver: {e}")
                    
def scrape_job(request):
    if request.method == 'POST':
        url = request.POST.get('url')
        max_pages = int(request.POST.get('max_pages'))
        if url:
            try:
                scrape_job_details(url, max_pages)  # Assuming this function is defined elsewhere
                data = scrape_job_details(url, max_pages)
                if data['is_success']:
                    messages.success(request, f"Scraping completed successfully!")
                else:
                    messages.error(request, f"Invalid Url given ::{data['url']}.")
                # messages.success(request, "Scraping completed successfully!")
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
        else:
            messages.error(request, "No URL provided.")
            return JsonResponse({'error': 'No URL provided'}, status=400)

    all_available_urls = AvilableUrl.objects.all()
    return render(request, 'store_job.html', {'all_available_urls': all_available_urls})


# scrape_view make function for view all job data and render to template job_scraper.html
def scrape_view(request):
    jobs = Job.objects.all() 
    paginator = Paginator(jobs, 20) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'job_scraper.html', {'page_obj': page_obj})

from django.shortcuts import redirect

def update_phone_number(request, job_id):
    if request.method == "POST":
        phone_number = request.POST.get('phone_number')
        job = Job.objects.get(id=job_id)
        job.phone_number = phone_number
        job.save()
        messages.success(request, "Phone number updated successfully!") 
        return redirect(request.META['HTTP_REFERER'])
    
def update_salary(request, job_id):
    if request.method == "POST":
        salary = request.POST.get('salary')
        job = Job.objects.get(id=job_id)
        job.salary = salary
        job.save()
        messages.success(request, "Salary updated successfully!") 
        return redirect(request.META['HTTP_REFERER'])

def home(request):
    return render(request, 'home.html')

import pandas as pd
from django.http import HttpResponse
def export_to_excel(request):
    data = Job.objects.all()
    df = pd.DataFrame(list(data.values()))
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="jobs.xlsx"'
    df.to_excel(response, index=False, engine='openpyxl')
    return response
