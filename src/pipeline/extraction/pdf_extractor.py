import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Legacy PDF extraction utility
def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    from pdfminer.high_level import extract_text
    import io
    return extract_text(io.BytesIO(pdf_bytes))

class MarkerExtractor:
    """
    Asynchronous adapter for Marker PDF-to-Markdown extraction.
    """
    
    async def extract_pdf(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Routes PDF bytes through an isolated Marker process.
        """
        with tempfile.TemporaryDirectory() as tmpdirname:
            tmp_path = Path(tmpdirname)
            pdf_file = tmp_path / "input.pdf"
            pdf_file.write_bytes(pdf_bytes)
            
            # Marker command: isolated process ensures we don't block the loop
            # Note: Expects 'marker_single' to be in the PATH
            cmd = ["marker_single", str(pdf_file), str(tmp_path), "--workers", "1"]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                logger.error(f"Marker processing failed: {stderr.decode()}")
                raise RuntimeError("Failed to parse PDF via Marker.")
                
            # Read output markdown
            markdown_file = tmp_path / "input.md"
            if not markdown_file.exists():
                raise RuntimeError("Marker did not produce output markdown.")
                
            return {
                "markdown_content": markdown_file.read_text(encoding="utf-8"),
                "is_raw_text": False
            }
