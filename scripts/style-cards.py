"""Keep provider-generated data unchanged; align the Summary Cards presentation."""
from pathlib import Path
import xml.etree.ElementTree as ET

for mode in ('dark', 'light'):
    path = Path(f'assets/time-{mode}.svg')
    if not path.exists():
        continue
    text = path.read_text()
    accent, muted = ('#58a6ff', '#8b949e') if mode == 'dark' else ('#0969da', '#57606a')
    text = text.replace('#0366d6', accent).replace('#40c463', accent).replace('#77909c', muted)
    text = text.replace('font-size: 22px', 'font-size: 18px; font-weight: 600')
    text = text.replace('stroke-opacity="1"', 'stroke-opacity="0"')
    ET.fromstring(text)
    path.write_text(text)
