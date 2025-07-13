import re
import csv
import time
import random
import hashlib
import requests
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm
import logging
import json
import os

# 配置高级日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    filename='netease_song_extractor.log',
    filemode='a'
)
logger = logging.getLogger(__name__)

class NeteaseAPI:
    """网易云音乐API客户端（带签名功能）"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://music.163.com/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        })
        self.cookies = self.load_cookies()
        self.api_key = "3go8&$8*3*3h0k(2)2"
        
    def load_cookies(self):
        """从文件加载Cookies"""
        if os.path.exists('netease_cookies.json'):
            try:
                with open('netease_cookies.json', 'r') as f:
                    return requests.utils.cookiejar_from_dict(json.load(f))
            except:
                pass
        return None
    
    def save_cookies(self):
        """保存Cookies到文件"""
        with open('netease_cookies.json', 'w') as f:
            json.dump(requests.utils.dict_from_cookiejar(self.session.cookies), f)
    
    def weapi_encrypt(self, text):
        """实现网易云WEAPI加密算法"""
        key = "rFgB&h#%2?^eDg:Q".encode('utf-8')
        cryptor = hashlib.md5(key)
        cryptor.update(text.encode('utf-8'))
        return cryptor.hexdigest()
    
    def generate_signature(self, params):
        """生成API签名"""
        keys = sorted(params.keys())
        message = ''.join([f'{k}={params[k]}' for k in keys])
        signature = self.weapi_encrypt(message)
        return signature
    
    def song_detail(self, song_ids, max_retries=5):
        """获取歌曲详情（带自动重试）"""
        if not isinstance(song_ids, list):
            song_ids = [song_ids]
            
        params = {
            'c': json.dumps([{'id': sid} for sid in song_ids]),
            'ids': json.dumps(song_ids),
            'timestamp': int(time.time() * 1000)
        }
        
        # 生成签名
        params['signature'] = self.generate_signature(params)
        
        url = "https://music.163.com/api/v3/song/detail"
        
        for attempt in range(max_retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 检查响应结构
                    if 'songs' in data and data['songs']:
                        return data
                    
                    # 检查错误码
                    if data.get('code', 0) != 200:
                        logger.warning(f"API返回错误: code={data.get('code')}, msg={data.get('message')}")
                    
                    # 特殊处理404
                    if data.get('code') == 404:
                        return None
                
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 30))
                    logger.warning(f"速率限制触发，等待 {retry_after} 秒")
                    time.sleep(retry_after)
                    continue
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"请求失败: {type(e).__name__} - {e}")
            
            
            if attempt < max_retries:
                sleep_time = 2 ** attempt + random.uniform(0, 1)
                time.sleep(sleep_time)
        
        logger.error(f"所有重试失败: {song_ids}")
        return None



class NeteaseSongExtractor:
    def __init__(self):
        self.api = NeteaseAPI()
        # 不缓存失败结果
        self.failed_ids = set()
        
    def extract_from_html(self, html_content):
        
        soup = BeautifulSoup(html_content, 'html.parser')
        song_list = []
        
        for li in soup.find_all('li'):
            a_tag = li.find('a', href=re.compile(r'/song\?id=\d+'))
            if a_tag:
                song_id = re.search(r'id=(\d+)', a_tag['href']).group(1)
                song_name = a_tag.get_text(strip=True)
                song_list.append((song_id, song_name))
        
        return song_list
    
    
    
    def get_artist_info(self, song_id):
        
        # 跳过已知失败的ID
        if song_id in self.failed_ids:
            return "歌曲信息不存在"
            
        result = self.api.song_detail(song_id)
        
        if result is None:
            self.failed_ids.add(song_id)
            return "歌曲信息不存在"
            
            
        if 'songs' in result and result['songs']:
            song_data = result['songs'][0]
            artists = [artist['name'] for artist in song_data['ar']]
            return ', '.join(artists)
        
        self.failed_ids.add(song_id)
        return "歌曲信息不存在"
    
    def process_file(self, input_html, output_csv, batch_size=10):
        
        try:
            logger.info(f"开始处理文件: {input_html}")
            with open(input_html, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except Exception as e:
            logger.error(f"文件读取失败: {e}")
            return False
        
        
        songs = self.extract_from_html(html_content)
        logger.info(f"共找到 {len(songs)} 首歌曲")
        
        if not songs:
            logger.warning("未找到任何歌曲信息")
            return False
        
        
        processed_ids = set()
        output_exists = os.path.exists(output_csv)
        
        if output_exists:
            try:
                existing_df = pd.read_csv(output_csv)
                processed_ids = set(existing_df['Song ID'].astype(str))
            except:
                pass
        
        with open(output_csv, 'a', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            if not output_exists:
                writer.writerow(['Song ID', '歌曲名', '艺人'])
            
            for i in tqdm(range(0, (len(songs) + batch_size - 1) // batch_size), desc="处理歌曲", unit="批"):
                batch = []
                for j in range(batch_size):
                    idx = i * batch_size + j
                    if idx >= len(songs):
                        break
                    song_id, song_name = songs[idx]

                    if song_id in processed_ids:
                        continue
                    batch.append((song_id, song_name))
                
                if not batch:
                    continue
                

                results = []
                for song_id, song_name in batch:
                    artist = self.get_artist_info(song_id)
                    results.append((song_id, song_name, artist))
                
                writer.writerows(results)
                csvfile.flush()
               
                
                time.sleep(random.uniform(1.0, 3.0))
        
        return True

def analyze_results(output_csv):
    
    try:
        df = pd.read_csv(output_csv)
        total = len(df)
        failed = df[df['艺人'] == "歌曲信息不存在"].shape[0]
        success_rate = (total - failed) / total * 100
        
        logger.info(f"处理完成! 成功获取 {total - failed}/{total} 首歌曲信息 ({success_rate:.2f}%)")
        
        if failed > 0:
            failed_df = df[df['艺人'] == "歌曲信息不存在"]
            failed_csv = 'failed_songs.csv'
            failed_df.to_csv(failed_csv, index=False)
            logger.info(f"有 {failed} 首歌曲失败，已保存到 {failed_csv}")
            
            # 生成重试脚本
            with open('retry_failed_songs.py', 'w', encoding='utf-8') as f:
                f.write("""#!/usr/bin/env python3
# 网易云失败歌曲重试脚本
import pandas as pd
from netease_song_extractor import NeteaseSongExtractor

def main():
    extractor = NeteaseSongExtractor()
    failed_df = pd.read_csv('failed_songs.csv')
    
    # 创建新结果文件
    with open('retry_results.csv', 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Song ID', '歌曲名', '艺人'])
        
        # 使用代理重试
        for _, row in failed_df.iterrows():
            artist = extractor.get_artist_info(str(row['Song ID']))
            writer.writerow([row['Song ID'], row['歌曲名'], artist])
            # 较长延迟
            time.sleep(random.uniform(3.0, 5.0))

if __name__ == "__main__":
    main()
""")
            logger.info("已生成重试脚本: retry_failed_songs.py")
            
        return True
    except Exception as e:
        logger.error(f"结果分析失败: {e}")
        return False

def main():
    
    extractor = NeteaseSongExtractor()
    
    
    input_html = 'playlist6.html'
    output_csv = 'playlist6.csv'
    
    
    if extractor.process_file(input_html, output_csv):
        logger.info("歌曲处理完成，开始分析结果...")
        if analyze_results(output_csv):
            logger.info("处理流程全部完成！")
        else:
            logger.error("结果分析失败")
    else:
        logger.error("文件处理失败")

if __name__ == "__main__":
    main()