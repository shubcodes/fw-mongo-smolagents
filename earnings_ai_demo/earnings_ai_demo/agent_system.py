from typing import Dict, List, Optional
from datetime import datetime
import asyncio
import logging

from smolagents import CodeAgent, LiteLLMModel, ManagedAgent, tool
from smolagents.agents import ToolCallingAgent

from earnings_ai_demo.database import DatabaseOperations
from earnings_ai_demo.embedding import EmbeddingGenerator
from earnings_ai_demo.extraction import DocumentExtractor
from earnings_ai_demo.transcription import AudioTranscriber


class FinancialAnalysisSystem:
    """Multi-agent system for financial document analysis"""

    def __init__(self, api_key: str, mongodb_uri: str, model_id: str = "deepseek/deepseek-chat"):
        # Initialize model
        self.model = LiteLLMModel(model_id=model_id, api_key=api_key)
        
        # Initialize core components
        self.db = DatabaseOperations(mongodb_uri)
        self.embedding_gen = EmbeddingGenerator(api_key)
        self.doc_extractor = DocumentExtractor()
        self.transcriber = AudioTranscriber(api_key)
        
        # Create specialized agents
        self.document_agent = self._create_document_agent()
        self.transcription_agent = self._create_transcription_agent()
        self.query_agent = self._create_query_agent()
        self.analysis_agent = self._create_analysis_agent()
        
        # Create managed agents
        self.managed_agents = [
            ManagedAgent(
                self.document_agent, "document_processor", 
                "Processes document files and extracts text"
            ),
            ManagedAgent(
                self.transcription_agent, "transcription", 
                "Transcribes audio files from earnings calls"
            ),
            ManagedAgent(
                self.query_agent, "query", 
                "Queries the document database to retrieve relevant information"
            ),
            ManagedAgent(
                self.analysis_agent, "analysis", 
                "Performs financial analysis on retrieved information"
            ),
        ]
        
        # Create manager agent
        self.manager = CodeAgent(
            tools=[],
            system_prompt="""You are coordinating the analysis of financial documents and earnings calls.
            For each request:
            1. Process documents and audio files if provided
            2. Generate embeddings and store them in the database
            3. Query the database to retrieve relevant information
            4. Analyze the information to extract key insights
            
            Use relevant agents: {{managed_agents_descriptions}} and you can use {{authorized_imports}}
            """,
            model=self.model,
            managed_agents=self.managed_agents,
            additional_authorized_imports=["json", "asyncio", "datetime"],
        )
    
    def _create_document_agent(self):
        """Create document processing agent with tools"""
        
        @tool
        def extract_text(file_path: str) -> Dict:
            """Extract text from a document file.
            
            Args:
                file_path: Path to document file
                
            Returns:
                Dict with extracted text and metadata
            """
            return self.doc_extractor.extract_text(file_path)
        
        @tool
        def process_directory(directory_path: str) -> List[Dict]:
            """Process all documents in a directory.
            
            Args:
                directory_path: Path to directory containing documents
                
            Returns:
                List of documents with extracted text and metadata
            """
            return self.doc_extractor.process_directory(directory_path)
        
        @tool
        def store_document(text: str, metadata: Dict) -> str:
            """Store document in database with embeddings.
            
            Args:
                text: Document text
                metadata: Document metadata
                
            Returns:
                Document ID
            """
            embeddings = self.embedding_gen.generate_document_embedding(text)
            return self.db.store_document(text, embeddings, metadata)
        
        return ToolCallingAgent(
            tools=[extract_text, process_directory, store_document],
            model=self.model,
            max_iterations=10
        )
    
    def _create_transcription_agent(self):
        """Create transcription agent with tools"""
        
        @tool
        async def transcribe_file(file_path: str, metadata: Optional[Dict] = None) -> Dict:
            """Transcribe an audio file.
            
            Args:
                file_path: Path to audio file
                metadata: Optional metadata
                
            Returns:
                Dict with transcription and metadata
            """
            result = await self.transcriber.transcribe_file(file_path, metadata)
            
            # Store transcription in database
            if result and 'transcription' in result:
                embeddings = self.embedding_gen.generate_document_embedding(result['transcription'])
                doc_metadata = result.get('metadata', {})
                doc_metadata['document_type'] = 'transcript'
                self.db.store_document(result['transcription'], embeddings, doc_metadata)
                
            return result
        
        @tool
        async def transcribe_directory(directory_path: str, metadata: Optional[Dict] = None) -> List[Dict]:
            """Transcribe all audio files in a directory.
            
            Args:
                directory_path: Path to directory containing audio files
                metadata: Optional metadata to apply to all files
                
            Returns:
                List of transcription results
            """
            return await self.transcriber.transcribe_directory(directory_path, metadata)
        
        return ToolCallingAgent(
            tools=[transcribe_file, transcribe_directory],
            model=self.model,
            max_iterations=10
        )
    
    def _create_query_agent(self):
        """Create query agent with tools"""
        
        @tool
        def query_similar(query_text: str, limit: int = 5, filters: Optional[Dict] = None) -> List[Dict]:
            """Find documents similar to the query text.
            
            Args:
                query_text: Query text
                limit: Maximum number of results
                filters: Optional filters
                
            Returns:
                List of similar documents
            """
            query_embedding = self.embedding_gen.generate_embedding(query_text)
            return self.db.query_similar(query_embedding, limit, filters)
        
        @tool
        def filter_by_company(documents: List[Dict], company_ticker: str) -> List[Dict]:
            """Filter documents by company ticker.
            
            Args:
                documents: List of documents
                company_ticker: Company ticker symbol
                
            Returns:
                Filtered list of documents
            """
            return [doc for doc in documents if doc.get('metadata', {}).get('company_ticker') == company_ticker]
        
        @tool
        def filter_by_date_range(documents: List[Dict], start_date: str, end_date: str) -> List[Dict]:
            """Filter documents by date range.
            
            Args:
                documents: List of documents
                start_date: Start date (YYYY-MM-DD)
                end_date: End date (YYYY-MM-DD)
                
            Returns:
                Filtered list of documents
            """
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            
            return [
                doc for doc in documents 
                if start <= datetime.fromisoformat(doc.get('metadata', {}).get('date', '1970-01-01')) <= end
            ]
        
        return ToolCallingAgent(
            tools=[query_similar, filter_by_company, filter_by_date_range],
            model=self.model,
            max_iterations=10
        )
    
    def _create_analysis_agent(self):
        """Create analysis agent with tools"""
        
        @tool
        def extract_financial_metrics(documents: List[Dict]) -> Dict:
            """Extract financial metrics from documents.
            
            Args:
                documents: List of documents
                
            Returns:
                Dict with extracted financial metrics
            """
            # Build context from documents
            context = "\n\n".join([doc.get('text', '') for doc in documents])
            
            # Prompt for financial metrics extraction
            prompt = """Given the following financial document(s), extract the key financial metrics including:
            - Revenue
            - Earnings per share (EPS)
            - Gross margin
            - Operating margin
            - Net income
            - Year-over-year growth
            - Any forward guidance
            
            If a metric is not present, leave it out of your response.
            
            Documents:
            {context}
            """.format(context=context)
            
            # Get response
            response = self.model.complete(prompt=prompt)
            
            # Convert to structured format
            return {"analysis": response}
        
        @tool
        def identify_key_trends(documents: List[Dict]) -> Dict:
            """Identify key trends in documents.
            
            Args:
                documents: List of documents
                
            Returns:
                Dict with identified trends
            """
            context = "\n\n".join([doc.get('text', '') for doc in documents])
            
            prompt = """Based on the following financial documents, identify key business trends, including:
            - Growth areas
            - Challenges or risks
            - Strategic investments
            - Market conditions
            - Competitive landscape
            
            Documents:
            {context}
            """.format(context=context)
            
            response = self.model.complete(prompt=prompt)
            return {"trends": response}
        
        @tool
        def summarize_earnings_call(documents: List[Dict]) -> Dict:
            """Summarize an earnings call.
            
            Args:
                documents: List of documents
                
            Returns:
                Dict with summary
            """
            context = "\n\n".join([doc.get('text', '') for doc in documents])
            
            prompt = """Summarize the following earnings call transcript in 3-5 concise bullet points:
            
            {context}
            """.format(context=context)
            
            response = self.model.complete(prompt=prompt)
            return {"summary": response}
        
        return ToolCallingAgent(
            tools=[extract_financial_metrics, identify_key_trends, summarize_earnings_call],
            model=self.model,
            max_iterations=10
        )
    
    async def process_financial_data(self, query: str, files: List[str] = None, 
                                    company_ticker: str = None, date_range: List[str] = None) -> Dict:
        """Process financial data and answer a query.
        
        Args:
            query: Question or analysis request
            files: Optional list of files to process
            company_ticker: Optional company ticker symbol
            date_range: Optional date range [start_date, end_date]
            
        Returns:
            Dict with analysis results
        """
        request = {
            "query": query,
            "files": files or [],
            "company_ticker": company_ticker,
            "date_range": date_range
        }
        
        return await self.manager.arun(
            f"Process financial data with the following parameters: {request}"
        ) 