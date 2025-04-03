import asyncio
import yaml
from pathlib import Path
import logging
from earnings_ai_demo.agent_system import FinancialAnalysisSystem


async def main():
    # Load config
    with open('config/config.yaml') as f:
        config = yaml.safe_load(f)

    # Initialize the multi-agent system
    analysis_system = FinancialAnalysisSystem(
        api_key=config['fireworks']['api_key'],
        mongodb_uri=config['mongodb']['uri']
    )
    
    # Process sample data
    sample_dir = Path('data')
    audio_dir = sample_dir / 'audio'
    documents_dir = sample_dir / 'documents'
    
    # Prepare files list
    files = []
    for audio_file in audio_dir.glob('*.mp3'):
        files.append(str(audio_file))
    for doc_file in documents_dir.glob('*'):
        if doc_file.suffix.lower() in ['.pdf', '.docx', '.txt']:
            files.append(str(doc_file))
    
    # Sample queries
    queries = [
        "What is the total q3 earnings for fiscal 2025?",
        "what is the future of AI at Mongo? Is it going to be big?"
    ]

    for query in queries:
        logging.info(f"Processing query: {query}")
        # Process with multi-agent system
        result = await analysis_system.process_financial_data(
            query=query,
            files=files,
            company_ticker='MDB'
        )
        
        print(f"\nQuery: {query}")
        print(f"Multi-Agent Response:")
        print(result)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
