# -*- coding: utf-8 -*-
"""
@author: peterpiperpickedpeppers
Description: Manages Chrome browser setup and navigation.
"""
from selenium import webdriver
import chromedriver_autoinstaller
from selenium.webdriver.chrome.service import Service

class BrowserManager:
    def __init__(self, url):
        self.url = url
        self.driver = None
        
        # ensure chromedriver is installed and gets its path
        try:
            self.driver_path = chromedriver_autoinstaller.install()
        except Exception as e:
            print(f"Error installing Chromedriver: {e}")
            self.driver_path = None
            
    def open_browser(self):
        """Opens Chrome browser with given settings and loads the url."""
        if self.driver is None:
            options = webdriver.ChromeOptions()
            options.add_argument("start-maximized")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("disable-infobars")
            options.add_argument("disable-popup-blocking")
            options.add_argument("disable-extensions")
            
            # user agent to mimic real broswer
            user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
            )
            options.add_argument(f"user-agent={user_agent}")
            
            # start chromedriver with explicitly installed path
            if self.driver_path:
                service = Service(self.driver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
                self.driver.get(self.url)
            
            else:
                raise RuntimeError("ChromeDriver installation failed. Check logs.")
        return self.driver
    
    def close_browser(self):
        """Closes the browser instance if open."""
        if self.driver:
            self.driver.quit()
            self.driver = None
