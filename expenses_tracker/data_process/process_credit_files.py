from pathlib import Path
from markitdown import MarkItDown


def to_markdown(filepath: str):
    md = MarkItDown()
    result = md.convert(filepath)

    output_file = Path(filepath).with_suffix(".md")
    output_file.write_text(result.text_content)
    # print(f"Markdown file saved: {output_file}")


if __name__ == '__main__':
    filepath = r"./data/transactions.xlsx"
    to_markdown(filepath)
