"""
This module provides the QdrantLoader class, which orchestrates the loading,
chunking, and embedding of documents before storing them in QdrantDB.
It integrates with an embedding manager and a text chunker to process
various document types and prepare them for vector search.
"""

import argparse
import sys
import uuid
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from qdrant_client.http import models

from src.ingestion.embedding_manager import EmbeddingManager
from src.ingestion.text_chunker import TextChunker
from src.ingestion.reader import DocumentReader
from src.utils import logger
from src.utils.config_loader import get_config
from src.vector.qdrant_db_client import QdrantDBClient

# Load environment variables
load_dotenv()


class QdrantLoader:
    """Orchestrates document loading, chunking, and storage in QdrantDB"""

    def __init__(self, collection_name: str = None):

        self.collection_name = collection_name or get_config("vector.collection_name")
        self.embedding_model = get_config("vector.embedding_model_name")

        # Initialize components
        self.chunker = TextChunker()
        self.embedding_manager = EmbeddingManager()
        self.document_reader = DocumentReader()

        # Initialize Qdrant
        self.qdrant_db_client = QdrantDBClient()
        self._initialize_qdrant()

    def _initialize_qdrant(self):
        """Initialize Qdrant collection"""
        try:

            self.qdrant_db_client.ensure_collection(self.collection_name)
            logger.info("Qdrant collection '%s' ready", self.collection_name)

        except Exception as e:
            logger.error("Error initializing Qdrant: %s", e)
            raise

    def _read_from_bytes(self, file_bytes: bytes, filename: str) -> str:
        """
        Load document content from bytes using DocumentReader factory.
    
        Supports all formats: DOCX, PDF, XLSX, PPTX, TXT, MD, EPUB, CSV, images, etc.

        Args:
            file_bytes: Bytes of the document file
            filename: Name of the file (used to determine format)

        Returns:
            Extracted text content
        """
        try:
            content = self.document_reader.extract(file_bytes, filename)
            logger.info(f"Extracted {len(content)} characters from document: {filename}")
            return content
        except Exception as e:
            raise RuntimeError(f"Failed to read document: {e}") from e

    def process_document(self, file_bytes: bytes, filename: str) -> dict:
        """
        Process a document from bytes

        Args:
            file_bytes: Bytes of the uploaded file
            filename: Name of the file (e.g., "Schengen Visa FAQs.docx")

        Returns:
            Dictionary with processing statistics
        """
        logger.info("\n%s", "=" * 60)
        logger.info("Processing file: %s", filename)
        logger.info("%s\n", "=" * 60)

        try:
            # 0. Delete existing chunks for this document (enables overwrite)
            old_chunk_count = self.get_document_chunk_count(filename)
            was_replaced = old_chunk_count > 0

            if was_replaced:
                self.delete_document_chunks(filename)
                logger.info("Removed %d existing chunks for overwrite", old_chunk_count)

            # 1. Load document from bytes
            content = self._read_from_bytes(file_bytes, filename)
            logger.info("Loaded %d characters", len(content))

            # 2. Chunk document
            chunks = self.chunker.chunk(content)
            logger.info("Created %d chunks", len(chunks))

            # Free document content from memory immediately
            del content

            # 3. Embed chunks (chunks are dicts with 'text' key)
            chunk_texts = [chunk["text"] for chunk in chunks]
            embeddings = self.embedding_manager.embed_texts(chunk_texts)

            # Free chunk texts after embedding
            del chunk_texts

            # 4. Add to Qdrant
            points = []

            # Extract stem from filename (remove extension)
            file_stem = Path(filename).stem

            for i, chunk in enumerate(chunks):
                doc_id_str = f"{file_stem}_{chunk['chunk_id']}"
                # Qdrant requires UUID or integer IDs
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, doc_id_str))

                # Prepare metadata
                chunk_metadata = {
                    **chunk.get("metadata", {}),
                    "document_name": filename,
                    "document_stem": file_stem,
                    "embedding_model": self.embedding_model,
                    "chunk_id": chunk["chunk_id"],
                    "content": chunk["text"],  # Store text in payload
                    "orig_id": doc_id_str,
                }

                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector=(
                            embeddings[i].tolist()
                            if hasattr(embeddings[i], "tolist")
                            else embeddings[i]
                        ),
                        payload=chunk_metadata,
                    )
                )

            # Add to collection
            self.qdrant_db_client.upsert(self.collection_name, points)

            logger.info("Added %d chunks to QdrantDB", len(points))

            return {
                "file": filename,
                "status": "success",
                "was_replaced": was_replaced,
                "old_chunk_count": old_chunk_count,
                "chunks_created": len(chunks),
                "chunks_stored": len(points),
                "content_size": sum(len(chunk["text"]) for chunk in chunks),
            }

        except Exception as e:
            logger.exception("Error processing file %s: %s", filename, e)
            return {"file": filename, "status": "error", "error": str(e)}

    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.3,
        include_metadata: bool = True,
    ) -> List[dict]:
        """
        Search for relevant documents

        Args:
            query: Search query
            top_k: Number of results to return
            include_metadata: Whether to include metadata in results

        Returns:
            List of search results
        """
        try:
            # 1. Embed query
            query_embedding = self.embedding_manager.embed_single_text(query)

            # 2. Query Qdrant
            results = self.qdrant_db_client.query_collection(
                self.collection_name, query_embedding, top_k
            )

            formatted_results = []
            for i, result in enumerate(results):
                formatted_results.append(
                    {
                        "rank": i + 1,
                        "content": result.content,
                        "relevance_score": result.relevance_score,
                        "metadata": result.metadata if include_metadata else None,
                    }
                )

            return formatted_results

        except Exception as e:
            logger.error("Error searching: %s", e)
            raise

    def get_collection_stats(self) -> dict:
        """Get statistics about the collection"""
        try:
            count = self.qdrant_db_client.count(self.collection_name)
            return {
                "collection_name": self.collection_name,
                "total_documents": count,
                "embedding_model": self.embedding_model,
                "provider": "Qdrant Cloud",
            }
        except Exception as e:
            logger.error("Error getting collection stats: %s", e)
            raise

    def delete_document_chunks(self, document_name: str) -> int:
        """
        Delete all chunks belonging to a specific document.

        Args:
            document_name: Name of the document (e.g., "Schengen Visa FAQs.docx")

        Returns:
            Number of chunks deleted (approximate/0 if unsupported)
        """
        try:
            # Delete by filter
            self.qdrant_db_client.delete_by_filter(
                self.collection_name, "document_name", document_name
            )
            logger.info("Deleted chunks for document: %s", document_name)
            return 0  # Qdrant delete by filter doesn't return count easily

        except Exception as e:
            logger.error("Error deleting document chunks: %s", e)
            raise

    def _scroll_all_points(self):
        """
        Generator that yields all points in the collection using pagination.

        Args:
            limit: Number of points per scroll batch

        Yields:
            Qdrant PointStruct objects
        """
        limit = get_config("ingestion.scroll_batch_size")

        next_offset = None

        while True:
            points, next_offset = self.qdrant_db_client.client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                with_payload=True,
                with_vectors=False,
                offset=next_offset,
            )

            for point in points:
                yield point

            if next_offset is None:
                break

    def get_unique_document_count(self) -> int:
        """
        Count unique documents in the collection using paginated scroll.

        Returns:
            Number of unique documents
        """
        unique_docs = set()

        for point in self._scroll_all_points():
            # payload can be None depending on scroll response; guard against it
            payload = point.payload or {}
            doc_name = payload.get("document_name")
            if doc_name:
                unique_docs.add(doc_name)

        return len(unique_docs)

    def list_documents(self) -> List[dict]:
        """
        List all unique documents in the collection.
        """
        documents = {}

        for point in self._scroll_all_points():
            # payload may be None - use empty dict as fallback
            payload = point.payload or {}
            doc_name = payload.get("document_name")

            if not doc_name:
                continue

            if doc_name not in documents:
                documents[doc_name] = {
                    "document_name": doc_name,
                    "document_stem": payload.get("document_stem"),
                    "chunk_count": 1,
                }
            else:
                documents[doc_name]["chunk_count"] += 1

        return list(documents.values())

    def get_document_chunk_count(self, document_name: str) -> int:
        """
        Get the number of chunks for a specific document.
        """
        # Could satisfy this with count(filter=...)
        try:
            return self.qdrant_db_client.client.count(
                self.collection_name,
                models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_name",
                            match=models.MatchValue(value=document_name),
                        )
                    ]
                ),
            ).count
        except Exception:
            return 0


