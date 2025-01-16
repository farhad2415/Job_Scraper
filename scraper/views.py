from bs4 import BeautifulSoup
from requests import request
from django.shortcuts import get_object_or_404
import requests
from .models import AvilableUrl, Job, Category, Notice
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib import messages
from selenium.common.exceptions import WebDriverException, TimeoutException
from django.shortcuts import render, redirect
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout, authenticate, login as auth_login
import re
import time
import easyocr
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

 
def scrape_job_details(url, max_pages, category_slug, request):
    base_url = url.strip()
    category_slug = category_slug.strip()
    category_name = Category.objects.get(slug=category_slug).name
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--remote-debugging-port=9222')
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
                                                                                                                              
    data = {
        "is_success": False,
        'url': url,
        'category_slug': category_slug,
        'total_jobs_found': 0,
        'total_stored': 0,
        'total_skipped_jobs': 0
    }
    if base_url == "https://www.romjob.ro/anunturi/locuri-de-munca/": 
        total_stored = 0
        total_skipped_jobs = 0
        total_jobs_found = 0
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
                url = f"{base_url}{category_slug}/?page:{page_number}/"
                print(f"Scraping URL: {url}")
                driver.get(url)
                page_source = BeautifulSoup(driver.page_source, features="lxml")
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
                    try:
                        wait = WebDriverWait(driver, 5)
                        show_phone_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn-act.btn-show-phone")))
                        show_phone_button.click()
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".telnumber")))
                        job_details_page = BeautifulSoup(driver.page_source, 'html.parser')
                        job_title_detail = job_details_page.find("h1", itemprop="name").get_text(strip=True) if job_details_page.find("h1", itemprop="name") else "Title not found"
                        job_location = job_details_page.find("div", class_="medium-5 columns").get_text(strip=True) if job_details_page.find("div", class_="medium-5 columns") else "Location not found"
                        source = "RomJob.ro"
                        job_posting_date = job_details_page.find("i", itemprop="validFrom").get_text(strip=True) if job_details_page.find("i", itemprop="validFrom") else "Date not found"
                        company_name = job_details_page.find("div", class_="attribute-value").get_text(strip=True) if job_details_page.find("div", class_="attribute-value") else "Company not found"
                        job_type = job_details_page.find_all("div", class_="attribute-value")[1].get_text(strip=True) if job_details_page.find_all("div", class_="attribute-value") else "Type not found"
                        formatted_description = job_details_page.find("div", class_="article-description").get_text(strip=True) if job_details_page.find("div", class_="article-description") else "Description not found"
                        description = formatted_description
                        phone_number = None
                        try:
                            phone_number_element = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "span.telnumber"))
                            )
                            WebDriverWait(driver, 10).until(
                                    lambda driver: phone_number_element.value_of_css_property("background-image") != 'none')
                            phone_number_image = phone_number_element.screenshot_as_png
                            reader = easyocr.Reader(['en'])
                            phone_number = reader.readtext(phone_number_image)
                            phone_number = phone_number[0][-2] if phone_number else "not found"
                        except Exception as e:
                            print(f"no number: {e}")
                            phone_number = "not found"
                        if not Job.objects.filter(position=job_title_detail, company=company_name, location=job_location, job_type=job_type).exists():
                            scraped_data = Job(position=job_title_detail, company=company_name, location=job_location, job_type=job_type, 
                                            description=description, job_posted=job_posting_date, job_link=job_details_url, source=source, job_category=category_name, user=request.user, phone_number=phone_number)
                            scraped_data.save()
                        else:
                            total_skipped_jobs += 1
                    except Exception as e:
                        print(f"{e}")
                        continue
                data = {
                    "is_success": True,
                    'url': url,
                    'total_jobs_found': len(job_grid_elements),
                    'total_stored': len(job_grid_elements) - total_skipped_jobs,
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
        total_jobs_found = 0
        data = {
            "is_success": False,
            'url': base_url,
            'category_slug': category_slug,
        }

        try:
            for page_number in range(1, max_pages + 1):
                url = f"{base_url}{category_slug}{'_' + str(page_number) if page_number > 1 else ''}.html"
                driver.get(url)
                page_source = BeautifulSoup(driver.page_source, features="lxml")
                
                if "Nu am găsit niciun rezultat" in page_source.get_text():
                    print(f"No more pages found after page {page_number-1}.")
                    break

                job_grid_elements = page_source.find_all("a", class_='main_items item_cart')
                if not job_grid_elements:
                    print(f"No job elements found on page {page_number}.")
                    break

                for job_element in job_grid_elements:
                    job_title = job_element.find("span", class_="title").get_text(strip=True) if job_element.find("span", class_="title") else "Position not found"
                    job_url = job_element['href'] if job_element else None
                    if not job_url:
                        print("Job URL not found, skipping.")
                        total_skipped_jobs += 1
                        continue

                    job_details_url = f"{job_url}"
                    driver.get(job_details_url)
                    wait = WebDriverWait(driver, 10)
                    try:
                        accept_cookies_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#onetrust-accept-btn-handler")))
                        accept_cookies_button.click()
                        print("Cookies accepted successfully.")
                    except Exception as e:
                        print(f"An error occurred while accepting cookies: {e}")
                    try:
                        show_phone_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#phone_holder")))
                        show_phone_button.click()
                        print("Phone holder clicked")
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#phone_number")))
                        print("Phone number loaded")
                        time.sleep(2)
                    except TimeoutException:
                        print("Phone holder or number not found")
                    job_details_page = BeautifulSoup(driver.page_source, 'lxml')
                    salary = job_details_page.find("span", id="price").get_text(strip=True) if job_details_page.find("span", id="price") else "Salary not found"
                    job_location = job_details_page.find("span", id="location_city").get_text(strip=True) if job_details_page.find("span", id="location_city") else "not found"
                    phone_number = job_details_page.find("span", id="phone_number").get_text(strip=True) if job_details_page.find("span", id="phone_number") else None
                    company_name = job_details_page.find("div", class_="account_right").get_text(strip=True) if job_details_page.find("div", class_="account_right") else "not found"
                    category_name = Category.objects.get(slug=category_slug).name
                    job_posting_date = job_details_page.find("div", class_="info_extra_details").get_text(strip=True) if job_details_page.find("div", class_="info_extra_details") else "Date not found"
                    job_type = job_details_page.find("span", id="job_type").get_text(strip=True) if job_details_page.find("span", id="job_type") else None
                    job_description = job_details_page.find("p", id="paragraph").get_text(separator=" ", strip=True) if job_details_page.find("p", id="paragraph") else "Description not found"

                    if not Job.objects.filter(position=job_title, company=company_name, location=job_location, job_type=job_type).exists():
                        scraped_data = Job(
                            position=job_title, 
                            company=company_name, 
                            location=job_location, 
                            job_type=job_type,
                            description=job_description, 
                            job_posted=job_posting_date, 
                            job_link=job_details_url, 
                            source="Jobzz.ro", 
                            job_category=category_name, 
                            user=request.user, 
                            phone_number=phone_number
                        )
                        scraped_data.save()
                        total_stored += 1
                    else:
                        total_skipped_jobs += 1

            data.update({
                "is_success": True,
                'total_jobs_found': total_jobs_found,
                'total_stored': total_stored,
                'total_skipped_jobs': total_skipped_jobs
            })
            return data
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            try:
                driver.quit()
            except Exception as e:
                print(f"An error occurred while quitting the driver: {e}")
    if base_url == "https://www.posao.hr/djelatnosti/":
        total_stored = 0
        total_skipped_jobs = 0
        total_jobs_found = 0
        data = {
            "is_success": False,
            'url': base_url,
            'category_slug': category_slug,
        }
        total_job_found = 0

        try:
            for page_number in range(1, max_pages + 1):
                # Construct the URL for the current page
                if page_number == 1:
                    url = f"{base_url}{category_slug}"
                else:
                    url = f"{base_url}{category_slug}/stranica/{page_number}/"

                # Load the page
                driver.get(url)
                page_source = BeautifulSoup(driver.page_source, features="lxml")

                # Check if there are no more jobs
                if "Nema oglasa" in page_source.get_text():
                    print(f"No more pages found after page {page_number - 1}.")
                    break

                # Find job elements
                all_job_elements_links = page_source.find_all("div", class_='list box')
                if not all_job_elements_links:
                    print(f"No job elements found on page {page_number}.")
                    break

                for get_links in all_job_elements_links:
                    job_grid_elements = get_links.find_all("a")
                    if not job_grid_elements:
                        print(f"No job links found in the grid on page {page_number}.")
                        break

                    for job_element in job_grid_elements:
                        job_link = job_element.get('href', None)
                        if job_link and job_link.startswith("https://www.posao.hr/oglasi/"):
                            total_job_found += 1
                            print(f"Scraping job details: {job_link}")
                            driver.get(job_link)
                            job_details_page = BeautifulSoup(driver.page_source, 'lxml')

                            # Extract job details
                            job_details_div = job_details_page.find_all("div", class_="ad_mask")
                            position_name = (
                                job_details_div[0].find("h1").get_text(strip=True)
                                if job_details_div and job_details_div[0].find("h1")
                                else "Position not found"
                            )
                            company_name = (
                                job_details_div[0].find("div", class_="single_job_ad_right").get_text(strip=True)
                                if job_details_div and job_details_div[0].find("div", class_="single_job_ad_right")
                                else "Company not found"
                            )
                            job_location_divs = job_details_div[0].find_all("div", class_="single_job_ad_right") if job_details_div else []
                            job_location = job_location_divs[2].get_text(strip=True) if len(job_location_divs) > 2 else "Location not found"
                            salary = job_location_divs[3].get_text(strip=True) if len(job_location_divs) > 3 else "Salary not found"

                            # Extract contact details
                            phone_number = job_details_page.find(text=re.compile(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'))
                            phone_number = phone_number.strip() if phone_number else "Phone not found"

                            email = job_details_page.find(text=re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'))
                            email = email.strip() if email else "Email not found"

                            job_category = Category.objects.get(slug=category_slug).name
                            source = "Posao.hr"

                            # Extract job description
                            job_description_div = job_details_page.find("section", class_="radial_single_job")
                            if job_description_div:
                                job_description = job_description_div.get_text(separator="\n", strip=True).replace('\n', ' ')
                            else:
                                job_description_div_alt = job_details_page.find("div", class_="glavniDio")
                                job_description = job_description_div_alt.get_text(separator="\n", strip=True).replace('\n', ' ') if job_description_div_alt else "Description not found"

                            # Extract company website
                            website_element = job_details_page.find("div", id="sidebar")
                            website_div = website_element.find("div", class_="company_link") if website_element else None
                            website_link = website_div.find("a", href=True)['href'] if website_div and website_div.find("a", href=True) else "Website not found"

                            # Check if job already exists
                            if not Job.objects.filter(position=position_name, company=company_name, location=job_location, user=request.user).exists():
                                # Save job to the database
                                scraped_data = Job(
                                    position=position_name,
                                    company=company_name,
                                    location=job_location,
                                    email=email,
                                    description=job_description,
                                    job_link=job_link,
                                    source=source,
                                    job_category=job_category,
                                    user=request.user,
                                    website=website_link
                                )
                                scraped_data.save()
                                total_stored += 1
                            else:
                                total_skipped_jobs += 1

            # Final data summary
            data.update({
                "is_success": True,
                'total_jobs_found': total_job_found,
                'total_stored': total_stored,
                'total_skipped_jobs': total_skipped_jobs,
            })

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
    if base_url == "https://www.zaplata.bg/":
        total_stored = 0
        total_skipped_jobs = 0
        total_jobs_found = 0
        data = {
            "is_success": False,
            'url': base_url,
            'category_slug': category_slug,
        }
        total_job_found = 0
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
                                company_name = job_details_div.find("span").get_text(strip=True) if job_details_div.find("span") else "not found"
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
                                company_details_div = job_page_source.find("div", class_="comanyName")
                                if company_details_div:
                                    profile_link = company_details_div.find("a", href=True)['href']
                                else:
                                    profile_link = "not found"
                                driver.execute_script(f"window.open('{profile_link}', '_blank')")
                                driver.switch_to.window(driver.window_handles[-1])
                                driver.get(profile_link)
                                company_contact_page = BeautifulSoup(driver.page_source, features="html.parser")
                                company_contact_div = company_contact_page.find("div", class_="columns3 MT30")
                                if company_contact_div:
                                    # Extract phone number based on "Телефон" header text
                                    phone_section = company_contact_div.find("h3", string="Телефон")
                                    if phone_section:
                                        phone_number_div = phone_section.find_next_sibling("div")
                                        phone_number = phone_number_div.get_text(strip=True) if phone_number_div else "not found"
                                    else:
                                        phone_number = "not found"

                                    # Extract website based on "Уебсайт" header text
                                    website_section = company_contact_div.find("h3", string="Уебсайт")
                                    if website_section:
                                        website_div = website_section.find_next_sibling("div")
                                        website_span = website_div.find("span", class_="clever-link-blank nowrap") if website_div else None
                                        website = website_span["data-link"] if website_span else "not found"
                                    else:
                                        website = "not found"

                                print(f"Phone Number: {phone_number}")
                                print(f"Website: {website}")
                                driver.close()
                                driver.switch_to.window(driver.window_handles[0])
                                if job_description_div:
                                    job_description = job_description_div.get_text(separator="\n", strip=True)
                                else:
                                    job_description = "Description not found"
                                if not Job.objects.filter(position=postiion, company=company_name, location=location, user=request.user).exists():
                                    scraped_data = Job(position=postiion, company=company_name, location=location, description=job_description, job_posted=job_posted, job_link=job_link, source=source, job_category=job_category, user=request.user, salary=salary, phone_number=phone_number, website=website)
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
    if base_url == "https://www.maltapark.com/jobs/category/":
        total_stored = 0
        total_skipped_jobs = 0
        total_jobs_found = 0
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
                    url = f"{base_url}{category_slug}/?page={page_number}"
                
                driver.get(url)
                page_source = BeautifulSoup(driver.page_source, features="html.parser")
                job_grid_elements_first = page_source.find("div", class_='ui items job unstackable listings')

                # Check if job_grid_elements_first is None
                if job_grid_elements_first is None:
                    print(f"Job grid not found on page {page_number}. Terminating scraping.")
                    data['is_success'] = total_stored > 0
                    data['total_jobs_found'] = total_stored + total_skipped_jobs
                    return data

                job_grid_elements = job_grid_elements_first.find_all("div", class_='content clearfix')

                # Check if no job elements found
                if not job_grid_elements:
                    print(f"No job elements found on page {page_number}. Terminating scraping.")
                    data['is_success'] = total_stored > 0  # Set success based on whether any jobs were stored
                    data['total_jobs_found'] = total_stored + total_skipped_jobs
                    return data
                
                for job_element in job_grid_elements:
                    title_div = job_element.find("a", class_="header")
                    location_div = job_element.find("div", class_="extra").text
                    location_text = location_div.strip()
                    if title_div:
                        postiion = title_div.get_text(strip=True)
                        job_link = title_div['href']
                        domain_link = 'https://www.maltapark.com'
                        full_job_link = f"{domain_link}{job_link}"
                        
                        driver.get(full_job_link)
                        job_page_source = BeautifulSoup(driver.page_source, features="html.parser") 
                        job_details_div = job_page_source.find("div", class_="margin-bottom-1")
                        company_name = job_details_div.find("h3", class_="company").get_text(strip=True) if job_details_div.find("h3", class_="company") else "not found"
                        all_description = job_details_div.find_all('p', class_='ui segment whitebg shadowbox phone-nopanel')
                        job_description = all_description[0].get_text(strip=True) if all_description else "not found"
                    
                        job_category = Category.objects.get(slug=category_slug).name
                        source = "MaltaPark.com"
                        job_posting_date = job_details_div.find_all("div", class_="labelvaluepair")[3].find("span").text
                        
                        if not Job.objects.filter(position=postiion, company=company_name, location=location_text, user=request.user).exists():
                            scraped_data = Job(position=postiion, company=company_name, location=location_text, description=job_description, job_link=full_job_link, source=source, job_category=job_category, user=request.user, job_posted=job_posting_date)
                            scraped_data.save()
                            total_stored += 1
                        else:
                            total_skipped_jobs += 1
                    data = {
                        "is_success": True,
                        'url': url,
                        'total_jobs_found': len(job_grid_elements),
                        'total_stored': total_stored,
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
    if base_url == "https://alfred.com.mt/jobs?cat=":
        total_stored = 0
        total_skipped_jobs = 0
        total_jobs_found = 0
        data = {
            "is_success": False,
            'url': base_url,
            'category_slug': category_slug,
        }
        driver.get(base_url + category_slug)
        last_height = driver.execute_script("return document.body.scrollHeight")
        job__link = set()
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        page_source = BeautifulSoup(driver.page_source, features="html.parser")
        job_grid_elements = page_source.find_all("div", class_='hidden sm:block')
        job_grid_elements = job_grid_elements[1:]
        for job_element in job_grid_elements:
            job_link = job_element.find("a", href=True)['href']
            main_link = 'https://alfred.com.mt'
            full_job_link = f"{main_link}{job_link}"
            job__link.add(full_job_link)
            print(len(job__link))
        for job_link in job__link:
            total_stored += 1
            print(f"Scraping job link: {job_link}", "Total Stored: ", total_stored)
            driver.get(job_link)
            time.sleep(2)
            job_page_source = BeautifulSoup(driver.page_source, features="html.parser")
            try:
                job_details_div = job_page_source.find("div", class_="job-details")
                position_name = job_page_source.find("h1", class_="text-md md:text-lg font-bold").get_text(strip=True) if job_page_source.find("h1", class_="text-md md:text-lg font-bold") else "not found"
                job_details_div = job_page_source.find("div", class_="flex flex-col md:flex-row relative")
                left_job_details = job_details_div.find("div", class_="flex-grow md:mr-5 mt-8")
                right_job_details = job_details_div.find("div", class_="flex flex-col w-full md:mt-8 mt-5 md:min-w-[400px] md:max-w-[400px]")
                company_name = left_job_details.find("div", class_="font-semibold text-md sm:text-base").get_text(strip=True) if left_job_details.find("div", class_="font-semibold text-md sm:text-base") else "not found"
                job_description_element =  driver.find_element(By.CLASS_NAME, "HtmlDescription_content__9msWY")
                job_description = job_description_element.text
                job_description = job_description.replace('\n', ' ')
                job_posting_date_div = right_job_details.find("div", class_="flex justify-between")
                job_posting_date_data = job_posting_date_div.find_all("span")[1]
                job_posting_date = job_posting_date_data.get_text(strip=True) if job_posting_date_data else "not found"
                job_location_element = right_job_details.find_all("div", class_="mt-5")[1]
                if job_location_element:
                    job_location_data = job_location_element.find_all("div", class_="flex items-center")[1].get_text(strip=True) if job_location_element.find_all("div", class_="flex items-center")[1] else "not found"
                    job_location = job_location_data if job_location_data else "not found"
                else:
                    job_location = "not found"
                job_category = Category.objects.get(slug=category_slug).name
                job_type_element = right_job_details.find_all("div", class_="mt-5")[2]
                if job_type_element:
                    job_type_data = job_type_element.find("button").get_text(strip=True)
                    job_type = job_type_data if job_type_data else "not found"
                else:
                    job_type = "not found"
                source = "Alfred.com.mt"
                if not Job.objects.filter(position=position_name, company=company_name, location=job_location, user=request.user).exists():
                    scraped_data = Job(position=position_name, company=company_name, location=job_location, description=job_description, job_posted=job_posting_date, job_link=job_link, source=source, job_category=job_category, user=request.user, job_type=job_type)
                    scraped_data.save()
                else:
                    total_skipped_jobs += 1
                    continue
            except Exception as e:
                print(f"{e}")
                continue
        data = {
            "is_success": True,
            'url': base_url,
            'total_jobs_found': len(job__link),
            'total_stored': total_stored,
            'total_skipped_jobs': total_skipped_jobs
        }
        return data
    if base_url == "https://poslovi.infostud.com/":
        total_stored = 0
        total_skipped_jobs = 0
        total_jobs_found = 0
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
                    url = f"{base_url}{category_slug}&page={page_number}"
                driver.get(url)
                page_source = BeautifulSoup(driver.page_source, features="html.parser")
                # job_grid_elements = page_source.find_all("div", class_='uk-margin-bottom')
                job_grid_elements = page_source.find_all("div", id=lambda x: x and x.startswith('oglas_'))
                if not job_grid_elements:
                    print(f"No job elements found on page {page_number}.")
                    break
                total_jobs_found += len(job_grid_elements)
                for job_element in job_grid_elements:
                    job_link_temp = job_element.find("a", href=True)['href']
                    job_link = f"https://poslovi.infostud.com{job_link_temp}"
                    driver.get(job_link)
                    job_page_source = BeautifulSoup(driver.page_source, features="html.parser")
                    header_div = job_page_source.find("div", class_="ogl-header__desc")
                    if header_div:
                        job_title = header_div.find("h1").get_text(strip=True) if header_div.find("h1") else "not found"
                        company_name = header_div.find("h2").get_text(strip=True) if header_div.find("h2") else "not found"
                        job_location = header_div.find("div" , class_="job__location" ).get_text(strip=True) if header_div.find("p") else "not found"
                        job_posting_date = header_div.find('p', class_='uk-margin-remove-top uk-flex uk-flex-row uk-flex-middle')
                        if job_posting_date:
                            job_posting_date = job_posting_date.get_text(strip=True)
                        else:
                            job_posting_date = "not found"
                        category_name = Category.objects.get(slug=category_slug).name
                        job_type = header_div.find("div", class_="job__tags ").find("span")[1].get_text(strip=True) if header_div.find("div", class_="job__tags ") else "not found"
                        salary = header_div.find("div", class_="job__tags ").find("span")[0].get_text(strip=True) if header_div.find("div", class_="job__tags ") else "not found"
                        phone_number = None
                        job__link = job_link
                    else:
                        job_title = "not found"
                        company_name = "not found"
                    description_div = job_page_source.find("div", id="__fastedit_html_oglas")
                    if description_div:
                        job_description = description_div.get_text(strip=True)
                    else:
                        job_description = "not found"
                    website = None
                    source = "poslovi.infostud.com"
                    if not Job.objects.filter(position=job_title, company=company_name, location=job_location, user=request.user).exists():
                        scraped_data = Job(
                            position=job_title, 
                            company=company_name, 
                            location=job_location, 
                            description=job_description, 
                            job_posted=job_posting_date, 
                            job_link=job__link, source=source, 
                            job_category=category_name, 
                            user=request.user, 
                            phone_number=phone_number, 
                            salary=salary, website=website
                            )
                        scraped_data.save()
                        total_stored += 1
                    else:
                        total_skipped_jobs += 1
                data = {
                    "is_success": True,
                    'url': url,
                    'total_jobs_found': total_jobs_found,
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
    if base_url == "https://www.halooglasi.com/posao/":
        total_stored = 0
        total_skipped_jobs = 0
        total_jobs_found = 0
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
                    url = f"{base_url}{category_slug}?page={page_number}"
                driver.get(url)
                page_source = BeautifulSoup(driver.page_source, features="html.parser")
                job_grid_elements = page_source.find_all("div", class_='col-md-12 col-sm-12 col-xs-12 col-lg-12')
                if not job_grid_elements:
                    print(f"No job elements found on page {page_number}.")
                    break
                for job_element in job_grid_elements:
                    total_jobs_found += 1
                    job_title = job_element.find("h3", class_="courses-title").get_text(strip=True) if job_element.find("h3", class_="courses-title") else "not found"
                    job_link_id = job_element.find("a", href=True)['href']
                    job_link = f"https://www.halooglasi.com{job_link_id}"

                    # Make an Click Event for show show-phone-span find the phone-div and click it

                    driver.get(job_link)
                    try:
                        show_phone_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CLASS_NAME, "show-phone-span"))
                        )
                        show_phone_button.click()
                        time.sleep(2)
                    except Exception as e:
                        print("Show phone button not found.")
                    job_page_source = BeautifulSoup(driver.page_source, features="html.parser")
                    right_job_details = job_page_source.find("div", class_="col-md-12")
                    left_job_details = job_page_source.find("div", class_="sidebar-info-box")
                    company_name = right_job_details.find("div", id="plh20").get_text(strip=True) if right_job_details.find("div", id="plh20") else "not found"
                    position_name = job_title  
                    category_name = Category.objects.get(slug=category_slug).name
                    job_posting_date = left_job_details.find("strong", id="plh42").get_text(strip=True) if left_job_details.find("strong", id="plh42") else "not found"
                    employers_demands = right_job_details.find("table", class_="employers-demands")
                    if employers_demands:
                        salary = employers_demands.find(text=re.compile(r'Plata')).find_next('span').get_text(strip=True) if employers_demands.find(text=re.compile(r'Plata')) else "not found"
                        job_location = employers_demands.find(text=re.compile(r'Grad')).find_next('span').get_text(strip=True) if employers_demands.find(text=re.compile(r'Grad')) else "not found"
                        job_type = employers_demands.find(text=re.compile(r'Radno vreme')).find_next('span').get_text(strip=True) if employers_demands.find(text=re.compile(r'Radno vreme')) else "not found"
                    phone_number_element = right_job_details.find("div", class_="contact-info")
                    if phone_number_element:
                        phone_number_td = phone_number_element.find("td", id="plh24")
                        if phone_number_td:
                            phone_number_link = phone_number_td.find("a", class_="phone-number-link")
                            phone_number = phone_number_link.get_text(strip=True) if phone_number_link else "not found"
                        else:
                            phone_number = "not found"
                    else:
                        phone_number = "not found"
                    job_link = job_link
                    job_description_div = right_job_details.find("div", id="divAdditionalDescriptionGroup")
                    if job_description_div:
                        job_description = job_description_div.find("span", id="plh14").get_text(strip=True, separator=" ") if job_description_div.find("span", id="plh14") else "not found"
                    else:
                        job_description = "not found"
                    website_link = None
                    source = "HaloOglasi.com"
                    if not Job.objects.filter(position=position_name, company=company_name, user=request.user).exists():
                        scraped_data = Job(
                            position=position_name, 
                            company=company_name, 
                            location=job_location,
                            description=job_description, 
                            job_posted=job_posting_date, 
                            job_link=job_link, 
                            source=source, 
                            job_type=job_type,
                            job_category=category_name, 
                            user=request.user, 
                            phone_number=phone_number, 
                            salary=salary, 
                            website=website_link
                            )
                        scraped_data.save()
                        total_stored += 1
                        print(f"Job stored: {position_name}")
                    else:
                        total_skipped_jobs += 1
                data = {
                    "is_success": True,
                    'url': url,
                    'total_jobs_found': total_jobs_found,
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

@login_required(login_url='login')
def scrape_job(request):
    requested_user = request.user
    urls = AvilableUrl.objects.filter(users=requested_user)
    selected_url = None 
    categories = Category.objects.none
    max_pages = None
    category_slug = None
    notices = Notice.objects.filter(is_active=True)

    if request.method == 'POST':
        url_id = request.POST.get('url') 
        max_pages = request.POST.get('max_pages')  
        category_slug = request.POST.get('category') 
        if url_id:
            selected_url = get_object_or_404(AvilableUrl, id=url_id)
            categories = selected_url.category.filter(users=requested_user)
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
                        'total_skipped_jobs': data['total_skipped_jobs'],
                    })
                else:
                    return JsonResponse({'is_success': False, 'total_skipped_jobs': data['total_skipped_jobs']})
            except ValueError:
                return JsonResponse({'is_success': False, 'error': 'Max pages must be a valid number.'})
            except Exception as e:
                return JsonResponse({'is_success': False, 'error': str(e)})

    return render(request, 'store_job.html', {'urls': urls, 'selected_url': selected_url, 'categories': categories, 'max_pages': max_pages, 'category_slug': category_slug, 'notices': notices})

@login_required(login_url='login')  
def view_scraped_data(request):
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
# 
@login_required(login_url='login')
def home(request):
    return render(request, 'home.html')
def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('home') 
        else:
            messages.error(request, 'Invalid username or password')
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')

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

@login_required
def confirm_delete_jobs(request):
    job_count = Job.objects.filter(user=request.user).count()
    if request.method == "POST":
        if job_count > 0:
            Job.objects.filter(user=request.user).delete()
            return redirect('view_scraped_data') 
        else:
            return redirect('view_scraped_data')
    return render(request, 'confirm_delete_job.html', {'job_count': job_count})

