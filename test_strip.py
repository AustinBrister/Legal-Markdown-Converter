from markdown_it import MarkdownIt
from markdown_it.token import Token

def strip_westlaw_links(markdown_text):
    md = MarkdownIt()
    tokens = md.parseInline(markdown_text)[0].children
    output = []
    skip = False

    for token in tokens:
        if token.type == 'link_open':
            href = dict(token.attrs or {}).get('href', '')
            if 'westlaw.com' in href:
                skip = True
                continue
        elif token.type == 'link_close' and skip:
            skip = False
            continue

        if skip:
            if token.type == 'text':
                output.append(token.content)
        else:
            if token.type == 'text':
                output.append(token.content)
            elif token.type in ('softbreak', 'hardbreak'):
                output.append('\n')

    return ''.join(output)

# ✅ Try a realistic test string
sample = "[John Doe](https://www.westlaw.com/Link/Stuff) wrote this. [Link2](https://example.com)"
print("Result:\n")
print(strip_westlaw_links(sample))