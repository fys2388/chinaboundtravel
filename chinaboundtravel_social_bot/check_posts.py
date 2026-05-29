from content_manager import ContentManager

cm = ContentManager()

print(f"Total content items: {len(cm.posts)}")
print("\n" + "="*70)
print("Content by source:")
for source, count in cm.get_stats()['by_source'].items():
    print(f"  {source}: {count}")

print("\n" + "="*70)
print("All content items:")
for i, post in enumerate(cm.posts, 1):
    print(f"\n{i}. {post.get('title', 'Untitled')}")
    print(f"   URL: {post.get('url', 'No URL')}")
    print(f"   Published: {post.get('published_at', 'Not published')}")
    print(f"   Source: {post.get('source', 'unknown')}")
