"""Build a project-path-safe Pages site with an explicit HTTPS API origin."""

import argparse
import json
from pathlib import Path
import shutil
from urllib.parse import urlsplit


def build(output: Path, api_origin: str) -> None:
    parsed = urlsplit(api_origin)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
            or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
        raise ValueError('API origin must be an HTTPS origin, e.g. https://scarletcal.onrender.com')
    source = Path(__file__).resolve().parents[1] / 'src/scarletcal/web/static'
    output.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, output / 'static', dirs_exist_ok=True)
    html = source.joinpath('index.html').read_text()
    html = html.replace('"/static/', '"./static/').replace('href="/"', 'href="./"')
    output.joinpath('index.html').write_text(html)
    output.joinpath('static/config.js').write_text(
        'window.SCARLETCAL_API_ORIGIN = ' + json.dumps(api_origin.rstrip('/')) + ';\n')
    output.joinpath('.nojekyll').touch()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api-origin', required=True)
    parser.add_argument('--output', type=Path, default=Path('build/pages'))
    args = parser.parse_args()
    build(args.output, args.api_origin)
