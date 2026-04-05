#!/usr/bin/env python3
"""
Reddit Research Scanner - Read-only monitoring tool using PRAW.

Scans public subreddits for trends, insights, and sentiment across
multiple research domains. Does not post, comment, or interact.

Usage:
    python3 reddit_scanner.py --domain ai         # AI/ML discussions
    python3 reddit_scanner.py --domain trading     # Stocks/options/day trading
    python3 reddit_scanner.py --domain crypto      # Cryptocurrency
    python3 reddit_scanner.py --domain marketing   # PPC, SEO, digital marketing
    python3 reddit_scanner.py --domain all         # All domains
    python3 reddit_scanner.py --search "claude regression"  # Search specific topic
    python3 reddit_scanner.py --trending           # Top trending across all domains

Config: ~/.config/reddit/credentials.json
Output: Prints to stdout or saves to --output file
"""

import praw
import json
import os
import sys
import argparse
from datetime import datetime, timezone

# --- Configuration ---

CONFIG_PATH = os.path.expanduser("~/.config/reddit/credentials.json")

DOMAINS = {
    "ai": {
        "subreddits": [
            "ClaudeAI", "LocalLLaMA", "MachineLearning", "artificial",
            "ChatGPT", "AutoGPT", "singularity", "LangChain"
        ],
        "keywords": [
            "claude", "agent", "memory", "regression", "MCP",
            "local LLM", "ollama", "framework", "autonomous"
        ]
    },
    "trading": {
        "subreddits": [
            "wallstreetbets", "stocks", "investing", "options",
            "daytrading", "algotrading", "stockmarket"
        ],
        "keywords": [
            "momentum", "oversold", "RSI", "MACD", "scalping",
            "swing trade", "earnings", "squeeze"
        ]
    },
    "crypto": {
        "subreddits": [
            "cryptocurrency", "bitcoin", "ethereum", "solana",
            "CryptoMarkets", "defi", "CryptoTechnology"
        ],
        "keywords": [
            "BTC", "ETH", "SOL", "scalping", "funding rate",
            "order book", "whale", "DeFi"
        ]
    },
    "marketing": {
        "subreddits": [
            "PPC", "digital_marketing", "googleads", "FacebookAds",
            "SEO", "analytics", "advertising"
        ],
        "keywords": [
            "ROAS", "conversion", "CPA", "CTR", "quality score",
            "Performance Max", "broad match", "Meta Ads"
        ]
    },
    "design": {
        "subreddits": [
            "InteriorDesign", "architecture", "DesignPorn",
            "RoomPorn", "AmateurRoomPorn"
        ],
        "keywords": [
            "minimalist", "warm", "bouclé", "marble", "renovation",
            "styling", "luxury"
        ]
    },
    "startups": {
        "subreddits": [
            "startups", "venturecapital", "Entrepreneur",
            "SaaS", "smallbusiness"
        ],
        "keywords": [
            "pitch deck", "Series A", "bootstrapped", "valuation",
            "product market fit", "fundraising"
        ]
    },
    "tech": {
        "subreddits": [
            "programming", "rust", "golang", "elixir",
            "selfhosted", "homeassistant", "webdev"
        ],
        "keywords": [
            "Rust", "Go", "Elixir", "WASM", "transpiler",
            "DSL", "agent framework", "self-hosted"
        ]
    }
}


def load_credentials():
    """Load Reddit API credentials from config file."""
    if not os.path.exists(CONFIG_PATH):
        print(f"ERROR: Credentials not found at {CONFIG_PATH}")
        print("Create the file with: client_id, client_secret, username, password")
        sys.exit(1)

    with open(CONFIG_PATH) as f:
        creds = json.load(f)

    required = ["client_id", "client_secret", "username", "password"]
    for key in required:
        if key not in creds:
            print(f"ERROR: Missing '{key}' in {CONFIG_PATH}")
            sys.exit(1)

    return creds


def get_reddit(creds):
    """Initialize PRAW Reddit instance."""
    return praw.Reddit(
        client_id=creds["client_id"],
        client_secret=creds["client_secret"],
        username=creds["username"],
        password=creds["password"],
        user_agent="HiroResearchScanner/1.0 (personal read-only research tool)"
    )


