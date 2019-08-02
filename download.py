# download resources
import pdb
import argparse
import requests
from bs4 import BeautifulSoup

URL_AUTH_ROOT = 'https://sslvpn.tsinghua.edu.cn/dana-na/auth/url_default'
DOWNLOAD_URL = 'https://sslvpn.tsinghua.edu.cn/software/thcic_microsoft/office/2016/,DanaInfo=166.111.5.8+Office_Professional_Plus_2016_64Bit_English.ISO?st=PJlK0wDOujm8ThNY7bxSAg&e=1564760579&filename=Active_office2010.exe'

def login(session, username, userpass):
    r = session.get(URL_AUTH_ROOT + '/login.cgi', verify=False)
    # handle welcome cgi
    if(r.status_code == 200):
        
def download(session, file_id):
    r = session.get(DOWNLOAD_ROOT + file_id, stream=True)
    if r.status_code == 200:
        pass

def logout(session):
    return

def str_to_dic(cookie_string):
    cookie_dic = {}
    for i in cookie_string.split(';'):
        k,v = i.split('=')
        cookie_dic[k.strip()] = v.strip()
    return cookie_dic

def download_file(session, url, cookies={}):
    local_filename = url.split('?')[0].split('/')[-1]
    # NOTE the stream=True parameter below
    with session.get(url, stream=True, verify=False, cookies=cookies) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)
                    # f.flush()
    return local_filename        
    
if __name__ == '__main__':
    session = requests.Session()
    parser = argparse.ArgumentParser()
    parser.add_argument('--student_id', default='123')
    parser.add_argument('--password', default='abc')
    parser.add_argument('--debug', default=False, type=bool, nargs='?', const=True, help='whether to enter debug mode')
    args = parser.parse_args()    
    if(args.debug):
        pdb.set_trace()    
    login(session, args.student_id, args.password)
    download(session, DOWNLOAD_URL)    