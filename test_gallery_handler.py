"""
Test Image Gallery Handler
"""

from image_gallery_handler import ImageGalleryHandler

def test_gallery():
    handler = ImageGalleryHandler()
    
    print("=" * 60)
    print("IMAGE GALLERY HANDLER TEST")
    print("=" * 60)
    
    # Test gallery detection
    test_urls = [
        ("https://reddit.com/gallery/abc123", "reddit"),
        ("https://imgur.com/a/xyz789", "imgur"),
        ("https://twitter.com/user/status/123", "twitter"),
        ("https://reddit.com/r/pics/comments/abc", "reddit"),
    ]
    
    print("\n1. GALLERY DETECTION TEST")
    print("-" * 60)
    for url, platform in test_urls:
        is_gallery = handler.is_gallery_url(url)
        print(f"{platform:10} | {is_gallery:5} | {url}")
    
    print("\n2. GALLERY INFO TEST")
    print("-" * 60)
    
    # Test with mock content
    mock_content = {
        'url': 'https://reddit.com/gallery/test123',
        'platform': 'reddit',
        'thumbnail': 'https://i.redd.it/image1.jpg',
        'description': 'https://i.redd.it/image2.jpg | https://i.redd.it/image3.jpg'
    }
    
    info = handler.get_gallery_info(mock_content['url'], 'reddit', mock_content)
    print(f"Is Gallery: {info['is_gallery']}")
    print(f"Image Count: {info['image_count']}")
    print(f"Has Multiple: {info['has_multiple_images']}")
    print(f"Images: {info['images']}")
    
    print("\n3. IMAGE VALIDATION TEST")
    print("-" * 60)
    test_images = [
        'https://i.redd.it/abc123.jpg',
        'https://i.imgur.com/xyz.png',
        'https://preview.redd.it/test.webp',
        'https://example.com/notanimage',
    ]
    
    for img in test_images:
        valid = handler.validate_image_url(img)
        print(f"{valid:5} | {img}")
    
    print("\n=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    test_gallery()
