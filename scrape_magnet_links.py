#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scrape magnet download links from dygod.net search results page
"""

import requests
from bs4 import BeautifulSoup
import re
import time

def scrape_magnet_links(url):
    """Scrape all magnet links from the given dygod.net page"""
    magnet_links = []
    
    try:
        # Set headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        print(f"正在访问页面: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        # Try multiple encodings
        response.encoding = response.apparent_encoding or 'utf-8'
        
        if response.status_code != 200:
            print(f"页面访问失败，状态码: {response.status_code}")
            return magnet_links
            
        # Use html.parser with proper encoding handling
        soup = BeautifulSoup(response.content, 'html.parser', from_encoding=response.encoding)
        
        # Find all movie entries
        movie_entries = soup.find_all('div', class_='co_content8') or soup.find_all('div', class_='co_area2')
        
        if not movie_entries:
            print("未找到电影条目，尝试其他选择器...")
            # Try to find all links that might contain movie info
            all_links = soup.find_all('a', href=True)
            movie_links = []
            
            for link in all_links:
                href = link['href']
                text = link.get_text().strip()
                # Look for movie-related links
                if any(keyword in text.lower() for keyword in ['蓝光', '中英', '国粤', '中字']) or \
                   any(keyword in href for keyword in ['/html/', '/html/gndy/', '/html/dyzz/']):
                    if href.startswith('/'):
                        movie_links.append(f"https://www.dygod.net{href}")
                    elif href.startswith('http'):
                        movie_links.append(href)
            
            print(f"找到 {len(movie_links)} 个可能的电影链接")
            
            # Visit each movie page to find magnet links
            for i, movie_url in enumerate(movie_links, 1):
                print(f"正在处理第 {i}/{len(movie_links)} 个电影页面...")
                try:
                    movie_response = requests.get(movie_url, headers=headers, timeout=20)
                    movie_response.encoding = movie_response.apparent_encoding or 'utf-8'
                    
                    if movie_response.status_code == 200:
                        movie_soup = BeautifulSoup(movie_response.content, 'html.parser', from_encoding=movie_response.encoding)
                        
                        # Look for magnet links in the movie page with better encoding
                        magnet_pattern = re.compile(r'magnet:\?[^"\'<>\s]+', re.IGNORECASE)
                        magnets_in_page = magnet_pattern.findall(movie_response.text)
                        
                        if magnets_in_page:
                            # Clean and decode magnet links properly
                            for magnet in magnets_in_page:
                                try:
                                    # URL decode the magnet link if needed
                                    from urllib.parse import unquote
                                    decoded_magnet = unquote(magnet)
                                    magnet_links.append(decoded_magnet)
                                except Exception:
                                    magnet_links.append(magnet)
                            print(f"  找到 {len(magnets_in_page)} 个磁力链接")
                        else:
                            # Try to find download links that might contain magnets
                            download_links = movie_soup.find_all('a', href=True)
                            for dl_link in download_links:
                                if 'magnet' in dl_link['href'].lower():
                                    try:
                                        from urllib.parse import unquote
                                        decoded_magnet = unquote(dl_link['href'])
                                        magnet_links.append(decoded_magnet)
                                    except Exception:
                                        magnet_links.append(dl_link['href'])
                                elif any(keyword in dl_link.get_text().lower() for keyword in ['迅雷', '磁力', 'magnet']):
                                    # Try to find magnet in onclick or other attributes
                                    onclick = dl_link.get('onclick', '')
                                    magnet_match = magnet_pattern.search(onclick)
                                    if magnet_match:
                                        try:
                                            from urllib.parse import unquote
                                            decoded_magnet = unquote(magnet_match.group())
                                            magnet_links.append(decoded_magnet)
                                        except Exception:
                                            magnet_links.append(magnet_match.group())
                    
                    time.sleep(1)  # Be respectful with delays
                    
                except Exception as e:
                    print(f"  处理电影页面失败: {e}")
                    continue
        
        else:
            print(f"找到 {len(movie_entries)} 个电影条目区域")
            # Process each movie entry
            for entry in movie_entries:
                # Find all links in this entry
                links = entry.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    text = link.get_text().strip()
                    
                    # Check if it's a movie page link
                    if any(keyword in text.lower() for keyword in ['蓝光', '中英', '国粤', '中字']) or \
                       any(keyword in href for keyword in ['/html/', '/html/gndy/', '/html/dyzz/']):
                        
                        # Construct full URL
                        if href.startswith('/'):
                            movie_url = f"https://www.dygod.net{href}"
                        elif href.startswith('http'):
                            movie_url = href
                        else:
                            continue
                        
                        print(f"正在访问电影页面: {text}")
                        try:
                            movie_response = requests.get(movie_url, headers=headers, timeout=20)
                            movie_response.encoding = movie_response.apparent_encoding or 'utf-8'
                            
                            if movie_response.status_code == 200:
                                # Look for magnet links in the movie page
                                magnet_pattern = re.compile(r'magnet:\?[^"\'<>\s]+')
                                magnets_in_page = magnet_pattern.findall(movie_response.text)
                                
                                if magnets_in_page:
                                    magnet_links.extend(magnets_in_page)
                                    print(f"  找到 {len(magnets_in_page)} 个磁力链接")
                                
                            time.sleep(1)  # Be respectful with delays
                            
                        except Exception as e:
                            print(f"  处理电影页面失败: {e}")
                            continue
        
        # Also check the current page for any magnet links with better encoding
        magnet_pattern = re.compile(r'magnet:\?[^"\'<>\s]+', re.IGNORECASE)
        direct_magnets = magnet_pattern.findall(response.text)
        if direct_magnets:
            # Clean and decode direct magnets
            for magnet in direct_magnets:
                try:
                    from urllib.parse import unquote
                    decoded_magnet = unquote(magnet)
                    magnet_links.append(decoded_magnet)
                except Exception:
                    magnet_links.append(magnet)
            print(f"在当前页面找到 {len(direct_magnets)} 个磁力链接")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_magnet_links = []
        for magnet in magnet_links:
            if magnet not in seen:
                seen.add(magnet)
                unique_magnet_links.append(magnet)
        
        return unique_magnet_links
        
    except Exception as e:
        print(f"抓取页面失败: {e}")
        return magnet_links

def save_magnet_links(magnet_links, filename="magnet_links.txt"):
    """Save magnet links to a file with proper encoding"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            for i, magnet in enumerate(magnet_links, 1):
                # Ensure proper encoding when writing
                f.write(f"{i}. {magnet}\n\n")
        print(f"磁力链接已保存到 {filename}")
        return True
    except Exception as e:
        print(f"保存文件失败: {e}")
        return False

def main():
    # The URL from your request
    url = "https://www.dygod.net/e/search/result/index.php?page=80&searchid=97801"
    
    print("开始抓取磁力链接...")
    magnet_links = scrape_magnet_links(url)
    
    if magnet_links:
        print(f"\n总共找到 {len(magnet_links)} 个磁力链接:")
        for i, magnet in enumerate(magnet_links, 1):
            try:
                # Try to display with proper encoding
                print(f"{i}. {magnet}")
            except UnicodeEncodeError:
                # Fallback for problematic characters
                print(f"{i}. {magnet.encode('utf-8', errors='replace').decode('utf-8')}")
        
        # Save to file
        save_magnet_links(magnet_links)
    else:
        print("\n未找到任何磁力链接")
        print("可能的原因:")
        print("1. 网站结构发生变化")
        print("2. 需要登录才能访问下载链接")
        print("3. 网站有反爬虫机制")
        print("4. 磁力链接可能在具体的电影详情页面中")

if __name__ == "__main__":
    main()