def display_search_results(results: List[dict], query: str):
    """Display search results in a clean, readable format"""

    print("\n" + "=" * 80)
    print("🔍 SEARCH RESULTS")
    print("=" * 80)
    print(f"\nQuery: '{query}'")
    print(f"Found: {len(results)} results\n")

    if not results:
        print("No results found. Try:")
        print("   - Lowering the score threshold")
        print("   - Using different search terms")
        print("   - Checking if documents are uploaded")
        return

    # Display each result
    for i, result in enumerate(results, 1):
        print("=" * 80)
        print(f"Result #{i}")
        print("=" * 80)
        print(f"\n📊 Score: {result['relevance_score']:.4f} (0=worst, 1=best)")

        # Metadata
        metadata = result.get("metadata", {})
        print(f"\n📁 Source: {metadata.get('document_name', 'Unknown')}")
        print(
            f"📄 Chunk: {metadata.get('chunk_index', '?')} of {metadata.get('total_chunks', '?')}"
        )

        # Content with proper wrapping
        print("\n📝 Content:")
        print(f"   {'-' * 76}")

        # Wrap text to 76 characters with indentation
        text = result["content"]
        words = text.split()
        lines = []
        current_line = "   "

        for word in words:
            if len(current_line) + len(word) + 1 <= 80:
                current_line += word + " "
            else:
                lines.append(current_line.rstrip())
                current_line = "   " + word + " "

        if current_line.strip():
            lines.append(current_line.rstrip())

        print("\n".join(lines))
        print(f"   {'-' * 76}\n")

        # Summary statistics
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    avg_score = sum(r["relevance_score"] for r in results) / len(results)
    print(f"\nTotal results: {len(results)}")
    print(f"Average score: {avg_score:.4f}")
    print(f"Best score: {results[0]['relevance_score']:.4f}")
    print(f"Worst score: {results[-1]['relevance_score']:.4f}")
    print()


