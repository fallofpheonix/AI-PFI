class AI_PFI_Error(Exception):
    """Base exception for AI-PFI."""
    pass

class ParseError(AI_PFI_Error):
    """Raised when parsing fails."""
    pass
