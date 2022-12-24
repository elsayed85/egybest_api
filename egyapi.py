from ast import literal_eval
import enum
from numexpr import evaluate
from enum import Enum
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from flask import Flask
from flask import jsonify
from flask import request


import threading
import traceback
import requests
import argparse
import base64
import pickle
import time
import sys
import re
import os


class TYPES(Enum):
    episode = 'episode'
    masrahiya = 'masrahiya'
    season = 'season'
    series = 'series'
    movie = 'movie'
    anime = 'anime'
    show = 'show'
    wwe = 'wwe-show'


class EgyGrab():
    def __init__(self, url):
        self.dl_url = self.url = url
        base_url = urlparse(url)
        self.base_url = '{uri.scheme}://{uri.netloc}'.format(uri=base_url)
        self.type = None
        for t in TYPES:
            if '/%s/' % t.value in url:
                self.type = TYPES[t.name]
                break
        if self.type is None:
            raise ValueError('There is nothing to download :(')
        self.threads = []
        self.results = []

    def grab(self, quality='1080p', cookies=True):
        if self.type in [TYPES.episode, TYPES.masrahiya, TYPES.movie]:
            return [self.__grab_item(self.url, quality, cookies)[1]]

        urls = [self.url]
        if self.type in [TYPES.series, TYPES.anime, TYPES.wwe, TYPES.show]:
            html = requests.get(self.url).text
            urls = reversed([self.base_url + match[1]
                            for match in re.finditer(r'(\/season\/.+?)"', html)])

        self.threads = []
        self.results = []
        grabbed = []
        for url in urls:
            season_results = []
            i = 0
            html = requests.get(url)
            html = html.text
            for match in re.finditer(r'(\/episode\/.+?)"', html):
                t = threading.Thread(target=lambda: season_results.append(
                    self.__grab_item(self.base_url + match[1], quality, cookies, i)))
                i += 1
                t.start()
                self.threads.append(t)
            for t in self.threads:
                t.join()

            self.results += sorted(season_results,
                                   key=lambda x: x[0], reverse=True)
            # grabbed.append(re.search(r'.+?\/season\/(.+?)(\/|$)', url)[1])

        return [v for _, v in self.results]

    def __grab_item(self, url, quality='1080p', last_session=True, id=0):
        try:
            sess = requests.Session()
            sess.headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36',
            }

            cookiesPath = 'cookies/cookies_%s.pickle' % str(id)
            if os.path.exists(cookiesPath) and last_session:
                sess.cookies = pickle.load(open(cookiesPath, 'rb'))

            html = sess.get(url).text
            main_html = html
            # open('test.html', 'w', encoding='utf-8').write(html)
            # html = open('html.txt', encoding='utf-8').read()
            # print('item page loaded!')

            # print(html)
            html = html.replace("'+'", '')
            # call = 'https://mila.egybest.ninja/api?call='+re.search(r'rel="#yt_trailer".+?data-call="(.+?)"', html)[1]
            qualities = ['240p', '480p', '720p', '1080p']
            permitted = False
            code = None
            while not code and len(qualities):
                q = qualities.pop()
                if not permitted:
                    permitted = q == quality
                if permitted:
                    code = re.search(
                        q + r'.+?"(/api\?call=.+?)"><i class="i-dl">', html)
            if not code:
                print('%s no link was available' % url)
                return (id, '')
            code = code[1]
            # watch = 'https://mila.egybest.ninja'+re.search(r'<iframe.+?src="(.+?)"', html)[1]
            name = re.search(
                r"([a-z0-9]+)={'url':[^,]+?\+([a-z0-9]{3,}),", html, re.I)
            data = re.search(
                r"([a-z0-9]{3,})\['forEach'].+?%s\+=([a-z0-9]+?)\[.+?]" % name[2], html, re.I)
            for val in re.finditer(r"%s\['data'\]\['([^']+?)'\]='([^']+?)'" % name[1], html):
                pass
            a, b = data[1], data[2]

            data = {a: {}, b: {}}
            for arrName in data.keys():
                for p in re.finditer(r"%s\[([^\]]+?)]='(.+?)'[,;]" % arrName, html, re.I):
                    k = p[1][1:-1] if p[1][0] == "'" else int(evaluate(p[1]))
                    data[arrName][k] = p[2]

            l = data[a]
            data[a] = []
            for i in range(len(l)):
                data[a].append(l[i])

            vidstream = sess.get(self.base_url+code,
                                 allow_redirects=False).headers['location']
            app.logger.info(vidstream)

            if vidstream[:2] == '/?':
                verification = self.base_url + '/api?call=' + \
                    (''.join([data[b][v] for v in data[a] if v in data[b]]))
                click = self.base_url + '/' + \
                    base64.b64decode(
                        re.search(r"=\['([^']+?)'\]", html)[1] + '===').decode('utf8')
                res = sess.get(click).text
                # args = re.search(
                #     r'\("(.+?)",(\d+),"(.+?)",(\d+),(\d+),(\d+)\)', res)
                # cipher, _, key, offset, base, _ = args.groups()
                # base = int(base)
                # offset = int(offset)
                # cipher = cipher.split(key[base])
                # cipher = [c.translate(c.maketrans(key, ''.join(
                #     [str(i) for i in range(len(key))]))) for c in cipher]
                # cipher = [chr(int(c, base) - offset) for c in cipher if c]
                # print(sess.cookies)
                # c_name, c_value = tuple(re.search(r'cookie="(.+?);', ''.join(cipher))[1].split('='))
                # sess.cookies.set(c_name, c_value)
                time.sleep(1)
                mm = sess.post(verification, data={val[1]: val[2]})

                vidstream = sess.get(
                    self.base_url +code, allow_redirects=False).headers['location']
                # sess.cookies.pop(c_name)
            else:
                # print('vidstream link grabbed using cookies')
                pass

            app.logger.info(re.search(r'vidstream.+?\/f\/.+?\/', vidstream))
            # vidstream = 'https://mila.egybest.ninja/vs-mirror/vidstream.to/f/YvD0EpU8nU'
            vidstream2 = vidstream
            vidstream = self.base_url + '/vs-mirror/' + re.search(r'vidstream.+?\/f\/.+?\/', vidstream)[0]
            app.logger.info(vidstream2)

            # print(vidstream)
            html = sess.get(vidstream).text
            # print(html)
            # html = open('html.txt', encoding='utf-8').read()
            if not re.search('<a href="(h.+?)" class="bigbutton"', html):
                a0c = literal_eval(re.search(r'var \w=(\[.+?\]);', html)[1])
                a0d_offset = re.search(
                    r'return a0d=function\(d,e\)\{d=d-([^;]+?);', html)[1]

                def a0d(a):
                    a = int(a, 16)-int(a0d_offset, 16)
                    return a0c[a]

                parameters = re.search(
                    r"function\(a,b\)\{var .=a0d.+?;while\(!!\[\]\)\{try\{var .=([^;]+?);[^,]+?\(a0c,([^)].+?)\)", html)
                limit = int(parameters[2], 16)
                c = 0
                while True:
                    step = parameters[1]
                    for match in re.finditer(r'parseInt\(.\(([^)]+?)\)\)', parameters[0]):
                        step = step.replace(match[0], str(
                            int((re.search(r'\d+', a0d(match[1])) or [0])[0])))
                    c = evaluate(step)
                    if c == limit:
                        break

                    a0c.append(a0c.pop(0))

                token = re.search(r",[^,]+?=\[a0[a-zA-Z]\((.+?)\)", html)
                if token:
                    token = a0d(token[1])
                else:
                    token = re.search(r",[^,]+?=\['([^']+?)'\]", html)[1]

                arrNames = re.search(r'\+=(_.+?)\[(.+?)\[.+?\]\]\|\|''', html)

                values = {}
                arrName = arrNames[1]
                for match in re.finditer(r"%s\['([^'()]+?)'\]='([^']+?)'" % arrName, html):
                    values[match[1]] = match[2]
                for match in re.finditer(r"%s\['([^'()]+?)'\]=a0.\(([^)]+?)\)" % arrName, html):
                    values[match[1]] = a0d(match[2])
                for match in re.finditer(r"%s\[a0.\(([^)]+?)\)\]='([^']+?)'" % arrName, html):
                    values[a0d(match[1])] = match[2]
                for match in re.finditer(r"%s\[a0.\(([^)]+?)\)\]=a0.\(([^)]+?)\)" % arrName, html):
                    values[a0d(match[1])] = a0d(match[2])

                keys = {}
                arrName = arrNames[2]
                for match in re.finditer(r"%s\[([^=()]+?)\]='([^'].+?)'" % arrName, html):
                    keys[int(match[1], 16)] = match[2]
                for match in re.finditer(r"%s\[([^=()]+?)\]=a0.\(([^)].+?)\)" % arrName, html):
                    keys[int(match[1], 16)] = a0d(match[2])

                # print(token)
                app.logger.info(token + "===")
                sess.get(self.base_url + '/' +
                         base64.b64decode(token + '===').decode('utf8'))
                verification = ''.join(
                    [values[keys[i]] for i in range(len(keys)) if keys[i] in values])
                # time.sleep(.2)
                sess.post(self.base_url + '/tvc.php?verify='+verification,
                          data={re.search(r"'([^']+?)':'ok'", html)[1]: 'ok'})
                html = sess.get(vidstream).text
            else:
                # print('download link grabbed using cookies')
                pass
            if not os.path.exists('cookies'):
                os.mkdir('cookies')
            pickle.dump(sess.cookies, open(cookiesPath, 'wb'))

            doc = BeautifulSoup(main_html, 'html.parser')
            main = doc.find('div','full_movie')
            cover = main.find('div', 'movie_img').find('img')['src']
            title = main.find('td', 'movie_title').find('h1').text

            # return (id , re.search('<a href="(h.+?)" class="bigbutton"', html)[1])
            download_url = re.search('<a href="(h.+?)" class="bigbutton"', html)[1]
            watch_url = download_url.replace('/dl/', '/watch/')
            return (id, {
                'title': title,
                'cover': cover,
                'quilty' : quality,
                'watch_url': watch_url,
                'download_url': download_url + "/[Elsayed Kamal]" + title.replace(' ', '.') + ".mp4"
            })
        except Exception as e:
            # traceback.print_exc()
            app.logger.info("retry")
            return self.__grab_item(url, quality, last_session, id)


app = Flask(__name__)


@app.route('/main', methods=['GET', 'POST'])
def main():
    data = request.form
    url = data['url']
    q = data['q']
    c = data['c']
    grabber = EgyGrab(url)
    type_name = grabber.type.name
    return jsonify(grabber.grab(q))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1234, debug=True)
