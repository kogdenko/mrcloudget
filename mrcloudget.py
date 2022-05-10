#!/usr/bin/python

import os
import sys
import time
import getopt
import shutil
import traceback
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import selenium.webdriver.support.ui as ui
from selenium.webdriver.support import expected_conditions as EC

g_verbose = 0
g_download_path = None
g_driver = None
g_downloaded = 0

def list_view(timeout):
    TOOLBAR_CLASS="Toolbar__rightControls--2amHH"
    VIEW_CLASS="Toolbar__item--28MNd"
    try:
        toolbar = ui.WebDriverWait(g_driver, timeout).until(lambda g_driver:
            g_driver.find_element(by=By.CLASS_NAME, value=TOOLBAR_CLASS))
    except selenium.common.exceptions.TimeoutException:
        return False
    view = toolbar.find_element(by=By.CLASS_NAME, value=VIEW_CLASS)
    view.click()
    #view_list=g_driver.find_element(by=By.XPATH, 
    #   value="//div[@class='DropdownList__item--2m8Vq' AND @data-name='viewList']")
    view_list=g_driver.find_element(by=By.XPATH, value="//div[@data-name='viewList']")
    view_list.click()
    return True
 
def is_file(e):
    try:
        e.find_element(by=By.CLASS_NAME, value="DataListItemRow__date--JMvpW")
    except:
        return False
    return True

def do_ls():
    ENTRY_CLASS="DataListItemRow__root--39hIM"
    try:
        wait = ui.WebDriverWait(g_driver, 2)
        return wait.until(lambda g_driver: g_driver.find_elements(by=By.CLASS_NAME, value=ENTRY_CLASS))
    except selenium.common.exceptions.TimeoutException:
        return []

def get_name(e):
    ne = e.find_element(by=By.CLASS_NAME, value="DataListItemRow__name--39Wrn")
    name = ne.text
    if len(name) > 0 and name[0] == '.':
        # Someone (google-chrome or js script) remove '.' at the begin of the file name
        name = name[1:]
    return name.replace('\n', '').replace('\r', '')
#    for character in name:i
#        print(character, character.encode('utf-8').hex())

def center(e):
    g_driver.execute_script("arguments[0].scrollIntoView({'block':'center','inline':'center'})", e)
    ui.WebDriverWait(g_driver, 3).until(EC.element_to_be_clickable(e))

def download_file(e):
    d = e.find_element(by=By.CLASS_NAME, value="DataListItemRow__download--YSHnR")
    center(d)
    d.click()

#class="DropdownList__item--2m8Vq" data-name="newTab"
def open_in_new_tab(e):
    center(e)
    actions = ActionChains(g_driver)
    actions.context_click(e).perform()
    o = ui.WebDriverWait(g_driver, 3).until(lambda g_driver:
        g_driver.find_element(by=By.XPATH, value="//div[@data-name='newTab']"))
    o.click()

def find_downloaded(name):
    entries =  os.listdir(g_download_path)
    for entry in entries:
        if entry.replace(' ', '') == name.replace(' ', ''):
            return entry, entries
    return None, entries

def process_element(dst, path, depth, e):
    center(e)
    download = depth >= len(path)
    name = get_name(e)
    #print("process", name)
    if is_file(e):
        if download:
            dst_file_path = dst + "/" + name
            if os.path.exists(dst_file_path):
                return
            if g_verbose > 0:
                print("downloading", name)
            assert(len(os.listdir(g_download_path)) == 0)
            download_file(e)
            tries = 0
            while True:
                entry, entries = find_downloaded(name)
                tries += 1
                if entry == None:
                    if tries == 1000:
                        if len(entries) == 0:
                            print("Download seems not started, restarting...")
                            download_file(e)
                            tries = 0
                else:
                    src_file_path = g_download_path + "/" + entry
                    if g_verbose > 0:
                        print("downloaded", name)
                    shutil.move(src_file_path, dst_file_path)
                    global g_downloaded
                    g_downloaded += 1
                    break
                time.sleep(0.01)
    else:
        #print(download, path[depth], name)
        if download:
            found = False
        else:
            if path[depth] == name:
                # Find folder in path, do not traverse siblings
                found = True
            else:
                return False
        open_in_new_tab(e)
        g_driver.switch_to.window(g_driver.window_handles[-1])
        traverse(dst + "/" + name, path, depth + 1)
        g_driver.close()
        g_driver.switch_to.window(g_driver.window_handles[-1]) 
        return found
    return False

def process_elements(dst, path, depth):
    name = None
    tries = 0
    while True:
        try:
            tries += 1
            elements = do_ls()
            n = len(elements)
            if n == 0:
                return
            if name == None:
                e = elements[0]
            else:
                e = None
                for i in range(n):
                    if elements[i].text == name:
                        if i == n - 1:
                            return
                        else:
                            e = elements[i + 1]
                            break
                assert(e != None)
            if process_element(dst, path, depth, e):
                return
            name = e.text
            tries = 0
        except selenium.common.exceptions.StaleElementReferenceException:
            print("%s: StaleElementReferenceException" % dst)
            if tries > 10:
                print("Tries exceeded")
                sys.exit(1)
        except:
            print("Internal error")
            print(traceback.format_exc())
            if tries > 3:
                print("Tries exceeded")
                sys.exit(1)
            g_driver.refresh()
            name = None
           
def traverse(dst, path, depth):
    if not os.path.exists(dst):
        os.mkdir(dst)
    if g_verbose > 0:
        print("enter", dst)
    list_view(3)
    process_elements(dst, path, depth)
    if g_verbose > 0:
        print("leave", dst)

def usage():
    print("mrcloudget.py [options] {-D path}")

def main():
    global g_driver
    global g_verbose
    cloud_path = []
    destination_path = None
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hvD:", [
            "help",
            "path=",
            ])
    except getopt.GetoptError as err:
        print(err)
        sys.exit(1)
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit(0)
        if o in ("-v"):
            g_verbose += 1
        if o in ("-D"):
            destination_path = a
        if o in ("--path"):
            cloud_path = a.split('/')

    if destination_path == None:
        usage()
        sys.exit(1)
    destination_path = os.path.abspath(destination_path)
    if not os.path.isdir(destination_path):
        print("Destination path is not a directory")
        sys.exit(1)

    home = os.path.expanduser("~") + "/.mrcloudget"
    global g_download_path
    g_download_path = "%s/downloads" % home

    options = webdriver.ChromeOptions()
    shutil.rmtree(g_download_path, True)
    os.mkdir(g_download_path)
    options.add_argument("user-data-dir=%s/google-chrome" % home)
    options.add_argument("--start-maximized")
    prefs = {"download.default_directory" : g_download_path }
    options.add_experimental_option("prefs", prefs)
    g_driver = webdriver.Chrome(options=options)
    g_driver.get("http://cloud.mail.ru")

    if list_view(120):
        if g_verbose > 0:
            print("Logined")
    else:
        print("Login timeout expired")
        sys.exit(1)
    if g_verbose > 0:
        print("Changed to list view")
    try:
        traverse(destination_path, cloud_path, 0)
    except:
        print("Internal error")
        print(traceback.format_exc())
        #g_driver.quit()
        sys.exit(1)
    g_driver.quit()
    print("Done")
    print("Downloaded", g_downloaded, "files")
    sys.exit(0)

main()
