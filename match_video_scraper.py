"""
YouTube Match Video Scraper - finds and downloads full volleyball matches
Searches for high-quality match footage and extracts URLs automatically
"""
import os
import json
import time
from datetime import datetime
import subprocess

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("ERROR: Google API client not installed")
    print("Install with: pip install google-api-python-client")
    exit(1)

# ── Configuration ─────────────────────────────────────────────────────────────
BASE_DIR = "C:/sportsai-backend"
OUTPUT_CSV = os.path.join(BASE_DIR, "data/input/match_urls.csv")
OUTPUT_JSON = os.path.join(BASE_DIR, "data/input/match_metadata.json")

# Get your API key from: https://console.cloud.google.com/apis/credentials
# Enable YouTube Data API v3 in your Google Cloud Console
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "YOUR_API_KEY_HERE")

# Search queries for different match types
SEARCH_QUERIES = [
    "volleyball full match 2024 HD",
    "volleyball world championship full match",
    "volleyball olympics full match",
    "volleyball VNL full match 2024",
    "volleyball nations league full match",
    "volleyball world cup full match",
    "professional volleyball match full game",
    "FIVB volleyball full match",
]

# Quality filters
MIN_DURATION_MINUTES = 30  # Full matches are usually 60-120 minutes
MAX_DURATION_MINUTES = 180
MIN_VIEWS = 1000  # Ensure some popularity/quality
MAX_RESULTS_PER_QUERY = 10

# ── YouTube API Functions ─────────────────────────────────────────────────────

def search_youtube_matches(api_key: str, query: str, max_results: int = 10) -> list:
    """Search YouTube for volleyball match videos"""
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        search_response = youtube.search().list(
            q=query,
            part='id,snippet',
            maxResults=max_results,
            type='video',
            videoDuration='long',  # Only long videos (>20 min)
            videoDefinition='high',  # HD only
            order='relevance',
            relevanceLanguage='en'
        ).execute()
        
        videos = []
        for item in search_response.get('items', []):
            video_id = item['id']['videoId']
            title = item['snippet']['title']
            channel = item['snippet']['channelTitle']
            published = item['snippet']['publishedAt']
            
            # Get detailed video stats
            video_response = youtube.videos().list(
                part='contentDetails,statistics',
                id=video_id
            ).execute()
            
            if not video_response['items']:
                continue
                
            video_data = video_response['items'][0]
            duration = video_data['contentDetails']['duration']
            stats = video_data['statistics']
            
            # Parse ISO 8601 duration (PT1H23M45S)
            duration_minutes = parse_duration(duration)
            
            # Filter by duration and views
            view_count = int(stats.get('viewCount', 0))
            if (MIN_DURATION_MINUTES <= duration_minutes <= MAX_DURATION_MINUTES 
                and view_count >= MIN_VIEWS):
                
                videos.append({
                    'video_id': video_id,
                    'url': f'https://www.youtube.com/watch?v={video_id}',
                    'title': title,
                    'channel': channel,
                    'duration_minutes': duration_minutes,
                    'views': view_count,
                    'likes': int(stats.get('likeCount', 0)),
                    'published': published,
                    'query': query
                })
        
        return videos
        
    except HttpError as e:
        print(f"YouTube API error: {e}")
        return []


def parse_duration(iso_duration: str) -> int:
    """Convert ISO 8601 duration to minutes (PT1H23M45S -> 83)"""
    import re
    hours = re.search(r'(\d+)H', iso_duration)
    minutes = re.search(r'(\d+)M', iso_duration)
    
    total_minutes = 0
    if hours:
        total_minutes += int(hours.group(1)) * 60
    if minutes:
        total_minutes += int(minutes.group(1))
    
    return total_minutes


# ── Main Scraper ──────────────────────────────────────────────────────────────

