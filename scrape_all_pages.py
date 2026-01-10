#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scrape all magnet download links from dygod.net search results across all pages
Enhanced version for bulk scraping ~6000 movies
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import json
import os
from urllib.parse import urljoin, urlparse, parse_qs
import random

class DygodBulkScraper:
    def __init__(self):
        self.base_url = "https://www.dygod.net"
        self.search_base = "/e/search/result/index.php"
        self.magnet_links = []
        self.failed_pages = []
        self.processed_movies = set()
        self.session = requests.Session()
        
        # Enhanced headers with rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
        
        self.headers_template = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def get_headers(self):
        """Get randomized headers"""
        headers = self.headers_template.copy()
        headers['User-Agent'] = random.choice(self.user_agents)
        return headers
    
    def get_total_pages(self, searchid):
        """Get total number of pages for the search"""
        url = f"{self.base_url}{self.search_base}?page=1&searchid={searchid}"
        try:
            response = self.session.get(url, headers=self.get_headers(), timeout=30)
            response.encoding = response.apparent_encoding or 'utf-8'
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser', from_encoding=response.encoding)
                
                # Look for pagination info
                pagination = soup.find('div', class_='pages') or soup.find('div', class_='pagebox')
                if pagination:
                    page_links = pagination.find_all('a')
                    max_page = 1
                    for link in page_links:
                        href = link.get('href', '')
                        if 'page=' in href:
                            try:
                                page_num = int(re.search(r'page=(\d+)', href).group(1))
                                max_page = max(max_page, page_num)
                            except:
                                pass
                    return max_page
                
                # Alternative: check if there's a "下一页" link
                next_page = soup.find('a', text=re.compile(r'下一页|下页|next', re.I))
                if next_page:
                    # Estimate based on content density
                    movie_count = len(soup.find_all('div', class_='co_content8') or soup.find_all('div', class_='co_area2'))
                    if movie_count > 0:
                        estimated_total = 6000  # Based on user input
                        movies_per_page = movie_count
                        return min(estimated_total // movies_per_page + 1, 300)  # Cap at 300 pages
                        
        except Exception as e:
            print(f"获取总页数失败: {e}")
        
        return 300  # Default estimate
    
    def extract_movie_links_from_page(self, page_content):
        """Extract movie page URLs from search results page"""
        movie_links = []
        soup = BeautifulSoup(page_content, 'html.parser')
        
        # Find movie entries
        movie_entries = soup.find_all('div', class_='co_content8') or soup.find_all('div', class_='co_area2')
        
        if movie_entries:
            for entry in movie_entries:
                links = entry.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    text = link.get_text().strip()
                    
                    # Filter movie links
                    if any(keyword in text.lower() for keyword in ['蓝光', '中英', '国粤', '中字']) or \
                       any(keyword in href for keyword in ['/html/', '/html/gndy/', '/html/dyzz/']):
                        
                        if href.startswith('/'):
                            movie_url = f"{self.base_url}{href}"
                        elif href.startswith('http'):
                            movie_url = href
                        else:
                            continue
                            
                        movie_links.append((text, movie_url))
        else:
            # Fallback: find all links and filter
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link['href']
                text = link.get_text().strip()
                
                if any(keyword in text.lower() for keyword in ['蓝光', '中英', '国粤', '中字']) or \
                   any(keyword in href for keyword in ['/html/', '/html/gndy/', '/html/dyzz/']):
                    
                    if href.startswith('/'):
                        movie_url = f"{self.base_url}{href}"
                    elif href.startswith('http'):
                        movie_url = href
                    else:
                        continue
                        
                    movie_links.append((text, movie_url))
        
        return movie_links
    
    def extract_magnet_from_movie_page(self, movie_url, movie_title):
        """Extract magnet links from individual movie page"""
        magnet_links = []
        
        try:
            response = self.session.get(movie_url, headers=self.get_headers(), timeout=20)
            response.encoding = response.apparent_encoding or 'utf-8'
            
            if response.status_code == 200:
                # Use regex to find magnet links
                magnet_pattern = re.compile(r'magnet:\?[^"\'<>\\s]+')
                magnets_in_page = magnet_pattern.findall(response.text)
                
                if magnets_in_page:
                    magnet_links.extend(magnets_in_page)
                    print(f"  找到 {len(magnets_in_page)} 个磁力链接: {movie_title}")
                else:
                    # Try to find download links
                    soup = BeautifulSoup(response.content, 'html.parser', from_encoding=response.encoding)
                    download_links = soup.find_all('a', href=True)
                    
                    for dl_link in download_links:
                        href = dl_link['href']
                        text = dl_link.get_text().strip()
                        
                        if 'magnet' in href.lower():
                            magnet_links.append(href)
                        elif any(keyword in text.lower() for keyword in ['迅雷', '磁力', 'magnet']):
                            onclick = dl_link.get('onclick', '')
                            magnet_match = magnet_pattern.search(onclick)
                            if magnet_match:
                                magnet_links.append(magnet_match.group())
                
                # Also check for magnet links in the page content directly
                page_magnets = magnet_pattern.findall(response.text)
                if page_magnets:
                    magnet_links.extend(page_magnets)
                
        except Exception as e:
            print(f"  处理电影页面失败 {movie_title}: {e}")
        
        return list(set(magnet_links))  # Remove duplicates
    
    def process_search_page(self, page_num, searchid):
        """Process a single search results page"""
        url = f"{self.base_url}{self.search_base}?page={page_num}&searchid={searchid}"
        print(f"正在处理第 {page_num} 页: {url}")
        
        try:
            response = self.session.get(url, headers=self.get_headers(), timeout=30)
            response.encoding = response.apparent_encoding or 'utf-8'
            
            if response.status_code == 200:
                movie_links = self.extract_movie_links_from_page(response.content)
                print(f"  找到 {len(movie_links)} 部电影")
                
                page_magnets = []
                for i, (movie_title, movie_url) in enumerate(movie_links, 1):
                    if movie_url not in self.processed_movies:
                        print(f"  处理第 {i}/{len(movie_links)} 部电影: {movie_title}")
                        magnets = self.extract_magnet_from_movie_page(movie_url, movie_title)
                        page_magnets.extend(magnets)
                        self.processed_movies.add(movie_url)
                        
                        # Random delay to be respectful
                        time.sleep(random.uniform(0.5, 2.0))
                    else:
                        print(f"  跳过已处理的电影: {movie_title}")
                
                return page_magnets
            else:
                print(f"  页面访问失败，状态码: {response.status_code}")
                self.failed_pages.append(page_num)
                return []
                
        except Exception as e:
            print(f"  处理第 {page_num} 页失败: {e}")
            self.failed_pages.append(page_num)
            return []
    
    def save_progress(self, filename="bulk_magnet_links.txt"):
        """Save current progress"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for i, magnet in enumerate(self.magnet_links, 1):
                    f.write(f"{i}. {magnet}\n\n")
            print(f"进度已保存到 {filename}，共 {len(self.magnet_links)} 个磁力链接")
            return True
        except Exception as e:
            print(f"保存文件失败: {e}")
            return False
    
    def save_state(self, filename="scraper_state.json"):
        """Save scraper state for resume capability"""
        state = {
            'processed_movies': list(self.processed_movies),
            'failed_pages': self.failed_pages,
            'magnet_links': self.magnet_links,
            'total_processed': len(self.magnet_links)
        }
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            print(f"状态已保存到 {filename}")
        except Exception as e:
            print(f"保存状态失败: {e}")
    
    def load_state(self, filename="scraper_state.json"):
        """Load scraper state for resume"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                self.processed_movies = set(state.get('processed_movies', []))
                self.failed_pages = state.get('failed_pages', [])
                self.magnet_links = state.get('magnet_links', [])
                print(f"状态已加载，已处理 {len(self.processed_movies)} 部电影，{len(self.magnet_links)} 个磁力链接")
                return True
        except Exception as e:
            print(f"加载状态失败: {e}")
        return False
    
    def scrape_all_pages(self, searchid, start_page=1, end_page=None, resume=False):
        """Scrape all pages or specified range"""
        
        # Load state if resuming
        if resume:
            self.load_state()
        
        # Get total pages if not specified
        if not end_page:
            print("正在获取总页数...")
            end_page = self.get_total_pages(searchid)
            print(f"估计总页数: {end_page}")
        
        print(f"开始抓取第 {start_page} 到 {end_page} 页，共 {end_page - start_page + 1} 页")
        
        # Process pages
        for page_num in range(start_page, end_page + 1):
            if page_num in self.failed_pages:
                print(f"跳过之前失败的第 {page_num} 页")
                continue
            
            print(f"\n{'='*60}")
            print(f"处理第 {page_num}/{end_page} 页 (进度: {((page_num-start_page+1)/(end_page-start_page+1)*100):.1f}%)")
            print(f"{'='*60}")
            
            page_magnets = self.process_search_page(page_num, searchid)
            self.magnet_links.extend(page_magnets)
            
            # Save progress every 5 pages
            if page_num % 5 == 0:
                self.save_progress()
                self.save_state()
            
            # Random delay between pages
            if page_num < end_page:
                delay = random.uniform(2, 5)
                print(f"等待 {delay:.1f} 秒后继续...")
                time.sleep(delay)
        
        # Final save
        self.save_progress()
        self.save_state()
        
        print(f"\n{'='*60}")
        print(f"抓取完成！")
        print(f"总共处理: {len(self.processed_movies)} 部电影")
        print(f"总共获取: {len(self.magnet_links)} 个磁力链接")
        print(f"失败页面: {len(self.failed_pages)} 页")
        if self.failed_pages:
            print(f"失败页码: {self.failed_pages}")
        print(f"{'='*60}")

def main():
    scraper = DygodBulkScraper()
    
    # Configuration
    searchid = "97801"  # From the original URL
    start_page = 1
    # For testing, let's start with first 10 pages, then you can expand
    end_page = 10  # You can increase this gradually
    
    print("🎬 电影天堂批量磁力链接抓取工具")
    print("=" * 60)
    print(f"搜索ID: {searchid}")
    print(f"起始页: {start_page}")
    print(f"结束页: {end_page}")
    print("=" * 60)
    
    # Start scraping
    scraper.scrape_all_pages(searchid, start_page, end_page, resume=True)

if __name__ == "__main__":
    main()