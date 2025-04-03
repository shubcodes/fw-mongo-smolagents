# earnings_ai_demo/earnings_ai_demo/app.py
import streamlit as st
import asyncio
from pathlib import Path
import yaml
import tempfile
import os
from agent_system import FinancialAnalysisSystem

def load_config():
    with open('config/config.yaml') as f:
        return yaml.safe_load(f)

class EarningsAIApp:
    def __init__(self):
        config = load_config()
        # Initialize the multi-agent system
        self.analysis_system = FinancialAnalysisSystem(
            api_key=config['fireworks']['api_key'],
            mongodb_uri=config['mongodb']['uri']
        )

    async def process_files_and_query(self, files, query, company_ticker=None, date_range=None):
        # Save uploaded files to temporary locations
        temp_file_paths = []
        for file in files:
            file_extension = Path(file.name).suffix
            with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as tmp_file:
                tmp_file.write(file.getvalue())
                tmp_file.flush()
                temp_file_paths.append(tmp_file.name)

        # Process with multi-agent system
        try:
            result = await self.analysis_system.process_financial_data(
                query=query,
                files=temp_file_paths,
                company_ticker=company_ticker,
                date_range=date_range
            )
            return {"status": "success", "result": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            # Clean up temporary files
            for temp_file in temp_file_paths:
                try:
                    os.unlink(temp_file)
                except:
                    pass

def main():
    st.set_page_config(
        page_title="EarningsAI",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    st.markdown("""
        <style>
        /* Global Styles */
        .stApp {
            background-color: #2c2c2e;
            color: #f5f5f7;
        }
        
        /* Typography */
        h1, h2, h3 {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            font-weight: 600;
            color: #ffffff;
        }
        
        /* Input and Text Styles */
        input, textarea {
            background-color: #3a3a3c;
            color: #f5f5f7;
            border: none;
            border-radius: 5px;
        }
        
        /* Buttons */
        .stButton > button {
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 0.25rem;
            padding: 0.5rem 1rem;
            font-size: 1rem;
            cursor: pointer;
        }
        .stButton > button:hover {
            background-color: #0056b3;
        }
        
        /* Chat Messages */
        .chat-message {
            padding: 1rem;
            margin-bottom: 0.5rem;
        }
        
        .user-message {
            background: #1a1a1c;
            margin-left: 20%;
            margin-right: 10px;
            border-radius: 15px 15px 0 15px;
        }
        
        .bot-message {
            background: #2d2d30;
            margin-right: 20%;
            margin-left: 10px;
            border-radius: 15px 15px 15px 0;
        }
        
        /* Remove unwanted spacing and dividers */
        [data-testid="stMarkdownContainer"] {
            margin: 0 !important;
            padding: 0 !important;
            border: none !important;
        }
        
        .st-emotion-cache-1cvow4s {
            margin: 0 !important;
            padding: 0 !important;
            border: none !important;
        }

        /* Error and Success Messages */
        .st-alert-error {
            background-color: #000000;
            color: #ffffff;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 0.5rem;
        }

        .st-alert-success {
            background-color: #000000;
            color: #ffffff;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 0.5rem;
        }

        /* Form styling */
        .stForm {
            background-color: transparent !important;
            border: none !important;
        }
        
        .stForm [data-testid="stForm"] {
            border: none !important;
            padding: 0 !important;
        }

        /* Chat container */
        .chat-container {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        /* Sources expander */
        .streamlit-expanderHeader {
            background-color: #3a3a3c !important;
            border-radius: 5px;
        }

        /* Secondary button style */
        .secondary-button {
            background-color: #6c757d !important;
        }
        .secondary-button:hover {
            background-color: #5a6268 !important;
        }
        
        /* File uploader styling */
        .uploadedFiles {
            margin-top: 1rem;
            background: transparent !important;
        }
        
        /* Processed files section */
        .processed-files {
            margin-top: 1rem;
            padding: 0;
            background: transparent;
        }
        
        /* Remove stMarkdown borders */
        .element-container {
            margin: 0 !important;
            padding: 0 !important;
            border: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

    if 'processed_files' not in st.session_state:
        st.session_state.processed_files = set()

    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    st.title("EarningsAI with Multi-Agent Analysis")
    st.markdown("Transform your financial documents into insights using AI agents")

    app = EarningsAIApp()

    # Create two columns for layout
    col1, col2 = st.columns([2, 1])

    with col2:
        # File Upload Section
        st.subheader("📄 Upload Documents")
        uploaded_files = st.file_uploader(
            "Drop your files here",
            type=['pdf', 'docx', 'txt', 'mp3', 'wav'],
            accept_multiple_files=True,
            key="file_uploader"
        )

        # Company ticker filter
        st.subheader("🔍 Filters")
        company_ticker = st.text_input("Company Ticker", value="MDB")
        
        # Date range filter
        st.subheader("📅 Date Range")
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")
        date_range = [start_date.isoformat(), end_date.isoformat()] if start_date and end_date else None

    with col1:
        # Query Section
        st.subheader("💬 Ask a Question")
        query = st.text_area("Enter your query", "What are the key financial metrics and trends?")
        
        if st.button("Analyze", type="primary"):
            if uploaded_files:
                with st.spinner("Processing files and analyzing data..."):
                    # Process files and query
                    result = asyncio.run(app.process_files_and_query(
                        uploaded_files, 
                        query, 
                        company_ticker,
                        date_range
                    ))
                    
                    if result["status"] == "success":
                        # Add to chat history
                        st.session_state.chat_history.append({"role": "user", "content": query})
                        st.session_state.chat_history.append({"role": "bot", "content": result["result"]})
                        
                        # Add files to processed list
                        for file in uploaded_files:
                            st.session_state.processed_files.add(file.name)
                    else:
                        st.error(f"Error: {result['message']}")
            else:
                st.warning("Please upload at least one file")
        
        # Display chat history
        if st.session_state.chat_history:
            st.subheader("💬 Conversation")
            for message in st.session_state.chat_history:
                if message["role"] == "user":
                    st.markdown(f"<div class='chat-message user-message'><strong>You:</strong> {message['content']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='chat-message bot-message'><strong>AI:</strong> {message['content']}</div>", unsafe_allow_html=True)

    # Display processed files
    if st.session_state.processed_files:
        st.sidebar.subheader("Processed Files")
        for file in st.session_state.processed_files:
            st.sidebar.text(f"✅ {file}")


if __name__ == "__main__":
    main()