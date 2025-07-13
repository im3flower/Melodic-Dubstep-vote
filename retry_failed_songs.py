#!/usr/bin/env python3
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
