import csv

def search_songs(csv_file, keyword):
    
    results = []
    
    
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            song_id = row['Song ID']
            title = row['歌曲名']
            artist = row['艺人']
            
            
            title_match = keyword.lower() in title.lower()
            artist_match = keyword.lower() in artist.lower()
            
            
            if title_match or artist_match:
                
                score = 0
                
                if title_match:
                    score += 3
                if artist_match:
                    score += 1
                
                results.append({
                    'score': score,
                    'song_id': song_id,
                    'title': title,
                    'artist': artist,
                    'raw_data': row
                })
    
    
    results.sort(key=lambda x: (-x['score'], x['title']))
    
    return [item['raw_data'] for item in results]



def main(search_term):
    
    matched_songs = search_songs('songlist.csv', search_term)
    
    print(f"\n找到 {len(matched_songs)} 首相关歌曲:")
    for i, song in enumerate(matched_songs, 1):
        print(f"{i}. [{song['Song ID']}] {song['歌曲名']} - {song['艺人']}")
