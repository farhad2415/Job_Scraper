from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from .models import AvilableUrl, Job, Category
from django.http import JsonResponse
from django.shortcuts import render
from django.core.paginator import Paginator
from django.contrib import messages
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
def scrape_job_details(url, max_pages, category_slug):
    base_url = url.strip()
    category_slug = category_slug.strip()
    # service = Service('/usr/bin/chromedriver')
    # service1 = Service(ChromeDriverManager().install())
    # options = Options()
    # options.add_argument('--headless') 
    # driver = webdriver.Chrome(service=service1, options=options)
    options = Options()
    options.add_argument('--window-size=1920,1080')
    driver = webdriver.Chrome(service=Service(
        ChromeDriverManager().install()), options=options)

    data = {
        "is_success": False,
        'url': url,
        'category_slug': category_slug,
        'total_jobs_found': 0,
        'total_skipped_jobs': 0
    }
    total_skipped_jobs = 0
    if base_url == "https://www.romjob.ro/anunturi/locuri-de-munca/":
        data = {
            "is_success": False,
            'url': base_url,
            'category_slug': category_slug,
            'total_jobs_found': 0,
            'total_skipped_jobs': 0,
            'job_details': []
        }

        try:
            for page_number in range(1, max_pages + 1):
            #    make url as f"{base_url}/{category_slug}/page:{page_number}/"
                url = f"{base_url}{category_slug}/?page:{page_number}/"
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
    category = Category.objects.all()
    if request.method == 'POST':
        url = request.POST.get('url')
        max_pages = int(request.POST.get('max_pages'))
        category.slug = request.POST.get('category')    
        if url:
            try:
                scrape_job_details(url, max_pages, category.slug)
                data = scrape_job_details(url, max_pages, category.slug)
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

    
    return render(request, 'store_job.html', {'category': category})


# scrape_view make function for view all job data and render to template job_scraper.html
def scrape_view(request):
    jobs = Job.objects.all() 
    paginator = Paginator(jobs, 20) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    total_jobs = jobs.count()

    return render(request, 
                    'job_scraper.html', {
                        'page_obj': page_obj, 
                        'total_jobs': total_jobs
                        })



from django.shortcuts import redirect
# Update Phone Number When Geeting Null
def update_phone_number(request, job_id):
    if request.method == "POST":
        phone_number = request.POST.get('phone_number')
        job = Job.objects.get(id=job_id)
        job.phone_number = phone_number
        job.save()
        messages.success(request, "Phone number updated successfully!") 
        return redirect(request.META['HTTP_REFERER'])


# Update Salary Button   
def update_salary(request, job_id):
    if request.method == "POST":
        salary = request.POST.get('salary')
        job = Job.objects.get(id=job_id)
        job.salary = salary
        job.save()
        messages.success(request, "Salary updated successfully!") 
        return redirect(request.META['HTTP_REFERER'])


# Defualt Home Page
def home(request):
    return render(request, 'home.html')


# export_to_excel function to export job data to excel file
import pandas as pd
from django.http import HttpResponse
def export_to_excel(request):
    data = Job.objects.all()
    df = pd.DataFrame(list(data.values()))
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="jobs.xlsx"'
    df.to_excel(response, index=False, engine='openpyxl')
    return response
