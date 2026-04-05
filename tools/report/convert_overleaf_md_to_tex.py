from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
OVERLEAF_DIR = ROOT / "report" / "overleaf"
CHAPTERS_DIR = OVERLEAF_DIR / "chapters"


MD_TO_TEX = {
    "01_introduction.md": "01_introduction.tex",
    "02_literature_review.md": "02_literature_review.tex",
    "03_proposed_system.md": "03_proposed_system.tex",
    "04_results_and_discussion.md": "04_results_and_discussion.tex",
    "05_conclusion_and_future_scope.md": "05_conclusion_and_future_scope.tex",
    "06_references_body.md": "06_references_body.tex",
}


SPECIALS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def escape_tex(text: str) -> str:
    out = text
    for old, new in SPECIALS.items():
        out = out.replace(old, new)
    return out


def convert_inline(text: str) -> str:
    code_tokens = {}
    bold_tokens = {}
    italic_tokens = {}
    url_tokens = {}

    def path_macro(value: str) -> str:
        for delimiter in ["|", "!", "+", ";", "~", "^", "@"]:
            if delimiter not in value:
                return rf"\path{delimiter}{value}{delimiter}"
        escaped = value.replace("\\", r"\textbackslash{}").replace("{", r"\{").replace("}", r"\}")
        return r"\texttt{" + escaped + "}"

    def url_repl(match: re.Match[str]) -> str:
        key = f"@@URL{len(url_tokens)}@@"
        url_tokens[key] = r"\url{" + match.group(0) + "}"
        return key

    def code_repl(match: re.Match[str]) -> str:
        key = f"@@CODE{len(code_tokens)}@@"
        raw = match.group(1)
        code_tokens[key] = path_macro(raw)
        return key

    def bold_repl(match: re.Match[str]) -> str:
        key = f"@@BOLD{len(bold_tokens)}@@"
        bold_tokens[key] = r"\textbf{" + escape_tex(match.group(1)) + "}"
        return key

    def italic_repl(match: re.Match[str]) -> str:
        key = f"@@ITALIC{len(italic_tokens)}@@"
        italic_tokens[key] = r"\emph{" + escape_tex(match.group(1)) + "}"
        return key

    working = re.sub(r"https?://[^\s]+", url_repl, text)
    working = re.sub(r"`([^`]+)`", code_repl, working)
    working = re.sub(r"\*\*([^*]+)\*\*", bold_repl, working)
    working = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", italic_repl, working)
    working = escape_tex(working)

    for key, value in {**url_tokens, **code_tokens, **bold_tokens, **italic_tokens}.items():
        working = working.replace(escape_tex(key), value)

    return working


def title_case_heading(text: str) -> str:
    words = text.split()
    lowered = {"and", "of", "the", "for", "in", "to", "on"}
    result = []
    for index, word in enumerate(words):
        lower = word.lower()
        if index > 0 and lower in lowered:
            result.append(lower)
        else:
            result.append(lower.capitalize())
    return " ".join(result)


def flush_paragraph(out: list[str], paragraph: list[str]) -> None:
    if paragraph:
        out.append(convert_inline(" ".join(part.strip() for part in paragraph if part.strip())))
        out.append("")
        paragraph.clear()


def close_list(out: list[str], itemize_open: bool, enum_open: bool) -> tuple[bool, bool]:
    if itemize_open:
        out.append(r"\end{itemize}")
        out.append("")
    if enum_open:
        out.append(r"\end{enumerate}")
        out.append("")
    return False, False


def convert_table(table_lines: list[str]) -> list[str]:
    rows = []
    for line in table_lines:
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        rows.append(parts)

    if len(rows) < 2:
        return [convert_inline(" ".join(table_lines)), ""]

    header = rows[0]
    body = rows[2:] if re.fullmatch(r"[:\- ]+", "".join(rows[1])) else rows[1:]
    col_count = len(header)
    use_longtable = len(body) > 12

    if use_longtable:
        col_spec = "|" + "|".join([f">{{\\RaggedRight\\arraybackslash\\hspace{{0pt}}}}p{{{0.84/col_count:.2f}\\textwidth}}" for _ in range(col_count)]) + "|"
        out = [
            r"\begingroup",
            r"\footnotesize",
            r"\renewcommand{\arraystretch}{1.15}",
            r"\setlength{\tabcolsep}{4pt}",
            r"\begin{longtable}{" + col_spec + "}",
            r"\hline",
            " & ".join(r"\textbf{" + convert_inline(cell) + "}" for cell in header) + r" \\ \hline",
        ]
    else:
        col_spec = "|" + "|".join([r">{\RaggedRight\arraybackslash\hspace{0pt}}X" for _ in range(col_count)]) + "|"
        out = [
            r"\begingroup",
            r"\footnotesize",
            r"\renewcommand{\arraystretch}{1.15}",
            r"\setlength{\tabcolsep}{4pt}",
            r"\begin{table}[H]",
            r"\centering",
            r"\begin{tabularx}{\textwidth}{" + col_spec + "}",
            r"\hline",
            " & ".join(r"\textbf{" + convert_inline(cell) + "}" for cell in header) + r" \\ \hline",
        ]

    for row in body:
        padded = row + [""] * (col_count - len(row))
        out.append(" & ".join(convert_inline(cell) for cell in padded[:col_count]) + r" \\ \hline")

    if use_longtable:
        out.extend([r"\end{longtable}", r"\endgroup", ""])
    else:
        out.extend([r"\end{tabularx}", r"\end{table}", r"\endgroup", ""])
    return out


