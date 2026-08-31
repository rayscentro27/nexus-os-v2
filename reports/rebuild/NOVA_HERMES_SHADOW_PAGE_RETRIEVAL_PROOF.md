# Hermes Shadow Page Retrieval Proof

**Tool:** `public_web_retrieval_shadow`  
**Test URL:** `https://www.ftc.gov/about-ftc/mission`  
**Provider:** bounded Python HTTP retrieval  
**Result:** REAL success

The tool fetched the public page, followed the final URL, removed HTML
presentation/script noise, returned readable text, preserved the requested and
final URLs, content type, content length, source type, and retrieval timestamp.
The model summarized the FTC mission from returned page content.

This is separate from search: a search result/snippet is not treated as page
verification.