def scrape_match_videos():
    """Main scraper - searches YouTube and saves results"""
    
    if YOUTUBE_API_KEY == "YOUR_API_KEY_HERE":
        print("ERROR: YouTube API key not configured")
        print("\nTo get an API key:")
        print("1. Go to: https://console.cloud.google.com/")
        print("2. Create a new project (or select existing)")
        print("3. Enable 'YouTube Data API v3'")
        print("4. Go to Credentials -> Create Credentials -> API Key")
        print("5. Set the key in environment variable: YOUTUBE_API_KEY")
        print("   OR edit this file and replace YOUR_API_KEY_HERE")
        return
    
    print("Starting YouTube match video scraper...")
    print(f"API Key: {YOUTUBE_API_KEY[:10]}...")
    print(f"Searching {len(SEARCH_QUERIES)} queries")
    print("="*60)
    
    all_videos = []
    seen_ids = set()
    
    for i, query in enumerate(SEARCH_QUERIES, 1):
        print(f"\n[{i}/{len(SEARCH_QUERIES)}] Searching: {query}")
        videos = search_youtube_matches(YOUTUBE_API_KEY, query, MAX_RESULTS_PER_QUERY)
        
        # Deduplicate
        new_videos = [v for v in videos if v['video_id'] not in seen_ids]
        for v in new_videos:
            seen_ids.add(v['video_id'])
        
        all_videos.extend(new_videos)
        print(f"  Found {len(new_videos)} new matches ({len(all_videos)} total)")
        
        # Rate limit - YouTube API has quota limits
        time.sleep(1)
    
    if not all_videos:
        print("\nNo videos found. Check your API key and quota.")
        return
    
    # Sort by views (quality proxy)
    all_videos.sort(key=lambda x: x['views'], reverse=True)
    
    # Save CSV
    with open(OUTPUT_CSV, 'w', encoding='utf-8') as f:
        f.write("url,title,channel,duration_min,views,skill_level\n")
        for v in all_videos:
            # Estimate skill level from title keywords
            title_lower = v['title'].lower()
            if any(kw in title_lower for kw in ['olympic', 'world championship', 'vnl', 'fivb']):
                skill = 'elite'
            elif any(kw in title_lower for kw in ['professional', 'national', 'international']):
                skill = 'advanced'
            else:
                skill = 'intermediate'
            
            f.write(f"{v['url']},{v['title']},{v['channel']},{v['duration_minutes']},{v['views']},{skill}\n")
    
    # Save detailed JSON
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump({
            'scraped_at': datetime.now().isoformat(),
            'total_videos': len(all_videos),
            'videos': all_videos
        }, f, indent=2)
    
    print("\n" + "="*60)
    print(f"✓ Scraped {len(all_videos)} match videos")
    print(f"✓ Saved to: {OUTPUT_CSV}")
    print(f"✓ Metadata: {OUTPUT_JSON}")
    print("\nTop 5 matches by views:")
    for i, v in enumerate(all_videos[:5], 1):
        print(f"  {i}. {v['title'][:60]}... ({v['views']:,} views, {v['duration_minutes']} min)")


# ── Alternative: Scrape without API (web scraping) ───────────────────────────

def scrape_without_api():
    """
    Alternative scraper using yt-dlp to search YouTube
    No API key needed, but less reliable and slower
    """
    print("Scraping without API using yt-dlp...")
    print("Installing yt-dlp if needed...")
    
    try:
        subprocess.run(['pip', 'install', 'yt-dlp'], check=True, capture_output=True)
    except:
        print("ERROR: Could not install yt-dlp")
        return
    
    all_videos = []
    
    for query in SEARCH_QUERIES:
        print(f"\nSearching: {query}")
        
        # Use yt-dlp to search (returns JSON)
        cmd = [
            'yt-dlp',
            f'ytsearch{MAX_RESULTS_PER_QUERY}:{query}',
            '--dump-json',
            '--no-download',
            '--match-filter', f'duration > {MIN_DURATION_MINUTES*60} & duration < {MAX_DURATION_MINUTES*60}'
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    all_videos.append({
                        'video_id': data['id'],
                        'url': data['webpage_url'],
                        'title': data['title'],
                        'channel': data['uploader'],
                        'duration_minutes': int(data['duration'] / 60),
                        'views': data.get('view_count', 0),
                        'likes': data.get('like_count', 0),
                        'published': data.get('upload_date', ''),
                        'query': query
                    })
                except json.JSONDecodeError:
                    continue
            
            print(f"  Found {len(all_videos)} videos so far")
            time.sleep(2)  # Be nice to YouTube
            
        except subprocess.TimeoutExpired:
            print("  Search timed out, skipping...")
            continue
    
    # Save results (same format as API version)
    if all_videos:
        all_videos.sort(key=lambda x: x['views'], reverse=True)
        
        with open(OUTPUT_CSV, 'w', encoding='utf-8') as f:
            f.write("url,title,channel,duration_min,views,skill_level\n")
            for v in all_videos:
                title_lower = v['title'].lower()
                if any(kw in title_lower for kw in ['olympic', 'world championship', 'vnl']):
                    skill = 'elite'
                elif 'professional' in title_lower:
                    skill = 'advanced'
                else:
                    skill = 'intermediate'
                
                f.write(f"{v['url']},{v['title']},{v['channel']},{v['duration_minutes']},{v['views']},{skill}\n")
        
        print(f"\n✓ Scraped {len(all_videos)} videos")
        print(f"✓ Saved to: {OUTPUT_CSV}")


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--no-api":
        scrape_without_api()
    else:
        scrape_match_videos()
