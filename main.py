# coding=utf-8

import copy
import os
import time
from functools import partial

import concurrent.futures
import m3u8
import requests
import urllib.request
from Crypto.Cipher import AES
from bs4 import BeautifulSoup

url, videoName, videoCachePath = input('url such as https://jable.tv/videos/example/ : '), '', ''


def parseM3u8File(m3u8HeadUrl, m3u8DownloadUrl):
    global videoName, videoCachePath
    # download
    m3u8file = videoCachePath + '/' + videoName + '.m3u8'
    urllib.request.urlretrieve(m3u8HeadUrl, m3u8file)
    # parse
    m3u8Obj, m3u8Uri, m3u8Iv = m3u8.load(m3u8file), '', ''
    for key in m3u8Obj.keys:
        if key:
            m3u8Uri = key.uri
            m3u8Iv = key.iv
    tsList = []
    for seg in m3u8Obj.segments:
        tsUrl = m3u8DownloadUrl + '/' + seg.uri
        tsList.append(tsUrl)
    # make ci
    if m3u8Uri:
        httpHeaders = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36', }
        response = requests.get(m3u8DownloadUrl + '/' + m3u8Uri, headers=httpHeaders, timeout=10)
        vt = m3u8Iv.replace("0x", "")[:16].encode()
        ci = AES.new(response.content, AES.MODE_CBC, vt)  # 建構解碼器
    else:
        ci = ''
    return tsList, ci


def parseVideoUrl():
    global url, videoName, videoCachePath
    # Get video name and the cache path
    videoName = url.split('/')[-2]
    if not os.path.exists(videoName):
        os.makedirs(videoName)
    videoCachePath = os.getcwd() + '/' + videoName
    # Get m3u8 head and download url
    soup = BeautifulSoup(requests.get(url).text, 'lxml')
    hrefList = []
    for link in soup.find_all('link'):
        hrefList.append(link.get('href'))
    m3u8HeadUrl = hrefList[-1]
    m3u8urlList = m3u8HeadUrl.split('/')
    m3u8urlList.pop(-1)
    m3u8DownloadUrl = '/'.join(m3u8urlList)
    return m3u8HeadUrl, m3u8DownloadUrl


def doCrawler(ci, tsList, videoCachePath):
    start_time = time.time()
    downloadList = copy.deepcopy(tsList)
    print('begin download: ' + str(len(downloadList)))
    print('wait: {0:.2f} mins'.format(len(downloadList) / 150))

    def scrape(ci, videoCachePath, downloadList, urls):
        httpHeaders = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36', }
        response = requests.get(urls, headers=httpHeaders, timeout=10)
        content_ts = response.content
        fileName = urls.split('/')[-1][0:-3]
        with open(videoCachePath + "/" + fileName + ".mp4", 'ab') as f:
            if ci:
                f.write(ci.decrypt(content_ts))
            else:
                f.write(content_ts)
            print('processing: {0} , {1} left'.format(urls.split('/')[-1], len(downloadList)))
            downloadList.remove(urls)
            f.close()

    while (len(downloadList) > 0):
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            executor.map(partial(scrape, ci, videoCachePath, downloadList), downloadList)
    end_time = time.time()
    print('done after {0:.2f} mins'.format((end_time - start_time) / 60))


def mergeMp4s(videoCachePath, tsList):
    start_time = time.time()
    print('start merge:')
    for i in range(len(tsList)):
        sigFile = tsList[i].split('/')[-1][0:-3] + '.mp4'
        sigPath = videoCachePath + '/' + sigFile
        print(sigPath)
        if os.path.exists(sigPath):
            with open(sigPath, 'rb') as f1:
                with open(videoCachePath + '/' + videoCachePath.split('/')[-1] + ".mp4", 'ab') as f2:
                    f2.write(f1.read())
        else:
            print(sigFile + " fail")
    end_time = time.time()
    print('done after {0:.2f} s'.format(end_time - start_time))


def deleteWhenSuccess(videoCachePath, videoName):
    videoFileName = videoName + '.mp4'
    videoFilePath = videoCachePath + '/' + videoFileName
    if os.path.exists(videoFilePath):
        files = os.listdir(videoCachePath)
        for file in files:
            if file != videoFileName:
                os.remove(os.path.join(videoCachePath, file))


m3u8HeadUrl, m3u8DownloadUrl = parseVideoUrl()
tsList, ci = parseM3u8File(m3u8HeadUrl, m3u8DownloadUrl)
doCrawler(ci, tsList, videoCachePath)
mergeMp4s(videoCachePath, tsList)
deleteWhenSuccess(videoCachePath, videoName)
