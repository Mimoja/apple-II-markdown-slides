#!/usr/bin/env python3

import marko
from marko.ast_renderer import ASTRenderer

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import textwrap
import os

content = ""
with open("slides.md", "r") as f:
    content = f.read()


markdown = marko.Markdown(renderer=ASTRenderer)
res = markdown(content)

if len(res.get("children", [])) == 0:
    print("No children found in the markdown content.")


slides = []
currentSlide = None


def closeSlide():
    global currentSlide
    if currentSlide is not None:
        if (
            len(currentSlide.get("heading", [])) == 0
            and len(currentSlide.get("content", [])) == 0
        ):
            # Skip empty slides
            return
        slides.append(currentSlide)
        # print(
        #     f"\n\n====================\nContent: {currentSlide}\n====================\n\n"
        # )
    currentSlide = {
        "heading": [],
        "content": [],
    }


def parseNode(parent, depth=0):
    global currentSlide
    content = []
    for node in parent.get("children", []):
        type_ = node.get("element", "unknown")
        # print(f"{"  "*depth}Node: {type_}: {node}")
        match type_:
            case "setext_heading":
                continue
            case "blank_line":
                continue

            case "thematic_break":
                closeSlide()
            case "code_span":
                code = node.get("children", "")
                content.append(f"'{code}'")

            case "raw_text":
                content.append(node.get("children", ""))

            case "heading":
                currentSlide["heading"] += parseNode(node, depth + 1)

            case "line_break":
                content.append("\n")
            case type_ if type_ in ["inline_html", "html_block"]:
                html = node.get("children", "").strip()
                if html.startswith("<!--") and html.endswith("-->"):
                    # This is a comment, ignore it
                    continue
                if (html.startswith("<") or html.startswith("</")) and html.endswith(
                    ">"
                ):
                    # This is a HTML tag, skip
                    continue
                content.append(html)

            case "auto_link":
                title = node.get("title", "")
                if title is not None and title != "":
                    content.append(title)
                content += parseNode(node, depth + 1)

            case "link":
                title = node.get("title", "")
                if title is not None and title != "":
                    content.append(title)
                content += parseNode(node, depth + 1)

            case "list":
                bullet = node.get("bullet", "")
                list_items = parseNode(node, depth + 1)
                list_test = []
                for index, item in enumerate(list_items):
                    if item.strip(" ") != "\n":
                        if bullet in ["*", "-", "+"]:
                            list_test.append(bullet)
                        else:
                            list_test.append(f"{(index//2) + 1}.")
                    list_test.append(item.strip(" "))

                if depth == 0:
                    currentSlide["content"] += [
                        t for t in list_test if t.strip(" ") != ""
                    ]
                else:
                    content += list_test

            case type_ if type_ in [
                "paragraph",
                "emphasis",
                "strong_emphasis",
                "fenced_code",
                "list_item",
                "quote",
            ]:
                text = parseNode(node, depth + 1)
                if type_ == "paragraph" and len(text) > 0:
                    text += "\n"

                if depth == 0:
                    currentSlide["content"] += [t for t in text if t.strip(" ") != ""]
                else:
                    content += text

            case _:
                print(f"Unhandled node type: {type_}")
                print(node)
                continue
    return content


parseNode(res)
if currentSlide is not None:
    slides.append(currentSlide)

for slide in slides:
    print("\n".join(slide["heading"]))
    content_string = " ".join(
        [c.strip(" ") for c in slide["content"] if c.strip(" ") != ""]
    )
    slide_content = content_string.split("\n")
    for line in slide_content:
        print("  " + line.strip(" "))
    print("-" * 40)

os.makedirs("slides", exist_ok=True)

imageSize = (280, 192)
appleSoftBasic = []


for index, slide in enumerate(slides):
    appleSoftBasic.append("HOME")
    appleSoftBasic.append("COLOR = 6")
    img = Image.new(mode="RGB", size=imageSize)

    appleFont = ImageFont.truetype("PrintChar21.ttf", 8)
    draw = ImageDraw.Draw(img)
    # Render the Heading
    header_height = 0
    for i, heading in enumerate(
        [h.strip(" ") for h in slide["heading"] if h.strip(" ") != ""]
    ):
        heading = heading.strip(" ")
        h_len = len(heading)
        padding = (40 - h_len) / 2
        header_height = i * 8 + 7
        draw.text(
            (padding * 7, header_height),
            heading,
            font=appleFont,
            fill=(255, 0, 0),
        )
        printPadding = " " * int(padding)
        appleSoftBasic.append(f'PRINT "{printPadding}{heading}"')

    # Render the content
    content_string = " ".join(
        [c.strip(" ") for c in slide["content"] if c.strip(" ") != ""]
    )
    slide_content = content_string.split("\n")
    appleSoftBasic.append("COLOR = 1")
    text_img = Image.new("RGB", (280, 192), (0, 0, 0))
    text_draw = ImageDraw.Draw(text_img)
    y_pos = 0
    basicText = []
    for content in slide_content:
        if content.strip(" ") == "":
            continue
        text_lines = textwrap.wrap(content, width=38)
        for i, line in enumerate(text_lines):
            y_pos += 8
            position = (7, y_pos)
            text_draw.text(
                position,
                line.strip(" "),
                font=appleFont,
                fill=(255, 255, 255),
            )
            basicText.append(f'PRINT " {line.strip(" ")}"')
        if len(text_lines) > 1:
            y_pos += 8
            basicText.append('PRINT ""')
    space_avail = imageSize[1] - (header_height + 7) - y_pos
    horiz_padding_lines = (space_avail // 2) // 7
    if y_pos > 0:
        appleSoftBasic += ["PRINT"] * horiz_padding_lines
        appleSoftBasic += basicText
    appleSoftBasic.append("GET A$")
    img.paste(text_img, (0, horiz_padding_lines * 7))

    img.save(f"slides/slide_{index}.png")


def clearAppleSoft():
    for i, line in enumerate(appleSoftBasic):
        if line.startswith("PRINT"):
            line = line.replace("#", '"; CHR$(35); "')
            if line.count('"') > 2:
                parts = line.split('"')
                line = '"; CHR$(34); "'.join(parts[1:-1])
                line = f'PRINT "{line}"'
            appleSoftBasic[i] = line


clearAppleSoft()

with open("applesoft_basic.txt", "w") as f:
    for index, cmd in enumerate(appleSoftBasic):
        line = f"{(index + 1)*10:02d}: {cmd}\n"
        f.write(line)
