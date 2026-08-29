"""
utils/exporters.py
================================================================================
Data-export helpers used by the Admin dashboard. Supports CSV, JSON and XML
export of platform data straight from the UI. Each function writes a file and
returns the path it wrote to.
================================================================================
"""

import csv
import json
import os
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom


def _rows_to_dicts(rows):
    """Convert a list of sqlite3.Row into a list of plain dicts."""
    return [dict(r) for r in rows]


def export_csv(rows, path):
    """Write rows (sqlite3.Row list) to a CSV file at `path`."""
    data = _rows_to_dicts(rows)
    if not data:
        # Still create an empty file with no header — avoids a crash.
        open(path, "w", newline="", encoding="utf-8").close()
        return path
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        writer.writeheader()
        writer.writerows(data)
    return path


def export_json(rows, path):
    """Write rows to a pretty-printed JSON array at `path`."""
    data = _rows_to_dicts(rows)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def export_xml(rows, path, root_tag="data", row_tag="record"):
    """Write rows to a nicely-indented XML document at `path`."""
    data = _rows_to_dicts(rows)
    root = ET.Element(root_tag)
    for record in data:
        item = ET.SubElement(root, row_tag)
        for key, value in record.items():
            child = ET.SubElement(item, str(key))
            child.text = "" if value is None else str(value)
    raw = ET.tostring(root, encoding="utf-8")
    pretty = minidom.parseString(raw).toprettyxml(indent="  ")
    with open(path, "w", encoding="utf-8") as f:
        f.write(pretty)
    return path
