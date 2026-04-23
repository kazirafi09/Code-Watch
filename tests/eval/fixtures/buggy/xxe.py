import xml.etree.ElementTree as ET
def parse(xml_bytes):
    return ET.fromstring(xml_bytes)  # vulnerable to XXE with external entities
