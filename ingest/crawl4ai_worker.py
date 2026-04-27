"""
Crawl4AI Worker - Web extraction from URLs
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CrawlResult:
    """Result of URL crawling"""
    url: str
    text: str
    metadata: Dict[str, Any]
    success: bool
    error: Optional[str] = None

class Crawl4AIWorker:
    """
    Extracts content from URLs using Crawl4AI.
    Cleans and structures web content for RAG.
    """
    
    def __init__(self):
        self.session = None
    
    async def crawl(self, url: str) -> CrawlResult:
        """
        Crawl a single URL.
        
        Args:
            url: URL to crawl
            
        Returns:
            CrawlResult with extracted content
        """
        try:
            from crawl4ai import AsyncWebCrawler
            
            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.araw_fetch(url)
                
                if not result.success:
                    return CrawlResult(
                        url=url,
                        text="",
                        metadata={},
                        success=False,
                        error=result.error_message
                    )
                
                # Extract structured content
                return CrawlResult(
                    url=url,
                    text=result.markdown or result.html,
                    metadata={
                        "source": url,
                        "doc_type": "web",
                        "title": result.metadata.get("title", ""),
                        "description": result.metadata.get("description", ""),
                        "language": result.metadata.get("language", "unknown")
                    },
                    success=True
                )
                
        except ImportError:
            return self._crawl_fallback(url)
        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            return CrawlResult(
                url=url,
                text="",
                metadata={"source": url},
                success=False,
                error=str(e)
            )
    
    def _crawl_fallback(self, url: str) -> CrawlResult:
        """Fallback crawling with requests + BeautifulSoup"""
        import requests
        from bs4 import BeautifulSoup
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; DuneRAG/1.0)"
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove scripts and styles
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            
            # Extract main content
            title = soup.title.string if soup.title else ""
            
            # Try to find main content
            main = soup.find("main") or soup.find("article") or soup.find("div", class_="content")
            if main:
                text = main.get_text(separator="\n\n", strip=True)
            else:
                text = soup.get_text(separator="\n\n", strip=True)
            
            # Clean up whitespace
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            text = "\n\n".join(lines)
            
            return CrawlResult(
                url=url,
                text=text[:50000],  # Limit to 50k chars
                metadata={
                    "source": url,
                    "doc_type": "web",
                    "title": title
                },
                success=True
            )
            
        except Exception as e:
            return CrawlResult(
                url=url,
                text="",
                metadata={"source": url},
                success=False,
                error=str(e)
            )
    
    async def crawl_batch(self, urls: List[str]) -> List[CrawlResult]:
        """Crawl multiple URLs concurrently"""
        tasks = [self.crawl(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to CrawlResult
        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed.append(CrawlResult(
                    url=urls[i],
                    text="",
                    metadata={"source": urls[i]},
                    success=False,
                    error=str(result)
                ))
            else:
                processed.append(result)
        
        return processed
    
    def crawl_sync(self, url: str) -> CrawlResult:
        """Synchronous wrapper for crawl"""
        return asyncio.run(self.crawl(url))