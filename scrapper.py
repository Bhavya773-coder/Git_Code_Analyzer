import os
import tempfile
import shutil
from git import Repo
from pathlib import Path
import magic
from typing import Dict, List, Optional, Tuple
import re
import logging
from llm_summarizer import LLM_Summarize
from tqdm import tqdm
import hashlib
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GitHubScraper")

class GitHubScraper:
    def __init__(self):
        self.temp_dir = None
        self.repo_path = None
        self.cache_dir = os.path.join(os.path.expanduser("~"), ".git_analyzer_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize the LLM summarizer
        try:
            self.summarizer = LLM_Summarize()
            logger.info("Successfully initialized LLM summarizer")
        except Exception as e:
            logger.error(f"Failed to initialize LLM summarizer: {e}")
            raise

    def get_cache_key(self, repo_url: str) -> str:
        """Generate a cache key for the repository."""
        return hashlib.md5(repo_url.encode()).hexdigest()

    def get_cached_summaries(self, repo_url: str) -> Optional[Tuple[List[Dict], int]]:
        """Get cached summaries if they exist."""
        cache_key = self.get_cache_key(repo_url)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    logger.info("Using cached summaries")
                    return data['summaries'], data['total_files']
            except Exception as e:
                logger.error(f"Error reading cache: {e}")
        return None

    def save_to_cache(self, repo_url: str, summaries: List[Dict], total_files: int):
        """Save summaries to cache."""
        cache_key = self.get_cache_key(repo_url)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    'summaries': summaries,
                    'total_files': total_files
                }, f)
            logger.info("Saved summaries to cache")
        except Exception as e:
            logger.error(f"Error saving to cache: {e}")

    def clone_repository(self, repo_url: str) -> None:
        """Clone the GitHub repository to a temporary directory."""
        try:
            self.temp_dir = tempfile.mkdtemp()
            logger.info(f"Cloning repository to {self.temp_dir}")
            Repo.clone_from(repo_url, self.temp_dir)
            self.repo_path = self.temp_dir
            logger.info("Repository cloned successfully")
        except Exception as e:
            logger.error(f"Failed to clone repository: {e}")
            raise

    def get_file_type(self, file_path: str) -> str:
        """Determine the type of file using python-magic."""
        try:
            mime = magic.Magic(mime=True)
            return mime.from_file(file_path)
        except Exception as e:
            logger.error(f"Error determining file type for {file_path}: {e}")
            return "application/octet-stream"

    def is_text_file(self, file_path: str) -> bool:
        """Check if the file is a text file."""
        try:
            mime = self.get_file_type(file_path)
            return mime.startswith('text/') or mime in ['application/json', 'application/xml']
        except Exception as e:
            logger.error(f"Error checking if file is text: {e}")
            return False

    def should_skip_file(self, file_path: str) -> bool:
        """Determine if a file should be skipped based on various criteria."""
        # Skip hidden files and directories
        if any(part.startswith('.') for part in Path(file_path).parts):
            return True
            
        # Skip binary files
        if not self.is_text_file(file_path):
            return True
            
        # Skip files in certain directories
        skip_dirs = {
            '.git', 'node_modules', '__pycache__', 'venv', 'env', 'dist', 'build',
            'target', '.idea', '.vscode', 'coverage', 'docs', 'tests', 'test'
        }
        if any(skip_dir in Path(file_path).parts for skip_dir in skip_dirs):
            return True
            
        # Skip files larger than 100KB
        try:
            if os.path.getsize(file_path) > 100 * 1024:  # 100KB
                return True
        except Exception:
            return True
            
        # Skip files with certain extensions
        skip_extensions = {
            '.min.js', '.min.css', '.map', '.lock', '.log', '.sqlite', '.db',
            '.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib'
        }
        if Path(file_path).suffix.lower() in skip_extensions:
            return True
            
        return False

    def get_file_summary(self, file_path: str) -> Dict:
        """Generate a summary for a single file."""
        try:
            file_stats = os.stat(file_path)
            file_size = file_stats.st_size
            file_type = self.get_file_type(file_path)
            
            summary = {
                'path': os.path.relpath(file_path, self.repo_path),
                'size': file_size,
                'type': file_type,
                'is_text': self.is_text_file(file_path),
                'summary': None
            }

            if summary['is_text']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # Skip single line files or very short files
                    if len(lines) <= 3:
                        summary['summary'] = "File too short - skipping summary"
                        return summary
                    
                    # Count lines of code (excluding comments and empty lines)
                    summary['loc'] = len([l for l in lines if l.strip() and not l.strip().startswith(('#', '//', '/*', '*', '*/'))])
                    
                    # Only generate summary for files with significant content
                    if summary['loc'] > 5:
                        # Generate summary using the LLM
                        summary['summary'] = self.summarizer.summarize_code(content)
                    
                    # Try to detect language based on file extension
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in ['.py']:
                        summary['language'] = 'Python'
                    elif ext in ['.js', '.jsx']:
                        summary['language'] = 'JavaScript'
                    elif ext in ['.ts', '.tsx']:
                        summary['language'] = 'TypeScript'
                    elif ext in ['.java']:
                        summary['language'] = 'Java'
                    elif ext in ['.cpp', '.cc', '.cxx']:
                        summary['language'] = 'C++'
                    elif ext in ['.c']:
                        summary['language'] = 'C'
                    elif ext in ['.go']:
                        summary['language'] = 'Go'
                    elif ext in ['.rb']:
                        summary['language'] = 'Ruby'
                    elif ext in ['.html', '.htm']:
                        summary['language'] = 'HTML'
                    elif ext in ['.css']:
                        summary['language'] = 'CSS'
                    elif ext in ['.md']:
                        summary['language'] = 'Markdown'
                    elif ext in ['.json']:
                        summary['language'] = 'JSON'
                    elif ext in ['.xml']:
                        summary['language'] = 'XML'
                    elif ext in ['.yaml', '.yml']:
                        summary['language'] = 'YAML'
                    else:
                        summary['language'] = 'Unknown'

            return summary
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return {
                'path': os.path.relpath(file_path, self.repo_path),
                'error': str(e)
            }

    def get_all_files(self) -> List[str]:
        """Get all files in the repository that should be analyzed."""
        if not self.repo_path:
            raise ValueError("Repository not cloned. Call clone_repository first.")
            
        files_to_analyze = []
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                file_path = os.path.join(root, file)
                if not self.should_skip_file(file_path):
                    files_to_analyze.append(file_path)
        return files_to_analyze

    def analyze_repository(self, repo_url: str) -> Tuple[List[Dict], int]:
        """
        Analyze all files in the repository.
        
        Returns:
            Tuple[List[Dict], int]: List of summaries and total number of files analyzed
        """
        # Check cache first
        cached_result = self.get_cached_summaries(repo_url)
        if cached_result:
            return cached_result

        if not self.repo_path:
            raise ValueError("Repository not cloned. Call clone_repository first.")

        summaries = []
        code_contents = []
        
        try:
            # Get all files to analyze
            files_to_analyze = self.get_all_files()
            total_files = len(files_to_analyze)
            
            if total_files == 0:
                logger.warning("No files found to analyze")
                return [], 0
            
            logger.info(f"Found {total_files} files to analyze")
            
            # Analyze each file
            for file_path in tqdm(files_to_analyze, desc="Analyzing files"):
                summary = self.get_file_summary(file_path)
                summaries.append(summary)
                
                if summary['is_text'] and not summary.get('error'):
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        code_contents.append(f.read())

            # Generate overall repository summary
            if code_contents:
                logger.info("Generating repository summary...")
                repo_summary = self.summarizer.summarize_repo(code_contents)
                summaries.append({
                    'path': 'REPOSITORY_SUMMARY',
                    'summary': repo_summary,
                    'type': 'html'
                })
                logger.info("Repository summary generated successfully")

            # Save to cache
            self.save_to_cache(repo_url, summaries, total_files)

            return summaries, total_files
            
        except Exception as e:
            logger.error(f"Error analyzing repository: {e}")
            raise

    def cleanup(self):
        """Clean up temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.info("Temporary directory cleaned up successfully")
            except Exception as e:
                logger.error(f"Error cleaning up temporary directory: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

def main():
    # Example usage
    try:
        repo_url = input("Enter GitHub repository URL: ")
        
        with GitHubScraper() as scraper:
            scraper.clone_repository(repo_url)
            summaries, total_files = scraper.analyze_repository(repo_url)
            
            print(f"\nAnalyzed {total_files} files")
            print("\nRepository Analysis Results:")
            print("=" * 80)
            
            for summary in summaries:
                if summary['path'] == 'REPOSITORY_SUMMARY':
                    print("\nOverall Repository Summary:")
                    print("=" * 80)
                    print(summary['summary'])
                    continue
                    
                print(f"\nFile: {summary['path']}")
                print(f"Type: {summary['type']}")
                print(f"Size: {summary['size']} bytes")
                
                if 'language' in summary:
                    print(f"Language: {summary['language']}")
                
                if 'loc' in summary:
                    print(f"Lines of Code: {summary['loc']}")
                
                if summary['is_text'] and summary['summary']:
                    print("\nSummary:")
                    print("-" * 40)
                    print(summary['summary'])
                    print("-" * 40)
                
                if 'error' in summary:
                    print(f"Error: {summary['error']}")
                    
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()