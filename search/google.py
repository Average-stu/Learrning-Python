from selenium import webdriver
import sys

def convert(s):
    str =''
    return (str.join(s))

search_string = sys.argv[1:]

search_string = convert(search_string)

search_string =search_string.replace(' ', '+')

browser = webdriver.Chrome()

for i in range(1):
    matched_element = browser.get("https://www.google.com/search?q="
                                  + search_string + "&start="+ str(i))
