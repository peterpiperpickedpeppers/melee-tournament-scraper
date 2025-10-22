# -*- coding: utf-8 -*-
"""
@author: peterpiperpickedpeppers
Description: Helpers for common Selenium interactions.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def accept_cookies(driver):
    try:
        cookie_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/div[2]/div[1]/div[2]/button[1]'))
        )
        cookie_button.click()
        print("Cookies accepted!")
    except:
        print("No cookies popup found.")
        
def scroll_page(driver, target=None, pixels=None):
    if target:
        # Scroll element into view
        driver.execute_script("arguments[0].scrollIntoView(true);", target)
    elif pixels is not None:
        # Scroll by a number of pixels
        driver.execute_script(f'window.scrollBy(0, {pixels});')
    else:
        raise ValueError("Provide either 'target' element or 'pixels' to scroll.")


def wait_for_element(driver, xpath, timeout=10, clickable=False, multiple=False):
    if multiple:
        condition = EC.presence_of_all_elements_located((By.XPATH, xpath))
    elif clickable:
        condition = EC.element_to_be_clickable((By.XPATH, xpath))
    else:
        condition = EC.presence_of_element_located((By.XPATH, xpath))

    return WebDriverWait(driver, timeout).until(condition)

def click_element(driver, xpath, timeout=10):
    """
    Waits for an element, scrolls it into view, and then clicks it.
    
    Args:
        driver: Selenium Webdriver instance.
        xpath (str): the XPath of the element to click.
        timeout (int, optional): time to wait for the element to be clickable. Default is 10.
    """
    element = wait_for_element(driver, xpath, timeout=timeout, clickable=True)
    scroll_page(driver, target=element)
    driver.execute_script("arguments[0].click();", element)
