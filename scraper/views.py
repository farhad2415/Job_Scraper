from bs4 import BeautifulSoup
from requests import request
from django.shortcuts import get_object_or_404
from .models import AvilableUrl, Job, Category
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib import messages
from selenium.common.exceptions import WebDriverException
from django.shortcuts import render, redirect
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout, authenticate, login as auth_login
import re
 
def scrape_job_details(url, max_pages, category_slug, request):
    base_url = url.strip()
    category_slug = category_slug.strip()
    category_name = Category.objects.get(slug=category_slug).name
    chrome_options = Options()
    # chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    # chrome_options.add_argument('--headless')
    # chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--remote-debugging-port=9222')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
                                                                                                                              
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
                page_source = BeautifulSoup(driver.page_source, features="lxml")
                
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
                        scraped_data = Job(position=job_title_detail, company=company_name, location=job_location, job_type=job_type, 
                                           description=description, job_posted=job_posting_date, job_link=job_details_url, source=source, job_category=category_name, user=request.user)
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
    if base_url == "https://jobzz.ro/":

        total_stored = 0
        total_skipped_jobs = 0
        data = {
            "is_success": False,
            'url': base_url,
            'category_slug': category_slug,
        }
        total_job_found = 0
        try:
            for page_number in range(1, max_pages + 1):
                url = f"{base_url}{category_slug}_{page_number}.html"
                driver.get(url)
                page_source = BeautifulSoup(driver.page_source, features="lxml")
                
                if "Nu am găsit niciun rezultat" in page_source.get_text():
                    print(f"No more pages found after page {page_number-1}.")
                    break
                job_grid_elements = page_source.find_all("a", class_='main_items item_cart')
                if not job_grid_elements:
                    print(f"No job elements found on page {page_number}.")
                    break
                total_job_found = len(job_grid_elements)
                for job_element in job_grid_elements:
                    job_title = job_element.find("span", class_="title").get_text(strip=True) if job_element.find("span", class_="title") else "Position not found"
                    job_url = job_element['href'] if job_element else None
                    if not job_url:
                        print("Job URL not found, skipping.")
                        data['total_skipped_jobs'] += 1
                        continue
                    job_details_url = f"{job_url}"
                    driver.get(job_details_url)
                    job_details_page = BeautifulSoup(driver.page_source, 'lxml')
                    salary = job_details_page.find("span", id="price").get_text(strip=True) if job_details_page.find("span", id="price") else "Salary not found"
                    #location_city by id
                    job_location = job_details_page.find("span", id="location_city").get_text(strip=True) if job_details_page.find("span", id="location_city") else "Location not found"
                    source = "Jobzz.ro"
                    company_name = job_details_page.find("div", class_="account_right").get_text(strip=True) if job_details_page.find("div", class_="account_right") else "Company not found"
                    category_name = Category.objects.get(slug=category_slug).name
                    job_posting_date = job_details_page.find("div", class_="info_extra_details").get_text(strip=True) if job_details_page.find("div", class_="info_extra_details") else "Date not found"
                    job_type = job_details_page.find("span", id="job_type").get_text(strip=True) if job_details_page.find("span", id="job_type") else "Type not found"
                    job_description = job_details_page.find("p", id="paragraph").get_text(separator=" ", strip=True) if job_details_page.find("p", id="paragraph") else "Description not found"

                    if not Job.objects.filter(position=job_title, company=company_name, location=job_location, job_type=job_type, user=request.user).exists():
                        scraped_data = Job(position=job_title, company=company_name, location=job_location, job_type=job_type, 
                                           description=job_description, job_posted=job_posting_date, job_link=job_details_url, source=source, job_category=category_name, user=request.user, salary=salary)
                        scraped_data.save()
                        total_stored += 1
                    else:
                        total_skipped_jobs += 1
                data = {
                    "is_success": True,
                    'url': url,
                    'total_jobs_found': total_job_found,
                    'total_stored': total_stored,
                   ' total_skipped_jobs': total_skipped_jobs
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
    if base_url == "https://www.posao.hr/djelatnosti/":
        total_stored = 0
        total_skipped_jobs = 0
        data = {
            "is_success": False,
            'url': base_url,
            'category_slug': category_slug,
        }
        total_job_found = 0
        try:
            for page_number in range(1, max_pages + 1):
                # url = f"{base_url}{category_slug}"
                # driver.get(url)
                if page_number == 1:
                    url = f"{base_url}{category_slug}"
                else:
                    url = f"{base_url}{category_slug}/stranica/{page_number}/"
                
                driver.get(url)
                page_source = BeautifulSoup(driver.page_source, features="lxml")
                if "Nema oglasa" in page_source.get_text():
                    print(f"No more pages found after page {page_number-1}.")
                    break
               
                # intro a get link and open in new tab and get details
                job_grid_elements = page_source.find_all("div", class_='intro')
                if not job_grid_elements:
                    print(f"No job elements found on page {page_number}.")
                    break
                total_job_found = len(job_grid_elements)
                for job_element in job_grid_elements:
                    job_title = job_element.find("strong").get_text(strip=True) if job_element.find("strong") else "Position not found"
                    job_link = job_element.find("a", href=True)['href'] if job_element.find("a", href=True) else None
                    if not job_link:
                        print("Job URL not found, skipping.")
                        data['total_skipped_jobs'] += 1
                        continue
                    job_details_url = f"{job_link}"
                    driver.get(job_details_url)
                    job_details_page = BeautifulSoup(driver.page_source, 'lxml')    
                    if "not found" in job_details_page.get_text():
                        print("Job details not found, skipping.")
                        data['total_skipped_jobs'] += 1
                        continue
                    job_details_div = job_details_page.find_all("div", class_="ad_mask")
                    position_name = job_details_div[0].find("h1").get_text(strip=True) if job_details_div[0].find("h1") else "Position not found"
                    company_name = job_details_div[0].find("div", class_="single_job_ad_right").get_text(strip=True) if job_details_div[0].find("div", class_="single_job_ad_right") else "Company not found"
                    job_location_divs = job_details_div[0].find_all("div", class_="single_job_ad_right")
                    job_location = job_location_divs[2].get_text(strip=True) if len(job_location_divs) > 1 else "Location not found"
                    # phone_number = job_details_page.find(text=re.compile(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')).strip() if job_details_page.find(text=re.compile(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')) else "Phone not found"
                    email = job_details_page.find(text=re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')).strip() if job_details_page.find(text=re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')) else "Email not found"
                    job_category = Category.objects.get(slug=category_slug).name
                    source = "Posao.hr"
                    job_description_div = job_details_page.find("div", id="oglas")
                    if job_description_div:
                        job_description = job_description_div.get_text(separator="\n",strip=True)
                        job_description = job_description.replace('\n', ' ')
                    else:
                        job_description = "Job description not found"

                    # from "sidebar" find "company_link" and get href
                    website_element = job_details_page.find_all("div", id="sidebar")[0]
                    website_div = website_element.find("div", class_="company_link")
                    website_link = website_div.find("a", href=True)['href'] if website_div.find("a", href=True) else "Website not found"

                    if not Job.objects.filter(position=position_name, company=company_name, location=job_location, user=request.user).exists():
                        scraped_data = Job(position=position_name, company=company_name, location=job_location, email=email, description=job_description, job_link=job_details_url, source=source, job_category=job_category, user=request.user, website=website_link)
                        scraped_data.save()
                        total_stored += 1
                    else:
                        total_skipped_jobs += 1
                data = {
                    "is_success": True,
                    'url': url,
                    'total_jobs_found': total_job_found,
                    'total_stored': total_stored,
                   ' total_skipped_jobs': total_skipped_jobs
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
    if base_url == "https://www.zaplata.bg/":
        total_stored = 0
        total_skipped_jobs = 0
        data = {
            "is_success": False,
            'url': base_url,
            'category_slug': category_slug,
        }
        try:
            for page_number in range(1, max_pages + 1):
                if page_number == 1:
                    url = f"{base_url}{category_slug}"
                else:
                    url = f"{base_url}{category_slug}/page:{page_number}/"
                driver.get(url)
                page_source = BeautifulSoup(driver.page_source, features="html.parser")
                job_grid_elements = page_source.find_all("div", class_='grid')
                if not job_grid_elements:
                    print(f"No job elements found on page {page_number}.")
                    break
                else:
                    total_job_found = len(job_grid_elements)
                    for job_element in job_grid_elements:
                        main_div = job_element.find("div", class_="main")
                        if main_div:
                            title_div = main_div.find("div", class_="title")
                            if title_div and title_div.find("a", href=True):
                                postiion = title_div.find("a").get_text(strip=True)
                                job_link = title_div.find("a", href=True)['href']
                                driver.get(job_link)
                                job_page_source = BeautifulSoup(driver.page_source, features="html.parser") 
                                job_description_div = job_page_source.find("div", class_="advert_description")
                                job_details_div = job_page_source.find("div", class_="info")
                                job_posting_date_data = job_details_div.find("div", class_="date")
                                if job_posting_date_data:
                                    job_posted = job_posting_date_data.find("div", class_="view").contents[0].strip()
                                else:
                                    job_posted = "Date not found"
                                location = job_details_div.find("a", class_="location").get_text(strip=True) if job_details_div.find("a", class_="location") else "Location not found"
                                job_type = job_details_div.find("a", class_="fulltime").get_text(strip=True) if job_details_div.find("a", class_="fulltime") else "Type not found"
                                job_category = Category.objects.get(slug=category_slug).name
                                source = "Zaplata.bg"
                                salary_span_data= job_details_div.find("span", class_="clever-link salary")
                                if salary_span_data:
                                    salary_from = salary_span_data.find_all("strong")[0].get_text(strip=True) if salary_span_data.find_all("strong") else "Salary not found"
                                    salary_to = salary_span_data.find_all("strong")[1].get_text(strip=True) if salary_span_data.find_all("strong") else "Salary not found"
                                    salary = f"{salary_from} to {salary_to} (Gross)"
                                else:
                                    salary = f"not found"
                                company_details_div = job_page_source.find("div", class_="company")
                                if company_details_div:
                                    company_name_divs = company_details_div.find_all("div", class_="comanyName")
                                    
                                    if len(company_name_divs) >= 2:
                                        company = company_name_divs[1].find("a").get_text(strip=True) if company_name_divs[1].find("a") else "Company name not found"
                                        profile_link = company_name_divs[1].find("a", href=True)['href'] if company_name_divs[1].find("a", href=True) else "Website not found"
                                    else:
                                        company = "Company name not found"
                                        profile_link = "Website not found"
                                else:
                                    company = "Company not found"
                                    profile_link = "Website not found"
                                driver.execute_script(f"window.open('{profile_link}', '_blank')")
                                driver.switch_to.window(driver.window_handles[-1])
                                driver.get(profile_link)
                                company_contact_page = BeautifulSoup(driver.page_source, features="html.parser")
                                contact_info_div = company_contact_page.find("div", class_="columns3 MT30")
                                if contact_info_div:
                                    # Extract phone number
                                    phone_div = contact_info_div.find("h3", class_="phone")
                                    phone_number = phone_div.find_next("div").get_text(strip=True) if phone_div else "Phone not found"
                                    
                                    # Extract website
                                    website_span = contact_info_div.find("span", class_="clever-link-blank nowrap")
                                    website = website_span.get("data-link") if website_span else "not found"
                                driver.close()
                                driver.switch_to.window(driver.window_handles[0])
                                if job_description_div:
                                    job_description = job_description_div.get_text(separator="\n", strip=True)
                                else:
                                    job_description = "Description not found"
                                if not Job.objects.filter(position=postiion, company=company, location=location, user=request.user).exists():
                                    scraped_data = Job(position=postiion, company=company, location=location, description=job_description, job_posted=job_posted, job_link=job_link, source=source, job_category=job_category, user=request.user, salary=salary, phone_number=phone_number, website=website)
                                    scraped_data.save()
                                    total_stored += 1
                                else:
                                    total_skipped_jobs += 1
                                data = {
                                    "is_success": True,
                                    'url': url,
                                    'total_jobs_found': total_job_found,
                                    'total_stored': total_stored,
                                    'total_skipped_jobs': total_skipped_jobs
                                }
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
    return data



# Scrape Job
@login_required(login_url='login')
def scrape_job(request):
    urls = AvilableUrl.objects.all()  
    selected_url = None 
    categories = Category.objects.none()  
    max_pages = None
    category_slug = None

    if request.method == 'POST':
        url_id = request.POST.get('url') 
        max_pages = request.POST.get('max_pages')  
        category_slug = request.POST.get('category') 
        if url_id:
            selected_url = get_object_or_404(AvilableUrl, id=url_id)
            categories = selected_url.category.all()
        if max_pages and category_slug and selected_url:
            try:
                max_pages = int(max_pages)  
                category = get_object_or_404(Category, slug=category_slug)
                data = scrape_job_details(selected_url.url, max_pages, category.slug, request)
                if data['is_success']:
                    return JsonResponse({
                        'is_success': True,
                        'total_jobs_found': data['total_jobs_found'],
                        'total_stored': data['total_stored'],
                    })
                else:
                    return JsonResponse({'is_success': False, 'url': selected_url.url})
            except ValueError:
                return JsonResponse({'is_success': False, 'error': 'Max pages must be a valid number.'})
            except Exception as e:
                return JsonResponse({'is_success': False, 'error': str(e)})

    return render(request, 'store_job.html', {'urls': urls, 'selected_url': selected_url, 'categories': categories, 'max_pages': max_pages, 'category_slug': category_slug})

# Scrape View
@login_required(login_url='login')  
def scrape_view(request):
    jobs = Job.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(jobs, 20) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    total_jobs = jobs.count()

    return render(request, 
                    'job_scraper.html', {
                        'page_obj': page_obj, 
                        'total_jobs': total_jobs
                        })

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
@login_required(login_url='login')
def home(request):
    return render(request, 'home.html')

# Login Page #login
def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('home')  # Redirect to a home page or dashboard
        else:
            messages.error(request, 'Invalid username or password')
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')

# export_to_excel function to export job data to excel file
import pandas as pd
from django.http import HttpResponse
from django.utils.timezone import make_naive
from datetime import datetime

def export_to_excel(request):
    data = Job.objects.filter(user=request.user)
    data_dict = list(data.values())
    for item in data_dict:
        for key, value in item.items():
            if isinstance(value, pd.Timestamp) or isinstance(value, datetime):
                item[key] = make_naive(value)

    df = pd.DataFrame(data_dict)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="jobs.xlsx"'
    df.to_excel(response, index=False, engine='openpyxl')
    return response


