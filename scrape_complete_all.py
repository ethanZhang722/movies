#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整版：抓取所有6000部电影的磁力链接
分批处理，支持断点续传
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import json
import os
from urllib.parse import urljoin, urlparse, parse_qs
import random

class CompleteDygodScraper:
    def __init__(self):
        self.base_url = "https://www.dygod.net"
        self.search_base = "/e/search/result/index.php"
        self.magnet_links = []
        self.failed_pages = []
        self.processed_movies = set()
        self.session = requests.Session()
        self.stats = {
            'total_pages': 0,
            'processed_pages': 0,
            'total_movies': 0,
            'total_magnets': 0,
            'failed_movies': 0
        }
        
        # Enhanced headers with rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
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
    
    def estimate_total_pages(self, searchid):
        """Estimate total pages based on content density"""
        print("正在估算总页数...")
        
        # Test first few pages to estimate
        total_movies_found = 0
        pages_tested = 0
        
        for test_page in [1, 10, 50, 100]:
            try:
                url = f"{self.base_url}{self.search_base}?page={test_page}&searchid={searchid}"
                response = self.session.get(url, headers=self.get_headers(), timeout=30)
                response.encoding = response.apparent_encoding or 'utf-8'
                
                if response.status_code == 200:
                    movie_links = self.extract_movie_links_from_page(response.content)
                    movies_on_page = len(movie_links)
                    
                    if movies_on_page > 0:
                        total_movies_found += movies_on_page
                        pages_tested += 1
                        print(f"  第 {test_page} 页: {movies_on_page} 部电影")
                        
                        # If we found movies, estimate more pages exist
                        if test_page == 1 and movies_on_page >= 20:
                            # Based on user saying ~6000 movies, estimate ~300 pages
                            estimated_pages = 300
                            print(f"  估算总页数: {estimated_pages} 页 (约 {estimated_pages * 20} 部电影)")
                            return estimated_pages
                    else:
                        print(f"  第 {test_page} 页: 无电影数据")
                        break
                        
            except Exception as e:
                print(f"  测试第 {test_page} 页失败: {e}")
                continue
            
            time.sleep(2)  # Be respectful
        
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
                    # Decode magnet links
                    from urllib.parse import unquote
                    decoded_magnets = []
                    for magnet in magnets_in_page:
                        try:
                            decoded_magnet = unquote(magnet)
                            decoded_magnets.append(decoded_magnet)
                        except:
                            decoded_magnets.append(magnet)
                    
                    magnet_links.extend(decoded_magnets)
                    print(f"  找到 {len(decoded_magnets)} 个磁力链接: {movie_title[:30]}...")
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
            print(f"  处理电影页面失败 {movie_title[:30]}...: {e}")
            self.stats['failed_movies'] += 1
        
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
                        print(f"  处理第 {i}/{len(movie_links)} 部电影: {movie_title[:40]}...")
                        magnets = self.extract_magnet_from_movie_page(movie_url, movie_title)
                        page_magnets.extend(magnets)
                        self.processed_movies.add(movie_url)
                        self.stats['total_movies'] += 1
                        
                        # Random delay to be respectful
                        delay = random.uniform(0.5, 2.0)
                        time.sleep(delay)
                    else:
                        print(f"  跳过已处理的电影: {movie_title[:40]}...")
                
                self.stats['processed_pages'] += 1
                return page_magnets
            else:
                print(f"  页面访问失败，状态码: {response.status_code}")
                self.failed_pages.append(page_num)
                return []
                
        except Exception as e:
            print(f"  处理第 {page_num} 页失败: {e}")
            self.failed_pages.append(page_num)
            return []
    
    def save_progress(self, filename="complete_magnet_links.txt"):
        """Save current progress"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for i, magnet in enumerate(self.magnet_links, 1):
                    f.write(f"{i}. {magnet}\n\n")
            
            print(f"\n📁 进度已保存到 {filename}")
            print(f"📊 统计信息:")
            print(f"   总页数: {self.stats['total_pages']}")
            print(f"   已处理页数: {self.stats['processed_pages']}")
            print(f"   总电影数: {self.stats['total_movies']}")
            print(f"   总磁力链接: {len(self.magnet_links)}")
            print(f"   失败电影: {self.stats['failed_movies']}")
            return True
        except Exception as e:
            print(f"保存文件失败: {e}")
            return False
    
    def save_state(self, filename="complete_scraper_state.json"):
        """Save scraper state for resume capability"""
        state = {
            'processed_movies': list(self.processed_movies),
            'failed_pages': self.failed_pages,
            'magnet_links': self.magnet_links,
            'stats': self.stats,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            print(f"💾 状态已保存到 {filename}")
        except Exception as e:
            print(f"保存状态失败: {e}")
    
    def load_state(self, filename="complete_scraper_state.json"):
        """Load scraper state for resume"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                self.processed_movies = set(state.get('processed_movies', []))
                self.failed_pages = state.get('failed_pages', [])
                self.magnet_links = state.get('magnet_links', [])
                self.stats = state.get('stats', self.stats)
                print(f"📂 状态已加载")
                print(f"   已处理电影: {len(self.processed_movies)}")
                print(f"   已获取磁力链接: {len(self.magnet_links)}")
                print(f"   失败页面: {len(self.failed_pages)}")
                return True
        except Exception as e:
            print(f"加载状态失败: {e}")
        return False
    
    def scrape_all_pages(self, searchid, start_page=1, end_page=None, batch_size=50, resume=False):
        """Scrape all pages or specified range with batch processing"""
        
        # Load state if resuming
        if resume:
            self.load_state()
        
        # Get total pages if not specified
        if not end_page:
            print("正在估算总页数...")
            end_page = self.estimate_total_pages(searchid)
        
        self.stats['total_pages'] = end_page
        
        print(f"🚀 开始抓取第 {start_page} 到 {end_page} 页，共 {end_page - start_page + 1} 页")
        print(f"📊 预计总电影数: ~{end_page * 20} 部")
        print(f"📦 每批处理: {batch_size} 页")
        
        # Process in batches
        current_batch = 0
        for page_num in range(start_page, end_page + 1):
            if page_num in self.failed_pages:
                print(f"⏭️  跳过之前失败的第 {page_num} 页")
                continue
            
            print(f"\n{'='*80}")
            print(f"📄 处理第 {page_num}/{end_page} 页 (进度: {((page_num-start_page+1)/(end_page-start_page+1)*100):.1f}%)")
            print(f"{'='*80}")
            
            page_magnets = self.process_search_page(page_num, searchid)
            self.magnet_links.extend(page_magnets)
            self.stats['total_magnets'] = len(self.magnet_links)
            
            # Save progress every batch_size pages
            if page_num % batch_size == 0:
                self.save_progress(f"batch_{current_batch}_magnet_links.txt")
                self.save_state()
                current_batch += 1
                
                print(f"\n🎯 第 {current_batch} 批完成！")
                print(f"   已处理: {page_num} 页")
                print(f"   已获取: {len(self.magnet_links)} 个磁力链接")
                print(f"   预计剩余时间: {((end_page - page_num) * 0.5 / 60):.1f} 小时")
            
            # Longer delay between pages to be more respectful
            if page_num < end_page:
                delay = random.uniform(1, 3)
                print(f"⏱️  等待 {delay:.1f} 秒后继续...")
                time.sleep(delay)
        
        # Final save
        self.save_progress("complete_all_magnet_links.txt")
        self.save_state()
        
        print(f"\n{'='*80}")
        print(f"🎉 抓取完成！")
        print(f"📊 最终统计:")
        print(f"   总页数: {self.stats['total_pages']}")
        print(f"   已处理页数: {self.stats['processed_pages']}")
        print(f"   总电影数: {self.stats['total_movies']}")
        print(f"   总磁力链接: {len(self.magnet_links)}")
        print(f"   失败页面: {len(self.failed_pages)}")
        if self.failed_pages:
            print(f"   失败页码: {self.failed_pages}")
        print(f"{'='*80}")

def main():
    scraper = CompleteDygodScraper()
    
    # Configuration for complete scraping
    searchid = "97801"  # From the original URL
    start_page = 1
    end_page = 300  # Estimated 300 pages for ~6000 movies
    batch_size = 20  # Save every 20 pages
    
    print("🎬 电影天堂完整版批量磁力链接抓取工具")
    print("=" * 80)
    print(f"🎯 搜索ID: {searchid}")
    print(f"📄 起始页: {start_page}")
    print(f"📄 结束页: {end_page}")
    print(f"📦 批处理大小: {batch_size}")
    print(f"🎥 预计电影数: ~{end_page * 20} 部")
    print("=" * 80)
    print("⚠️  这将是一个长时间运行的任务，建议：")
    print("   1. 保持网络连接稳定")
    print("   2. 定期检查进度文件")
    print("   3. 可以随时中断，支持断点续传")
    print("=" * 80)
    
    # Ask for confirmation
    response = input("是否开始完整抓取？(y/N): ")
    if response.lower() == 'y':
        # Start scraping
        scraper.scrape_all_pages(searchid, start_page, end_page, batch_size, resume=True)
    else:
        print("任务已取消。您可以修改配置后重新运行。")

if __name__ == "__main__":
    main()