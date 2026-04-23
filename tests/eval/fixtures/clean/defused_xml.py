from defusedxml import ElementTree as ET
def parse(xml_bytes):
    return ET.fromstring(xml_bytes)
