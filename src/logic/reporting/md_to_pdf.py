import markdown_it
from weasyprint import HTML
import os

md_path = "/Users/aierarohit/Desktop/Political Data/Thiruvottiyur_Survey_Report.md"
pdf_path = "/Users/aierarohit/Desktop/Political Data/Thiruvottiyur_Survey_Report.pdf"
base_url = "/Users/aierarohit/Desktop/Political Data/"

print("Reading Markdown...")
with open(md_path, "r", encoding="utf-8") as f:
    text = f.read()

print("Converting to HTML...")
md = markdown_it.MarkdownIt()
html = md.render(text)

# Add some basic styling and font-support for Tamil (if present)
styled_html = f"""
<html>
<head>
    <style>
        body {{ font-family: sans-serif; padding: 20px; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        img {{ max-width: 100%; height: auto; }}
        h1, h2, h3 {{ color: #333; }}
    </style>
</head>
<body>
{html}
</body>
</html>
"""

print("Generating PDF via WeasyPrint...")
HTML(string=styled_html, base_url=base_url).write_pdf(pdf_path)

print(f"✅ Success! PDF saved to {pdf_path}")
