"""Validate the versioned contract's examples without claiming runtime coverage."""
import json
import re
from pathlib import Path

text = Path('interface_contracts_specification.md').read_text()
examples = re.findall(r'```json\s*\n(.*?)\n```', text, re.S)
assert len(examples) >= 7, 'Expected all request/response examples'
for index, example in enumerate(examples, 1):
    value = json.loads(example)
    assert isinstance(value, dict), f'Example {index} must be a JSON object'
for section in ['Part 1:', 'Part 2:', 'Part 3:', 'Part 4:', 'Errors and verification boundary']:
    assert section in text, f'Missing {section}'
print(f'Validated {len(examples)} JSON examples and required contract sections')