def convert_markdown(md_text: str) -> str:
    lines = md_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    paragraph: list[str] = []
    in_code = False
    in_equation = False
    equation_lines: list[str] = []
    table_buffer: list[str] = []
    itemize_open = False
    enum_open = False

    def flush_table_if_needed() -> None:
        nonlocal table_buffer
        if table_buffer:
            out.extend(convert_table(table_buffer))
            table_buffer = []

    for line in lines:
        stripped = line.strip()

        if in_equation:
            if stripped == r"\end{equation}":
                eq_tag = ""
                eq_body_parts: list[str] = []
                for eq_line in equation_lines:
                    eq_stripped = eq_line.strip()
                    tag_match = re.match(r"\\tag\{(.+)\}", eq_stripped)
                    if tag_match:
                        eq_tag = tag_match.group(1)
                    elif eq_stripped:
                        eq_body_parts.append(eq_stripped)

                eq_body = " ".join(eq_body_parts) if eq_body_parts else r"\text{}"
                if eq_tag:
                    out.append(r"\manualequation{" + eq_body + "}{" + eq_tag + "}")
                else:
                    out.append(r"\[" + eq_body + r"\]")
                out.append("")
                equation_lines = []
                in_equation = False
            else:
                equation_lines.append(line.rstrip())
            continue

        if in_code:
            if stripped.startswith("```"):
                out.append(r"\end{verbatim}")
                out.append("")
                in_code = False
            else:
                out.append(line.rstrip())
            continue

        if stripped.startswith("```"):
            flush_paragraph(out, paragraph)
            flush_table_if_needed()
            itemize_open, enum_open = close_list(out, itemize_open, enum_open)
            out.append(r"\begin{verbatim}")
            in_code = True
            continue

        if stripped == r"\begin{equation}":
            flush_paragraph(out, paragraph)
            flush_table_if_needed()
            itemize_open, enum_open = close_list(out, itemize_open, enum_open)
            in_equation = True
            equation_lines = []
            continue

        if stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2:
            flush_paragraph(out, paragraph)
            itemize_open, enum_open = close_list(out, itemize_open, enum_open)
            table_buffer.append(stripped)
            continue
        else:
            flush_table_if_needed()

        if not stripped:
            flush_paragraph(out, paragraph)
            itemize_open, enum_open = close_list(out, itemize_open, enum_open)
            continue

        if stripped.startswith("# "):
            flush_paragraph(out, paragraph)
            itemize_open, enum_open = close_list(out, itemize_open, enum_open)
            chapter_title = stripped[2:].strip()
            chapter_tex = convert_inline(chapter_title)
            if chapter_title.upper() == chapter_title and any(char.isalpha() for char in chapter_title):
                toc_title = convert_inline(title_case_heading(chapter_title))
                out.append(r"\chapter[" + toc_title + "]{" + chapter_tex + "}")
            else:
                out.append(r"\chapter{" + chapter_tex + "}")
            out.append("")
            continue

        if stripped.startswith("## "):
            flush_paragraph(out, paragraph)
            itemize_open, enum_open = close_list(out, itemize_open, enum_open)
            out.append(r"\section{" + convert_inline(stripped[3:].strip()) + "}")
            out.append("")
            continue

        if stripped.startswith("### "):
            flush_paragraph(out, paragraph)
            itemize_open, enum_open = close_list(out, itemize_open, enum_open)
            out.append(r"\subsection{" + convert_inline(stripped[4:].strip()) + "}")
            out.append("")
            continue

        standalone_caption = re.fullmatch(r"\*\*(Figure\s+\d+\.\d+.+|Table\s+\d+\.\d+.+)\*\*", stripped)
        if standalone_caption:
            flush_paragraph(out, paragraph)
            flush_table_if_needed()
            itemize_open, enum_open = close_list(out, itemize_open, enum_open)
            out.append(r"\begin{center}")
            out.append(r"\textbf{" + convert_inline(standalone_caption.group(1).strip()) + "}")
            out.append(r"\end{center}")
            out.append("")
            continue

        if stripped.startswith("\\"):
            flush_paragraph(out, paragraph)
            itemize_open, enum_open = close_list(out, itemize_open, enum_open)
            out.append(line.rstrip())
            continue

        bullet_match = re.match(r"[-*]\s+(.*)", stripped)
        if bullet_match:
            flush_paragraph(out, paragraph)
            if enum_open:
                enum_open = False
                out.append(r"\end{enumerate}")
                out.append("")
            if not itemize_open:
                out.append(r"\begin{itemize}")
                itemize_open = True
            out.append(r"\item " + convert_inline(bullet_match.group(1).strip()))
            continue

        enum_match = re.match(r"\d+\.\s+(.*)", stripped)
        if enum_match:
            flush_paragraph(out, paragraph)
            if itemize_open:
                itemize_open = False
                out.append(r"\end{itemize}")
                out.append("")
            if not enum_open:
                out.append(r"\begin{enumerate}")
                enum_open = True
            out.append(r"\item " + convert_inline(enum_match.group(1).strip()))
            continue

        paragraph.append(stripped)

    flush_paragraph(out, paragraph)
    flush_table_if_needed()
    itemize_open, enum_open = close_list(out, itemize_open, enum_open)

    return "\n".join(out).rstrip() + "\n"


def main() -> None:
    for md_name, tex_name in MD_TO_TEX.items():
        md_path = CHAPTERS_DIR / md_name
        tex_path = CHAPTERS_DIR / tex_name
        tex_path.write_text(convert_markdown(md_path.read_text(encoding="utf-8")), encoding="utf-8")
        print(f"Wrote {tex_path}")


if __name__ == "__main__":
    main()