def main():
    """
    Main function to handle command-line arguments for loading, searching,
    and managing documents in QdrantDB.
    """
    parser = argparse.ArgumentParser(description="Load documents into QdrantDB")

    parser.add_argument("--file", type=str, help="Path to single docx file")

    parser.add_argument(
        "--search", type=str, help="Search query after loading (optional)"
    )

    parser.add_argument(
        "--search-top-k",
        type=int,
        default=5,
        help="Number of results for search (default: 5)",
    )

    parser.add_argument(
        "--stats", action="store_true", help="Show collection statistics"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Batch size for embedding (default: 1 = safest). Use 2-4 only with 8GB+ RAM.",
    )

    parser.add_argument(
        "--list-docs", action="store_true", help="List all documents in the collection"
    )

    parser.add_argument(
        "--delete-doc", type=str, help="Delete all chunks for a specific document"
    )

    parser.add_argument(
        "--search-threshold",
        type=float,
        default=0.3,
        help="Minimum similarity score (0-1, default: 0.3)",
    )

    args = parser.parse_args()

    # Validate arguments
    if (
        not args.file
        and not args.search
        and not args.stats
        and not args.list_docs
        and not args.delete_doc
    ):
        parser.print_help()
        sys.exit(1)

    try:
        # processor = QdrantLoader(batch_size=args.batch_size)
        processor = QdrantLoader()

        # List documents
        if args.list_docs:
            docs = processor.list_documents()
            print("\n📚 Documents in collection:")
            if docs:
                for doc in docs:
                    print(f"   • {doc['document_name']} ({doc['chunk_count']} chunks)")
            else:
                print("   No documents found")

        # Delete document
        if args.delete_doc:
            deleted = processor.delete_document_chunks(args.delete_doc)
            logger.info("\nDeleted all chunks for: %s", args.delete_doc)

        # Process files
        if args.file:
            file_path = Path(args.file)

            if not file_path.exists():
                logger.error("File not found: %s", file_path)
                sys.exit(1)

            logger.info("Loading single file: %s", file_path)

            try:
                # Read file bytes
                file_bytes = file_path.read_bytes()

                # Process the document
                result = processor.process_document(file_bytes, file_path.name)

                # Check result status
                if result["status"] == "success":
                    logger.info("\n✅ File processed successfully:")
                    logger.info("   File: %s", result["file"])
                    logger.info("   Chunks created: %d", result["chunks_created"])
                    logger.info("   Chunks stored: %d", result["chunks_stored"])

                    if result["was_replaced"]:
                        logger.info("   ⚠️  Replaced existing document")
                        logger.info(
                            "   Old chunks: %d → New chunks: %d",
                            result["old_chunk_count"],
                            result["chunks_created"],
                        )
                else:
                    logger.error("\n❌ File processing failed:")
                    logger.error("   File: %s", result["file"])
                    logger.error("   Error: %s", result.get("error", "Unknown error"))
                    sys.exit(1)

            except PermissionError:
                logger.error("Permission denied: %s", file_path)
                sys.exit(1)
            except Exception as e:
                logger.error("Error reading file %s: %s", file_path, e)
                sys.exit(1)

        # Show statistics
        if args.stats:
            stats = processor.get_collection_stats()
            logger.info("\n📊 Collection Statistics:")
            stats_output = (
                f"   Collection: {stats['collection_name']}\n"
                f"   Total documents: {stats['total_documents']}\n"
                f"   Embedding model: {stats['embedding_model']}\n"
                f"   Provider: {stats['provider']}"
            )
            logger.info(stats_output)

        # Perform search
        # if args.search:
        #     results = processor.search(
        #         args.search,
        #         top_k=args.search_top_k,
        #         score_threshold=args.search_threshold
        #     )
        #     display_search_results(results, args.search)

    except Exception as e:
        logger.error("Error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()

### Load Single DOCX File
# bash
# python qdrant_loader.py --file Schengen-Visa-FAQs.docx

### Load Directory
# bash
# python qdrant_loader.py --file documents/MyDoc.docx --batch-size 4

### Search Documents
# bash
# python qdrant_loader.py --search "What documents do I need for Schengen visa?" --search-top-k 5

### Show Statistics
# bash
# python qdrant_loader.py --stats
