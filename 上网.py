import math
import json
import time
import random
import socket
import hashlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple, Iterable, Callable, Dict

import requests
import tldextract
from tqdm import tqdm

import 分析
import 信息
from 文 import 缩, 摘要
from 存储 import 融合之门
from 网站 import 超网站信息, 网站
from 配置 import 爬取线程数, 爬取集中度, 单网页最多关键词, 入口, 存储位置
from utils import tqdm_exception_logger, 坏, 检测语言, netloc, html结构特征


门 = 融合之门(存储位置/'门')
繁荣表 = 信息.繁荣表()

访问url数 = tqdm(desc='访问url数')
访问成功url数 = tqdm(desc='访问成功url数')
获取域名基本信息次数 = tqdm(desc='获取域名基本信息次数')


def 摘(url: str) -> Tuple[str, str, str, List[str], str, Dict[str, str], str, str]:
    r = 摘要(url, timeout=10)
    if len(url) >= 250:
        return r
    title, description, text, href, 真url, 重定向表, raw, 服务器类型 = r
    重定向表 = {k: v for k, v in 重定向表.items() if k == f'https://{netloc(k)}/'}
    if 重定向表:
        for k, v in 重定向表.items():
            b = netloc(k)
            息 = 超网站信息[b]
            息.重定向[k] = v
            超网站信息[b] = 息
    门[真url] = title, description[:256], text[:256], int(time.time())
    l = 分析.龙(title, description, text)
    if l:
        l = sorted(l, key=lambda x: x[1], reverse=True)[:单网页最多关键词]
        data = [真url, l]
        requests.post('http://127.0.0.1:5000/l', data=json.dumps(data)).raise_for_status()
    return r


def 再装填(b: str, x: 网站):
    try:
        if x.质量 is None or x.特征 is None or x.关键词 is None or x.https可用 is None or x.结构 is None:
            x.质量, x.特征, x.关键词, https可用, x.结构, 服务器类型 = 域名基本信息(b)
            if not x.https可用:
                x.https可用 = https可用
            if 服务器类型 and not x.服务器类型:
                x.服务器类型 = [服务器类型]
    except Exception as e:
        tqdm_exception_logger(e)
    try:
        if x.ip is None:
            x.ip = [i[4][0] for i in socket.getaddrinfo(b, 443, 0, 0, socket.SOL_TCP)][:3]
    except Exception as e:
        tqdm_exception_logger(e)


def 域名基本信息(域名: str) -> Tuple[float, str, List[str], bool, str, str]:
    获取域名基本信息次数.update(1)
    try:
        title, description, text, href, 真url, 重定向表, raw, 服务器类型 = 摘(f'https://{域名}/')
        https可用 = True
    except Exception:
        title, description, text, href, 真url, 重定向表, raw, 服务器类型 = 摘(f'http://{域名}/')
        https可用 = False
    s = 1.0
    if not title:
        s *= 0.2
    if not description:
        s *= 0.7
    if not https可用:
        s *= 0.8
    if 'm' in 域名.split('.'):
        s *= 0.6
    z = ' '.join([title, description, text])
    e = z.encode('utf8')
    特征 = len(z), hashlib.md5(e).hexdigest(), sum([*e])
    结构 = html结构特征(raw)
    关键词 = [x[0] for x in sorted(分析.龙('', '', text), key=lambda x:-x[1])[:40]]
    return s, 特征, 关键词, https可用, 结构, 服务器类型