def scan_subreddit(reddit, subreddit_name, limit=10, time_filter="week"):
    """Scan a subreddit for top posts."""
    results = []
    try:
        sub = reddit.subreddit(subreddit_name)
        for post in sub.top(time_filter=time_filter, limit=limit):
            results.append({
                "title": post.title,
                "score": post.score,
                "comments": post.num_comments,
                "url": f"https://reddit.com{post.permalink}",
                "created": datetime.fromtimestamp(post.created_utc, tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
                "subreddit": subreddit_name,
                "selftext_preview": (post.selftext[:200] + "...") if post.selftext else "",
                "flair": post.link_flair_text or ""
            })
    except Exception as e:
        print(f"  Warning: Could not scan r/{subreddit_name}: {e}")

    return results


def search_reddit(reddit, query, subreddits=None, limit=20, time_filter="week"):
    """Search Reddit for a specific topic."""
    results = []
    try:
        if subreddits:
            sub_str = "+".join(subreddits)
            sub = reddit.subreddit(sub_str)
        else:
            sub = reddit.subreddit("all")

        for post in sub.search(query, time_filter=time_filter, limit=limit, sort="relevance"):
            results.append({
                "title": post.title,
                "score": post.score,
                "comments": post.num_comments,
                "url": f"https://reddit.com{post.permalink}",
                "created": datetime.fromtimestamp(post.created_utc, tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
                "subreddit": post.subreddit.display_name,
                "selftext_preview": (post.selftext[:200] + "...") if post.selftext else "",
                "flair": post.link_flair_text or ""
            })
    except Exception as e:
        print(f"  Warning: Search failed for '{query}': {e}")

    return results


def scan_domain(reddit, domain_name, limit=10):
    """Scan all subreddits in a domain."""
    if domain_name not in DOMAINS:
        print(f"ERROR: Unknown domain '{domain_name}'. Available: {', '.join(DOMAINS.keys())}")
        sys.exit(1)

    domain = DOMAINS[domain_name]
    all_results = []

    print(f"\n{'='*60}")
    print(f"  DOMAIN: {domain_name.upper()}")
    print(f"  Subreddits: {', '.join('r/' + s for s in domain['subreddits'])}")
    print(f"{'='*60}")

    for sub_name in domain["subreddits"]:
        posts = scan_subreddit(reddit, sub_name, limit=limit)
        all_results.extend(posts)
        print(f"  r/{sub_name}: {len(posts)} posts")

    # Sort by score
    all_results.sort(key=lambda x: x["score"], reverse=True)

    # Print top posts
    print(f"\n  TOP POSTS (by score):")
    for i, post in enumerate(all_results[:15], 1):
        print(f"  {i:2d}. [{post['score']:>5d}] r/{post['subreddit']} - {post['title'][:80]}")
        if post["flair"]:
            print(f"      Flair: {post['flair']} | Comments: {post['comments']} | {post['created']}")

    return all_results


def scan_trending(reddit):
    """Get trending posts across all domains."""
    all_results = []

    print(f"\n{'='*60}")
    print(f"  TRENDING ACROSS ALL DOMAINS")
    print(f"{'='*60}")

    for domain_name, domain in DOMAINS.items():
        for sub_name in domain["subreddits"]:
            posts = scan_subreddit(reddit, sub_name, limit=5, time_filter="day")
            for post in posts:
                post["domain"] = domain_name
            all_results.extend(posts)

    # Sort by score
    all_results.sort(key=lambda x: x["score"], reverse=True)

    # Print top 25
    print(f"\n  TOP 25 TRENDING:")
    for i, post in enumerate(all_results[:25], 1):
        print(f"  {i:2d}. [{post['score']:>5d}] [{post['domain']:>10s}] r/{post['subreddit']} - {post['title'][:70]}")

    return all_results


def main():
    parser = argparse.ArgumentParser(description="Reddit Research Scanner")
    parser.add_argument("--domain", choices=list(DOMAINS.keys()) + ["all"], help="Domain to scan")
    parser.add_argument("--search", help="Search for a specific topic")
    parser.add_argument("--trending", action="store_true", help="Show trending across all domains")
    parser.add_argument("--limit", type=int, default=10, help="Posts per subreddit (default: 10)")
    parser.add_argument("--time", choices=["day", "week", "month"], default="week", help="Time filter (default: week)")
    parser.add_argument("--output", help="Save results to JSON file")

    args = parser.parse_args()

    if not args.domain and not args.search and not args.trending:
        parser.print_help()
        sys.exit(0)

    creds = load_credentials()
    reddit = get_reddit(creds)

    print(f"\nReddit Research Scanner - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Authenticated as: {creds['username']}")

    results = []

    if args.trending:
        results = scan_trending(reddit)

    elif args.search:
        print(f"\nSearching: '{args.search}' (time: {args.time})")
        subreddits = None
        if args.domain and args.domain != "all":
            subreddits = DOMAINS[args.domain]["subreddits"]
        results = search_reddit(reddit, args.search, subreddits=subreddits, limit=args.limit, time_filter=args.time)

        print(f"\n  RESULTS ({len(results)} found):")
        for i, post in enumerate(results[:20], 1):
            print(f"  {i:2d}. [{post['score']:>5d}] r/{post['subreddit']} - {post['title'][:80]}")
            if post["selftext_preview"]:
                print(f"      {post['selftext_preview'][:100]}")

    elif args.domain == "all":
        for domain_name in DOMAINS:
            domain_results = scan_domain(reddit, domain_name, limit=args.limit)
            results.extend(domain_results)

    elif args.domain:
        results = scan_domain(reddit, args.domain, limit=args.limit)

    # Save to file if requested
    if args.output and results:
        output = {
            "scan_date": datetime.now().isoformat(),
            "domain": args.domain or "search",
            "query": args.search,
            "result_count": len(results),
            "results": results
        }
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\nResults saved to: {args.output}")

    print(f"\nScan complete. {len(results)} total posts found.")


if __name__ == "__main__":
    main()
