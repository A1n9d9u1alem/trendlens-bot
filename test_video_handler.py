"""
Test script for VideoHandler
Run this to verify video detection and URL extraction
"""

from video_handler import VideoHandler

def test_video_handler():
    handler = VideoHandler()
    
    print("=" * 60)
    print("VIDEO HANDLER TEST")
    print("=" * 60)
    
    # Test URLs
    test_urls = [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "youtube"),
        ("https://youtu.be/dQw4w9WgXcQ", "youtube"),
        ("https://www.youtube.com/shorts/abc123", "youtube"),
        ("https://www.tiktok.com/@user/video/1234567890", "tiktok"),
        ("https://v.redd.it/abc123xyz", "reddit"),
        ("https://twitter.com/user/status/1234567890", "twitter"),
        ("https://example.com/video.mp4", "direct"),
        ("https://reddit.com/r/funny/comments/abc", "reddit"),
    ]
    
    print("\n1. VIDEO DETECTION TEST")
    print("-" * 60)
    for url, platform in test_urls:
        is_video = handler.is_video_url(url)
        print(f"✓ {platform:10} | {is_video:5} | {url[:50]}")
    
    print("\n2. VIDEO ID EXTRACTION TEST")
    print("-" * 60)
    youtube_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/abc123def"
    ]
    
    for url in youtube_urls:
        video_id = handler.extract_video_id(url, 'youtube')
        print(f"URL: {url}")
        print(f"ID:  {video_id}\n")
    
    print("\n3. YOUTUBE THUMBNAIL TEST")
    print("-" * 60)
    video_id = "dQw4w9WgXcQ"
    thumbnail = handler.get_youtube_thumbnail(video_id)
    print(f"Video ID: {video_id}")
    print(f"Thumbnail: {thumbnail}")
    
    print("\n4. VIDEO INFO TEST")
    print("-" * 60)
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    info = handler.get_video_info(test_url, 'youtube')
    print(f"URL: {test_url}")
    print(f"Info: {info}")
    
    print("\n5. SEND AS VIDEO TEST")
    print("-" * 60)
    test_cases = [
        ("https://v.redd.it/abc123", "reddit"),
        ("https://www.youtube.com/watch?v=abc123", "youtube"),
        ("https://example.com/video.mp4", "direct"),
    ]
    
    for url, platform in test_cases:
        should_send, video_url = handler.should_send_as_video(url, platform)
        print(f"Platform: {platform}")
        print(f"Should send as video: {should_send}")
        print(f"Video URL: {video_url}\n")
    
    print("=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    test_video_handler()