def 超吸(url: str) -> List[str]:
    访问url数.update(1)
    try:
        try:
            title, description, text, href, 真url, 重定向表, raw, 服务器类型 = 摘(url)
        except Exception as e:
            b = netloc(url)
            息 = 超网站信息[b]
            if 息.ip is None:    # 不做错误处理，如果DNS查询失败说明它不是域名
                息.ip = [i[4][0] for i in socket.getaddrinfo(b, 443, 0, 0, socket.SOL_TCP)][:3]
            if 息.成功率 is None:
                息.成功率 = 0
            息.成功率 *= 0.99
            超网站信息[b] = 息
            raise e
        else:
            访问成功url数.update(1)
            b = netloc(真url)
            超b = 缩(真url)

            息 = 超网站信息[b]
            息.访问次数 += 1
            息.最后访问时间 = int(time.time())
            if 息.成功率 is None:
                息.成功率 = 1
            if 真url.startswith('https://'):
                息.https可用 = True
            息.成功率 = 息.成功率 * 0.99 + 0.01
            再装填(b, 息)
            try:
                if 服务器类型 and 服务器类型 not in 息.服务器类型:
                    息.服务器类型.append(服务器类型)
                    息.服务器类型 = 息.服务器类型[-5:]
                if 息.访问次数 < 10 or random.random() < 0.1:
                    语种 = 检测语言(' '.join((title, description, text)))
                    td = {k: v*0.9 for k, v in 息.语种.items()}
                    td[语种] = td.get(语种, 0) + 0.1
                    息.语种 = td
                    外href = [h for h in href if 缩(h) != 超b]
                    息.链接 += random.sample(外href, min(10, len(外href)))
                    if len(息.链接) > 250:
                        息.链接 = random.sample(息.链接, 200)
            except Exception as e:
                tqdm_exception_logger(e)
            超网站信息[b] = 息

            if 超b != b:
                超息 = 超网站信息[超b]
                超息.访问次数 += 0.2
                再装填(超b, 超息)
                超网站信息[超b] = 超息
            return href
    except Exception as e:
        tqdm_exception_logger(e)
        time.sleep(0.2)
        return []


def 纯化(f: Callable, a: Iterable[str], k: float) -> List[str]:
    d = {}
    a = [*a]
    random.shuffle(a)
    for url in a:
        d.setdefault(f(url), []).append(url)
    res = []
    for v in d.values():
        sn = 1 + int(len(v)**k)
        res += v[:sn]
    random.shuffle(res)
    return res


def 重整(url_list: List[Tuple[str, float]]) -> Tuple[List[str], List[str]]:
    def 计算兴趣(域名: str, 已访问次数: int) -> float:
        限制 = 繁荣表.get(域名, 0) * 500 + 50
        b = 0.1**(1/限制)
        return b ** 已访问次数
    def 喜欢(item: Tuple[str, float]) -> float:
        url, 基本权重 = item
        b = netloc(url)
        息 = 缓存信息[b]
        if 息.语种:
            中文度 = 息.语种.get('zh', 0) / sum(息.语种.values())
        else:
            中文度 = 0.5
        已访问次数, 质量 = 息.访问次数, 息.质量 or 1
        超b = 缩(url)
        兴趣 = 计算兴趣(b, 已访问次数)
        if 超b == b:
            兴趣2 = 1
        else:
            超息 = 缓存信息[超b]
            已访问次数2 = 超息.访问次数
            兴趣2 = 计算兴趣(超b, 已访问次数2)
        繁荣 = min(30, 繁荣表.get(b, 0))
        荣 = math.log2(2+繁荣) + 2
        协议 = 1 - 0.5 * url.startswith('http://')
        return (0.2 + 中文度*0.8) * max(0.1, 兴趣) * 质量 * max(0.1, 兴趣2) * (1-坏(url)) * 基本权重 * 荣 * 协议
    if len(url_list) > 10_0000:
        url_list = random.sample(url_list, 10_0000)
    urls = [url for url, w in url_list]
    domains = {netloc(url) for url in urls} | {缩(url) for url in urls}
    pool = ThreadPoolExecutor(max_workers=16)
    缓存信息 = {k: v for k, v in zip(domains, pool.map(超网站信息.get, domains))}
    a = random.choices(url_list, weights=map(喜欢, url_list), k=min(40000, len(url_list)//5+100))
    a = {url for url, w in a}
    res = 纯化(lambda url: tldextract.extract(url).domain, a, 爬取集中度)
    return res


打点 = []


def bfs(start: str, epoch=150):
    吸过 = set()
    pool = ThreadPoolExecutor(max_workers=爬取线程数)
    q = [start]
    for ep in tqdm(range(epoch), ncols=60):
        吸过 |= {*q}
        新q = []
        for href in pool.map(超吸, q):
            n = len(href)
            for url in href:
                if url not in 吸过:
                    新q.append((url, 1/n))
        if not 新q:
            print('队列空了，坏！')
            return
        上l = len(新q)
        q = 重整(新q)

        c = Counter([netloc(x) for x in q])
        超c = Counter([缩(x) for x in q])
        打点.append({
            'ep': ep,
            '上次抓到的长度': 上l,
            'url个数': len(q),
            '域名个数': len(c),
            '一级域名个数': len(超c),
            '各个域名的url个数': dict(c.most_common(20)),
            '各个一级域名的url个数': dict(超c.most_common(20)),
        })
        with open('打点.json', 'w', encoding='utf8') as f:
            f.write(json.dumps(打点, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    time.sleep(3)
    bfs(入口)
