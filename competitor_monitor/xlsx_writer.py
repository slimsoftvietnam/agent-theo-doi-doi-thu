from __future__ import annotations

import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr


def _column_name(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _safe_sheet_name(name: str) -> str:
    return re.sub(r"[\\/*?:\[\]]", "_", name)[:31] or "Sheet"


def _excel_serial(value: datetime) -> float:
    if value.tzinfo:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    epoch = datetime(1899, 12, 30)
    return (value - epoch).total_seconds() / 86400


def _parse_date(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}T", value):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _cell_xml(row: int, col: int, value, style: int = 0) -> str:
    ref = f"{_column_name(col)}{row}"
    attrs = f' r="{ref}"' + (f' s="{style}"' if style else "")
    date = _parse_date(value)
    if date:
        return f"<c{attrs} s=\"2\"><v>{_excel_serial(date):.10f}</v></c>"
    if isinstance(value, bool):
        return f"<c{attrs} t=\"b\"><v>{1 if value else 0}</v></c>"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"<c{attrs}><v>{value}</v></c>"
    text = "" if value is None else str(value)
    preserve = ' xml:space="preserve"' if text != text.strip() else ""
    return f"<c{attrs} t=\"inlineStr\"><is><t{preserve}>{escape(text)}</t></is></c>"


def _sheet_xml(rows: list[list], widths: list[float], hyperlink_columns: set[int] | None = None, freeze_rows: int = 1, cell_styles: dict[str, int] | None = None) -> tuple[str, str | None]:
    hyperlink_columns = hyperlink_columns or set()
    cell_styles = cell_styles or {}
    row_xml = []
    hyperlinks = []
    rels = []
    for r_index, row in enumerate(rows, 1):
        cells = []
        for c_index, value in enumerate(row, 1):
            ref = f"{_column_name(c_index)}{r_index}"
            style = cell_styles.get(ref, 1 if r_index == 1 else 4 if c_index in hyperlink_columns and value else 0)
            cells.append(_cell_xml(r_index, c_index, value, style))
            if r_index > 1 and c_index in hyperlink_columns and isinstance(value, str) and value.startswith(("http://", "https://")):
                rel_id = f"rId{len(rels) + 1}"
                hyperlinks.append(f'<hyperlink ref="{_column_name(c_index)}{r_index}" r:id="{rel_id}"/>')
                rels.append(f'<Relationship Id="{rel_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target={quoteattr(value)} TargetMode="External"/>')
        row_xml.append(f'<row r="{r_index}">{"".join(cells)}</row>')
    max_col = max((len(row) for row in rows), default=1)
    max_row = max(len(rows), 1)
    columns = "".join(f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>' for index, width in enumerate(widths, 1))
    pane = f'<pane ySplit="{freeze_rows}" topLeftCell="A{freeze_rows + 1}" activePane="bottomLeft" state="frozen"/>' if freeze_rows else ""
    auto_filter = f'<autoFilter ref="A1:{_column_name(max_col)}{max_row}"/>' if len(rows) > 1 else ""
    hyperlink_xml = f'<hyperlinks>{"".join(hyperlinks)}</hyperlinks>' if hyperlinks else ""
    xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<dimension ref="A1:{_column_name(max_col)}{max_row}"/><sheetViews><sheetView workbookViewId="0" showGridLines="0">{pane}</sheetView></sheetViews>
<sheetFormatPr defaultRowHeight="18"/><cols>{columns}</cols><sheetData>{''.join(row_xml)}</sheetData>{auto_filter}{hyperlink_xml}
</worksheet>'''
    rel_xml = None
    if rels:
        rel_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{''.join(rels)}</Relationships>'''
    return xml, rel_xml


def write_xlsx(path: str | Path, sheets: list[dict]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet_defs = []
    workbook_rels = []
    overrides = []
    payloads = []
    for index, spec in enumerate(sheets, 1):
        name = _safe_sheet_name(spec["name"])
        sheet_defs.append(f'<sheet name={quoteattr(name)} sheetId="{index}" r:id="rId{index}"/>')
        workbook_rels.append(f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>')
        overrides.append(f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
        payloads.append(_sheet_xml(spec["rows"], spec.get("widths", [18] * max(1, len(spec["rows"][0]))), set(spec.get("hyperlink_columns", [])), spec.get("freeze_rows", 1), spec.get("cell_styles", {})))
    style_rel_id = len(sheets) + 1
    workbook_rels.append(f'<Relationship Id="rId{style_rel_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>')
    content_types = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>{''.join(overrides)}</Types>'''
    root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'''
    workbook = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>{''.join(sheet_defs)}</sheets></workbook>'''
    workbook_rels_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{''.join(workbook_rels)}</Relationships>'''
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="3"><font><sz val="10"/><name val="Arial"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="10"/><name val="Arial"/></font><font><color rgb="FF0563C1"/><u/><sz val="10"/><name val="Arial"/></font></fonts>
<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF1F4E78"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="6"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFill="1" applyFont="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="22" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/><xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/><xf numFmtId="10" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/></cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'''
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/styles.xml", styles)
        for index, (sheet_xml, rel_xml) in enumerate(payloads, 1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", sheet_xml)
            if rel_xml:
                archive.writestr(f"xl/worksheets/_rels/sheet{index}.xml.rels", rel_xml)
    return target
