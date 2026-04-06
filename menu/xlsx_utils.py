from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict
from xml.etree import ElementTree as ET


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"main": MAIN_NS}


def _col_to_num(col: str) -> int:
    value = 0
    for char in col:
        value = value * 26 + ord(char.upper()) - 64
    return value


@dataclass
class WorkbookSheet:
    name: str
    cells: Dict[tuple[int, int], str]
    max_row: int
    max_col: int

    def get(self, row: int, col: int) -> str:
        return self.cells.get((row, col), "").strip()


class XlsxWorkbook:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.archive = zipfile.ZipFile(self.path)
        self.shared_strings = self._load_shared_strings()
        self.sheet_targets = self._load_sheet_targets()

    def _load_shared_strings(self) -> list[str]:
        if "xl/sharedStrings.xml" not in self.archive.namelist():
            return []
        root = ET.fromstring(self.archive.read("xl/sharedStrings.xml"))
        values = []
        for item in root:
            values.append("".join(text.text or "" for text in item.iter(f"{{{MAIN_NS}}}t")))
        return values

    def _load_sheet_targets(self) -> dict[str, str]:
        workbook = ET.fromstring(self.archive.read("xl/workbook.xml"))
        rels = ET.fromstring(self.archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
        targets: dict[str, str] = {}
        for sheet in workbook.find("main:sheets", NS):
            rel_id = sheet.attrib[f"{{{REL_NS}}}id"]
            targets[sheet.attrib["name"]] = f"xl/{rel_map[rel_id]}"
        return targets

    def read_sheet(self, name: str) -> WorkbookSheet:
        root = ET.fromstring(self.archive.read(self.sheet_targets[name]))
        cells: dict[tuple[int, int], str] = {}
        max_row = 0
        max_col = 0
        for row in root.findall(".//main:sheetData/main:row", NS):
            row_num = int(row.attrib["r"])
            max_row = max(max_row, row_num)
            for cell in row.findall("main:c", NS):
                ref = cell.attrib.get("r", "A1")
                col_letters = re.match(r"[A-Z]+", ref).group(0)
                col_num = _col_to_num(col_letters)
                max_col = max(max_col, col_num)
                cell_type = cell.attrib.get("t")
                value_node = cell.find("main:v", NS)
                if value_node is not None:
                    value = value_node.text or ""
                    if cell_type == "s" and value:
                        value = self.shared_strings[int(value)]
                else:
                    inline = cell.find("main:is", NS)
                    value = "".join(
                        text.text or "" for text in inline.iter(f"{{{MAIN_NS}}}t")
                    ) if inline is not None else ""
                cells[(row_num, col_num)] = value.strip()
        return WorkbookSheet(name=name, cells=cells, max_row=max_row, max_col=max_col)
