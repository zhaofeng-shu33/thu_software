# download resources
import pdb
import argparse
import logging
from datetime import datetime
import re
import json
import os

import requests
from bs4 import BeautifulSoup
import progressbar

logging.basicConfig(filename='log.txt', level=logging.INFO, format='%(asctime)s %(message)s')
CHUNK_SIZE = 8192
URL_ROOT = 'https://sslvpn.tsinghua.edu.cn'
HOME_URL = 'https://sslvpn.tsinghua.edu.cn/dana/home/index.cgi'
URL_AUTH_ROOT = 'https://sslvpn.tsinghua.edu.cn/dana-na/auth/url_default'
LOGOUT_URL = 'https://sslvpn.tsinghua.edu.cn/dana-na/auth/logout.cgi?delivery=psal'
DOWNLOAD_ROOT = 'https://sslvpn.tsinghua.edu.cn/info/czxt/,DanaInfo=its.tsinghua.edu.cn+'
VERBOSE = False
VERBOSE_FILE = 'verbose.txt'
SAVE_PATH = './'
RE_AUTH_SIZE = 1024*1024*1024 # 1GB
STUDENT_ID = ''
PASSWORD = ''
def get_home(session):
    r = session.get(HOME_URL, verify=False)
    if(r.status_code == 200):
        if(VERBOSE):
            open(VERBOSE_FILE, 'wb+').write(r.text.encode('utf-8'))
        logging.info(r.url)
        if(r.text.find('Invalid username')>0):
            logging.info('fail login, unknown reason')
            return False
        if(r.text.find('Preference')>0):
            return True
    return False    
    
def process_to_start(session, html):
    # this is an auto delivered form
    soup = BeautifulSoup(html)
    auth_url_next =soup.find('form').get('action')
    auth_url_next_full = URL_ROOT + auth_url_next
    dic = {}
    for input in soup.find_all('input'):
        name = input.get('name')
        value = input.get('value')
        if(value is None):
            value = ''
        dic[name] = value
    if(dic.get('clienttime')==''):
        current_timestamp = str(int(datetime.timestamp(datetime.now())/1000))
        logging.info('set client time ' + current_timestamp)       
        dic['clienttime'] = current_timestamp
    r = session.post(auth_url_next_full, verify=False, data=dic)  
    if(r.status_code == 200):
        if(VERBOSE):
            open(VERBOSE_FILE, 'wb+').write(r.text.encode('utf-8'))
        logging.info(r.url)
        if(r.text.find('Invalid username')>0):
            logging.info('fail login, unknown reason')
            return False
        if(r.text.find('index.cgi')>0):
            return get_home(session)
        if(r.text.find('Preference')>0):
            return True
    return False    

def confirm_login(session, html):
    dic={"btnContinue" : "Continue the session"}
    soup = BeautifulSoup(html)
    a = soup.find('input',type="hidden")
    dic['FormDataStr'] = a.get('value')
    r = session.post(URL_AUTH_ROOT + '/login.cgi', verify=False, data=dic)    
    if(r.status_code == 200):
        if(VERBOSE):
            open(VERBOSE_FILE, 'wb+').write(r.text.encode('utf-8'))
        if(r.text.find('Invalid username')>0):
            logging.info('fail login, account suspended for a while')
            return False
        if(r.text.find('Please wait')>0):
            logging.info('process_to_start')
            return process_to_start(session, r.text)
        if(r.text.find('Preference')>0):
            return True
    return False    
    
def login(session, username, userpass):
    dic = {"username":username, "password":userpass, "realm":"ldap"}
    r = session.post(URL_AUTH_ROOT + '/login.cgi', verify=False, data=dic)
    # handle welcome cgi
    if(r.status_code == 200):
        if(VERBOSE):
            open(VERBOSE_FILE, 'wb+').write(r.text.encode('utf-8'))
        if(r.text.find('Invalid username')>0):
            return False
        if(r.text.find('Please wait')>0):
            logging.info('process_to_start')            
            return process_to_start(session, r.text)            
        if(r.text.find('index.cgi')>0):
            return get_home(session)            
        if(r.text.find('Last Access Time')>0):
            return confirm_login(session, r.text)            
        if(r.text.find('Preference')>0):
            return True
    return False

