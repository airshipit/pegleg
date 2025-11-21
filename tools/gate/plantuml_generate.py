#!/usr/bin/env python3
"""
PlantUML diagram generator using public PlantUML server.
Python 3.12 compatible replacement for the unmaintained plantuml package.
"""

import sys
import zlib
import base64
import argparse
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Error: httpx package not installed. Run: pip install httpx")
    sys.exit(1)


def plantuml_encode(data):
    """
    Encode PlantUML text using the same encoding as the official PlantUML server.

    Args:
        data: PlantUML text content as string

    Returns:
        Encoded string suitable for PlantUML server URL
    """
    # Compress using zlib
    compressed = zlib.compress(data.encode('utf-8'))[2:-4]

    # Base64 encode using PlantUML's custom alphabet
    plantuml_alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'

    # Convert to base64 equivalent using PlantUML alphabet
    encoded = []
    for i in range(0, len(compressed), 3):
        if i + 2 < len(compressed):
            b1, b2, b3 = compressed[i], compressed[i+1], compressed[i+2]
            encoded.append(plantuml_alphabet[(b1 >> 2) & 0x3F])
            encoded.append(plantuml_alphabet[((b1 & 0x3) << 4) | ((b2 >> 4) & 0xF)])
            encoded.append(plantuml_alphabet[((b2 & 0xF) << 2) | ((b3 >> 6) & 0x3)])
            encoded.append(plantuml_alphabet[b3 & 0x3F])
        elif i + 1 < len(compressed):
            b1, b2 = compressed[i], compressed[i+1]
            encoded.append(plantuml_alphabet[(b1 >> 2) & 0x3F])
            encoded.append(plantuml_alphabet[((b1 & 0x3) << 4) | ((b2 >> 4) & 0xF)])
            encoded.append(plantuml_alphabet[(b2 & 0xF) << 2])
        else:
            b1 = compressed[i]
            encoded.append(plantuml_alphabet[(b1 >> 2) & 0x3F])
            encoded.append(plantuml_alphabet[(b1 & 0x3) << 4])

    return ''.join(encoded)


def generate_diagram(uml_file, server='http://www.plantuml.com/plantuml', output_dir=None):
    """
    Generate PNG diagram from UML file using PlantUML server.

    Args:
        uml_file: Path to .uml file
        server: PlantUML server URL (default: public server)
        output_dir: Output directory for PNG (default: same as input)

    Returns:
        True if successful, False otherwise
    """
    uml_path = Path(uml_file)

    if not uml_path.exists():
        print(f"Error: File not found: {uml_file}")
        return False

    # Read UML content
    try:
        with open(uml_path, 'r', encoding='utf-8') as f:
            uml_content = f.read()
    except Exception as e:
        print(f"Error reading {uml_file}: {e}")
        return False

    # Encode content
    encoded = plantuml_encode(uml_content)

    # Build server URL
    url = f"{server.rstrip('/')}/png/{encoded}"

    # Fetch PNG from server
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        print(f"Error: PlantUML server returned status {e.response.status_code}")
        print(f"URL: {url}")
        return False
    except Exception as e:
        print(f"Error fetching diagram from server: {e}")
        return False

    # Determine output path
    if output_dir:
        output_path = Path(output_dir) / f"{uml_path.stem}.png"
    else:
        output_path = uml_path.with_suffix('.png')

    # Write PNG file
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(response.content)
        print(f"Generated: {output_path}")
        return True
    except Exception as e:
        print(f"Error writing output file: {e}")
        return False


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description='Generate PlantUML diagrams using public server'
    )
    parser.add_argument(
        'files',
        nargs='+',
        help='UML file(s) to process'
    )
    parser.add_argument(
        '-o', '--out',
        help='Output directory for PNG files'
    )
    parser.add_argument(
        '-s', '--server',
        default='http://www.plantuml.com/plantuml',
        help='PlantUML server URL (default: http://www.plantuml.com/plantuml)'
    )

    args = parser.parse_args()

    # Process each file
    results = []
    for uml_file in args.files:
        success = generate_diagram(uml_file, server=args.server, output_dir=args.out)
        results.append({
            'filename': uml_file,
            'gen_success': success
        })

    # Print summary
    print(results)

    # Exit with error if any failed
    if not all(r['gen_success'] for r in results):
        sys.exit(1)


if __name__ == '__main__':
    main()
