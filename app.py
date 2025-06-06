import streamlit as st
import tempfile
import os
from scrapper import GitHubScraper
from llm_summarizer import LLM_Summarize
import logging
from pathlib import Path
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("StreamlitApp")

# Set page config
st.set_page_config(
    page_title="GitHub Repository Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS with theme support
st.markdown("""
    <style>
    /* Main container */
    .main {
        padding: 2rem;
    }
    
    /* Button styling */
    .stButton>button {
        width: 100%;
        background-color: var(--primary-color);
        color: var(--text-color);
        border: none;
        padding: 10px 20px;
        border-radius: 5px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: var(--primary-color-hover);
    }
    
    /* Summary boxes */
    .summary-box {
        background-color: var(--background-color);
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid var(--primary-color);
        color: var(--text-color);
    }
    
    /* File boxes */
    .file-box {
        background-color: var(--background-color);
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 0.8rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid var(--border-color);
        transition: transform 0.2s;
        color: var(--text-color);
    }
    .file-box:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    /* Language badges */
    .language-badge {
        display: inline-block;
        padding: 0.35rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.875rem;
        font-weight: 600;
        margin-right: 0.5rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    /* Language colors - using fixed colors for better visibility */
    .python { background-color: #3572A5; color: white; }
    .javascript { background-color: #f7df1e; color: black; }
    .typescript { background-color: #2b7489; color: white; }
    .java { background-color: #b07219; color: white; }
    .cpp { background-color: #f34b7d; color: white; }
    .c { background-color: #555555; color: white; }
    .go { background-color: #00ADD8; color: white; }
    .ruby { background-color: #701516; color: white; }
    .html { background-color: #e34c26; color: white; }
    .css { background-color: #563d7c; color: white; }
    .markdown { background-color: #083fa1; color: white; }
    .json { background-color: #292929; color: white; }
    .xml { background-color: #f16529; color: white; }
    .yaml { background-color: #cb171e; color: white; }
    .unknown { background-color: #6c757d; color: white; }
    
    /* Headers */
    h1, h2, h3 {
        color: var(--text-color);
        font-weight: 600;
    }
    
    /* Stats cards */
    .stats-card {
        background-color: var(--background-color);
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        color: var(--text-color);
        border: 1px solid var(--border-color);
    }
    
    /* Search box */
    .stTextInput>div>div>input {
        border-radius: 0.5rem;
        border: 1px solid var(--border-color);
        padding: 0.5rem;
        background-color: var(--background-color);
        color: var(--text-color);
    }
    
    /* Progress bar */
    .stProgress>div>div>div {
        background-color: var(--primary-color);
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem 0;
        color: var(--text-color);
        font-size: 0.9rem;
        opacity: 0.8;
    }

    /* CSS Variables for theme support */
    :root {
        --primary-color: #4CAF50;
        --primary-color-hover: #45a049;
        --background-color: #ffffff;
        --text-color: #262730;
        --border-color: #e0e0e0;
    }

    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
        :root {
            --background-color: #0e1117;
            --text-color: #fafafa;
            --border-color: #2e3338;
        }
        
        .file-box, .summary-box, .stats-card {
            background-color: #1e2228;
        }
        
        .stTextInput>div>div>input {
            background-color: #1e2228;
        }
    }
    </style>
""", unsafe_allow_html=True)

def get_language_class(language: str) -> str:
    """Get CSS class for language badge"""
    language = language.lower()
    if language == 'python':
        return 'python'
    elif language == 'javascript':
        return 'javascript'
    elif language == 'typescript':
        return 'typescript'
    elif language == 'java':
        return 'java'
    elif language == 'c++':
        return 'cpp'
    elif language == 'c':
        return 'c'
    elif language == 'go':
        return 'go'
    elif language == 'ruby':
        return 'ruby'
    elif language == 'html':
        return 'html'
    elif language == 'css':
        return 'css'
    elif language == 'markdown':
        return 'markdown'
    elif language == 'json':
        return 'json'
    elif language == 'xml':
        return 'xml'
    elif language == 'yaml':
        return 'yaml'
    return 'unknown'

def format_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def display_stats(summaries):
    """Display repository statistics"""
    total_files = len([s for s in summaries if s['path'] != 'REPOSITORY_SUMMARY'])
    total_size = sum(s['size'] for s in summaries if s['path'] != 'REPOSITORY_SUMMARY')
    total_loc = sum(s.get('loc', 0) for s in summaries if s['path'] != 'REPOSITORY_SUMMARY')
    
    # Count files by language
    language_counts = {}
    for s in summaries:
        if s['path'] != 'REPOSITORY_SUMMARY' and 'language' in s:
            lang = s['language']
            language_counts[lang] = language_counts.get(lang, 0) + 1
    
    # Display stats in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
            <div class="stats-card">
                <h3>📁 Files</h3>
                <p style="font-size: 1.5rem; font-weight: bold;">{total_files:,}</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="stats-card">
                <h3>📊 Size</h3>
                <p style="font-size: 1.5rem; font-weight: bold;">{format_size(total_size)}</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="stats-card">
                <h3>📝 Lines of Code</h3>
                <p style="font-size: 1.5rem; font-weight: bold;">{total_loc:,}</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
            <div class="stats-card">
                <h3>🔤 Languages</h3>
                <p style="font-size: 1.5rem; font-weight: bold;">{len(language_counts)}</p>
            </div>
        """, unsafe_allow_html=True)
    
    # Display language distribution
    if language_counts:
        st.markdown("### 📊 Language Distribution")
        for lang, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_files) * 100
            st.markdown(f"""
                <div style="margin: 0.5rem 0;">
                    <div style="display: flex; align-items: center;">
                        <span class="language-badge {get_language_class(lang)}">{lang}</span>
                        <div style="flex-grow: 1; margin: 0 1rem;">
                            <div style="background-color: var(--border-color); height: 8px; border-radius: 4px;">
                                <div style="background-color: var(--primary-color); width: {percentage}%; height: 100%; border-radius: 4px;"></div>
                            </div>
                        </div>
                        <span style="color: var(--text-color); opacity: 0.8;">{count} files ({percentage:.1f}%)</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

def display_file_summary(summary):
    """Display a single file summary in a formatted box"""
    with st.container():
        st.markdown(f"""
            <div class="file-box">
                <h3>{summary['path']}</h3>
                <p><strong>Type:</strong> {summary['type']}</p>
                <p><strong>Size:</strong> {format_size(summary['size'])}</p>
        """, unsafe_allow_html=True)
        
        if 'language' in summary:
            lang_class = get_language_class(summary['language'])
            st.markdown(f"<p><strong>Language:</strong> <span class='language-badge {lang_class}'>{summary['language']}</span></p>", unsafe_allow_html=True)
        
        if 'loc' in summary:
            st.markdown(f"<p><strong>Lines of Code:</strong> {summary['loc']:,}</p>", unsafe_allow_html=True)
        
        if summary['is_text'] and summary['summary']:
            st.markdown("<p><strong>Summary:</strong></p>", unsafe_allow_html=True)
            st.markdown(f"<div class='summary-box'>{summary['summary']}</div>", unsafe_allow_html=True)
        
        if 'error' in summary:
            st.error(f"Error: {summary['error']}")
        
        st.markdown("</div>", unsafe_allow_html=True)

def main():
    st.title("📊 GitHub Repository Analyzer")
    st.markdown("""
    This tool analyzes GitHub repositories and provides detailed summaries of the codebase.
    Enter a GitHub repository URL to get started.
    """)

    # Input for GitHub repository URL
    repo_url = st.text_input("GitHub Repository URL", placeholder="https://github.com/username/repository.git")

    if st.button("Analyze Repository"):
        if not repo_url:
            st.error("Please enter a GitHub repository URL")
            return

        try:
            # Create a placeholder for the progress bar
            progress_placeholder = st.empty()
            status_placeholder = st.empty()
            
            with st.spinner("Initializing..."):
                # Initialize the scraper
                scraper = GitHubScraper()
                
                # Clone repository
                progress_placeholder.progress(20)
                status_placeholder.text("Cloning repository...")
                scraper.clone_repository(repo_url)
                
                # Get files to analyze
                progress_placeholder.progress(40)
                status_placeholder.text("Scanning repository...")
                files_to_analyze = scraper.get_all_files()
                total_files = len(files_to_analyze)
                
                if total_files == 0:
                    st.warning("No files found to analyze in the repository.")
                    return
                
                # Analyze repository
                progress_placeholder.progress(60)
                status_placeholder.text(f"Analyzing {total_files} files...")
                summaries, analyzed_files = scraper.analyze_repository(repo_url)
                
                # Display results
                progress_placeholder.progress(80)
                status_placeholder.text("Generating summaries...")
                
                # Find and display repository summary first
                repo_summary = next((s for s in summaries if s['path'] == 'REPOSITORY_SUMMARY'), None)
                if repo_summary:
                    st.markdown("## 📝 Repository Overview")
                    st.markdown(repo_summary['summary'], unsafe_allow_html=True)
                
                # Display repository statistics
                display_stats(summaries)
                
                # Display file summaries
                st.markdown(f"## 📁 File Analysis ({analyzed_files} files)")
                
                # Add a search box for filtering files
                search_query = st.text_input("🔍 Search files", placeholder="Type to filter files...")
                
                # Filter and display file summaries
                filtered_summaries = [
                    s for s in summaries 
                    if s['path'] != 'REPOSITORY_SUMMARY' and 
                    (not search_query or search_query.lower() in s['path'].lower())
                ]
                
                for summary in filtered_summaries:
                    display_file_summary(summary)
                
                progress_placeholder.progress(100)
                status_placeholder.text("Analysis complete!")
                st.success(f"Successfully analyzed {analyzed_files} files!")
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            logger.error(f"Error in main: {e}")

    # Add footer
    st.markdown("---")
    st.markdown("""
        <div class="footer">
            <p>Built using Streamlit, Hugging Face Transformers, and Python</p>
            <p>Analyze your GitHub repositories with AI-powered code understanding</p>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 