def get_download_url(html):
    m = re.search('http://(.*)\',0', html)
    if(m is None):
        return False
    url = m.group(1)
    first_part, second_part = url.split('?')
    url_pieces = first_part.split('/')
    file_name = url_pieces[-1]
    url_pieces[-1] = ',DanaInfo=' + url_pieces[0]
    url_pieces[0] = URL_ROOT
    full_url = '/'.join(url_pieces) + '+' + file_name + '?' + second_part
    return full_url
    
def download(session, file_id):
    r = session.get(DOWNLOAD_ROOT + str(file_id), verify=False)
    if r.status_code == 200:
        if(VERBOSE):
            open(VERBOSE_FILE, 'wb+').write(r.text.encode('utf-8'))
        full_url = get_download_url(r.text)
        logging.info(full_url)
        return download_file(session, full_url)
    return False;

def logout(session):
    r = session.get(LOGOUT_URL, verify=False)
    if(r.status_code == 200 and r.text.find('has ended')>0):
        return True
    else:
        return False


def str_to_dic(cookie_string):
    cookie_dic = {}
    for i in cookie_string.split(';'):
        k,v = i.split('=')
        cookie_dic[k.strip()] = v.strip()
    return cookie_dic

def download_inner(r, f, bar, current_size_start=0):
    '''
        r: response
        f: file
        bar: progress bar
    '''
    current_size_inner = current_size_start
    for chunk in r.iter_content(chunk_size=CHUNK_SIZE): 
        if chunk: # filter out keep-alive new chunks
            f.write(chunk)
            current_size_inner += len(chunk)
            bar.update(current_size_inner)
    return current_size_inner
    
def download_file(session, url):
    local_filename = url.split('?')[0].split('/')[-1].split('+')[-1]
    # NOTE the stream=True parameter below
    # if the file is larger than 2GB, use range.
    file_path = os.path.join(SAVE_PATH, local_filename)
    r = session.get(url, stream=True, verify=False)
    r.raise_for_status() # raise Error if 404
    size = int(r.headers.get('Content-Length'))
    bar = progressbar.ProgressBar(max_value=size)
    if(size <= RE_AUTH_SIZE):    
        with open(file_path, 'wb') as f:
            download_inner(r, f, bar)
    else:
        # check if the file exists
        start_size = 0
        if(os.path.exists(file_path)):
            start_size = os.path.getsize(file_path)
        current_size = start_size
        with open(file_path, 'ba') as f:
            new_status = 'incomplete'
            max_size = current_size + RE_AUTH_SIZE
            if(max_size > size):
                max_size = size
                new_status = 'complete'
            byte_range = 'bytes=%d-%d' %(current_size, max_size)
            r = session.get(url, stream=True, verify=False, headers={'Range': byte_range})
            if(VERBOSE):
                print(r.status_code)
                print(r.headers)
                logging.info('content-range' + r.headers['Content-Range'])
            new_current_size = download_inner(r, f, bar, current_size_start=current_size)
            current_size = new_current_size
            logging.info('download ' + local_filename + ' %d/%d'%(current_size, size))            
            return new_status
    return 'complete'

def download_main(file_id):
    session = requests.Session()
    isLogin = login(session, STUDENT_ID, PASSWORD)
    if not(isLogin):
        return 'login failed'
    isDownload = False
    try:
        isDownload = download(session, file_id)
    except Exception as e:
        logging.error(str(e))
    isLogout = logout(session) 
    if not(isLogout):
        return 'logout failed'
    return isDownload  

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--student_id', default='123')
    parser.add_argument('--password', default='abc')
    parser.add_argument('--file_id', default=1663, type=int)
    parser.add_argument('--verbose', default=False, type=bool, nargs='?', const=True, help='whether to save verbose info')    
    parser.add_argument('--save_path', default='./', help='download file save path')
    parser.add_argument('--debug', default=False, type=bool, nargs='?', const=True, help='whether to enter debug mode')
    parser.add_argument('--auth_limit', default=1024*1024*1024, type=int, help='logout and login download limit')
    args = parser.parse_args()   
    VERBOSE = args.verbose    
    SAVE_PATH = args.save_path
    if(args.debug):
        pdb.set_trace()
    RE_AUTH_SIZE = args.auth_limit
    STUDENT_ID = args.student_id
    PASSWORD = args.password
    status = 'incomplete'
    while(status == 'incomplete'):
        status = download_main(args.file_id)
    print(status)
