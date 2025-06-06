import logging
from typing import List, Dict
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import torch
from pathlib import Path
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GenerateSummary")

class LLM_Summarize:
    """Perform all LLM operations using Hugging Face models"""

    def __init__(self, model_name: str = "facebook/bart-large-cnn", device: str = None):
        """
        Initialize the summarizer with a Hugging Face model
        
        Args:
            model_name: Name of the Hugging Face model to use
            device: Device to run the model on ('cuda' or 'cpu'). If None, will use GPU if available
        """
        self.device = device if device else ('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Using device: {self.device}")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            self.summarizer = pipeline(
                "summarization",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == 'cuda' else -1
            )
            logger.info(f"Successfully loaded model: {model_name}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise

        # Prompts for different summarization tasks
        self.code_summary_prompt = """Analyze and summarize the following code. Focus on:
        1. Main functionality
        2. Key components/classes
        3. Important methods/functions
        4. Overall purpose

        Code:
        {code}

        Provide a concise summary (50-70 words):"""
        
        self.all_summary_prompt = """Based on the following code summaries, provide a comprehensive overview of the project:

        {summaries}

        Structure your response with:
        1. Project Overview (purpose and main goals)
        2. Key Features and Functionality
        3. Technical Stack and Technologies
        4. Architecture and Design Patterns
        5. Notable Components
        
        Keep the total summary under 2000 words."""

    def _preprocess_code(self, code: str) -> str:
        """Preprocess code to make it more suitable for summarization"""
        # Remove excessive whitespace
        code = re.sub(r'\n\s*\n', '\n', code)
        
        # Remove comments
        code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        
        # Remove empty lines
        code = '\n'.join(line for line in code.split('\n') if line.strip())
        
        return code

    def _chunk_text(self, text: str, max_length: int = 1000) -> List[str]:
        """Split text into chunks that fit within model's context window"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(self.tokenizer.encode(word))
            if current_length + word_length > max_length:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks

    def summarize_code(self, code: str) -> str:
        """Generate a summary for a single code file"""
        try:
            if not code.strip():
                return "Empty file"

            # Preprocess the code
            code = self._preprocess_code(code)
            
            # Skip if content is too short
            if len(code.split('\n')) <= 1:
                return "Single line file - skipping summary"

            # Split code into chunks if it's too long
            chunks = self._chunk_text(code)
            summaries = []
            
            for chunk in chunks:
                summary = self.summarizer(
                    chunk,
                    max_length=46,
                    min_length=30,
                    do_sample=False
                )[0]['summary_text']
                summaries.append(summary)
            
            return ' '.join(summaries)
        except Exception as e:
            logger.error(f"Error summarizing code: {e}")
            return "Error generating summary"

    def summarize_repo(self, code_list: List[str]) -> str:
        """
        Generate a comprehensive summary of the entire repository
        
        Args:
            code_list: List of code contents from different files
        
        Returns:
            str: HTML formatted summary of the repository
        """
        try:
            logger.info("Generating individual file summaries...")
            # Generate summaries for each file
            file_summaries = []
            for code in code_list:
                summary = self.summarize_code(code)
                if summary and summary != "Error generating summary":
                    file_summaries.append(summary)
            
            if not file_summaries:
                return "<p>No valid code files found to summarize.</p>"
            
            # Combine all summaries
            combined_summaries = "\n\n".join(file_summaries)
            
            # Generate final repository summary
            logger.info("Generating final repository summary...")
            final_summary = self.summarizer(
                combined_summaries,
                max_length=500,
                min_length=100,
                do_sample=False
            )[0]['summary_text']
            
            # Format as HTML
            html_summary = self._format_as_html(final_summary)
            
            logger.info("Summary generation complete")
            return html_summary
            
        except Exception as e:
            logger.error(f"Error in repository summarization: {e}")
            return f"<p>Error generating repository summary: {str(e)}</p>"

    def _format_as_html(self, text: str) -> str:
        """Format the summary as HTML with proper styling"""
        # Split into paragraphs
        paragraphs = text.split('\n\n')
        
        # Format each paragraph
        formatted_paragraphs = []
        for i, para in enumerate(paragraphs):
            if i == 0:
                # First paragraph as heading
                formatted_paragraphs.append(f"<h1>{para}</h1>")
            else:
                # Highlight key terms
                para = para.replace('Project', '<strong>Project</strong>')
                para = para.replace('Features', '<strong>Features</strong>')
                para = para.replace('Technologies', '<strong>Technologies</strong>')
                para = para.replace('Architecture', '<strong>Architecture</strong>')
                para = para.replace('Components', '<strong>Components</strong>')
                formatted_paragraphs.append(f"<p>{para}</p>")
        
        # Add some basic styling
        html = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px;">
            <style>
                h1 {{ color: #2c3e50; margin-bottom: 20px; }}
                p {{ color: #34495e; margin-bottom: 15px; }}
                strong {{ color: #2980b9; }}
            </style>
            {''.join(formatted_paragraphs)}
        </div>
        """
        
        return html

def main():
    # Example usage
    try:
        # Initialize the summarizer
        summarizer = LLM_Summarize()
        
        # Example code snippets
        code_snippets = [
            """
            def hello_world():
                print("Hello, World!")
            """,
            """
            class Calculator:
                def add(self, x, y):
                    return x + y
                
                def subtract(self, x, y):
                    return x - y
            """
        ]
        
        # Generate summary
        summary = summarizer.summarize_repo(code_snippets)
        print(summary)
        
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    main() 