"""
Build a new dashboard HTML by:
  1. Replacing the 4 inline DATA blocks (DATA, DATA_OO, DATA_INV, DATA_DEPOSITS)
     with values from a JSON produced by extract_all_data.py.
  2. Updating period labels (e.g. "Dec 25" -> "Mar 26", "121 institutions" -> "119 institutions",
     "6m" -> "9m") so the page reads correctly for the new latest period.

Usage:
    python generate_dashboard.py <data.json> <source_html> <out_html> \
        --current-short "Mar 26" --current-long "March 2026" \
        --base-short "Jun 25" --base-long "June 2025" \
        --span-short "9m"
"""

import argparse
import json
import re
import sys


def replace_data_block(html, var_name, new_value_json):
    """Replace `const VAR = {...};` with the new JSON value."""
    # Match: const VAR = {...};   spanning a single line (the existing file has it all on one line)
    pattern = re.compile(
        r'const\s+' + re.escape(var_name) + r'\s*=\s*\{.*?\};',
        re.DOTALL,
    )
    replacement = f'const {var_name} = ' + json.dumps(new_value_json) + ';'
    new_html, n = pattern.subn(replacement, html, count=1)
    if n != 1:
        raise RuntimeError(f'Failed to replace block {var_name} (matches={n})')
    return new_html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('data_json')
    ap.add_argument('source_html')
    ap.add_argument('out_html')
    ap.add_argument('--current-short', required=True, help='e.g. "Mar 26"')
    ap.add_argument('--current-long', required=True, help='e.g. "March 2026"')
    ap.add_argument('--base-short', default='Jun 25')
    ap.add_argument('--base-long', default='June 2025')
    ap.add_argument('--prev-current-short', default='Dec 25')
    ap.add_argument('--prev-current-long', default='December 2025')
    ap.add_argument('--prev-span-short', default='6m')
    ap.add_argument('--span-short', default='9m', help='e.g. "9m" if base->current is 9 months')
    args = ap.parse_args()

    with open(args.data_json) as f:
        data = json.load(f)

    with open(args.source_html, encoding='utf-8') as f:
        html = f.read()

    # 1. Replace data blocks
    html = replace_data_block(html, 'DATA', data['DATA'])
    html = replace_data_block(html, 'DATA_OO', data['DATA_OO'])
    html = replace_data_block(html, 'DATA_INV', data['DATA_INV'])
    html = replace_data_block(html, 'DATA_DEPOSITS', data['DATA_DEPOSITS'])

    # 2. Date / period label substitutions
    institutions_count = len(data['DATA']['all_institutions'])

    substitutions = [
        # Long form (specific phrases first to avoid double-replace)
        (args.prev_current_long + ' & ' + args.base_long,
         args.current_long + ' & ' + args.base_long),
        ('— ' + args.prev_current_long, '— ' + args.current_long),
        # Short form
        ('· ' + args.prev_current_short, '· ' + args.current_short),
        ('(' + args.prev_current_short + ')', '(' + args.current_short + ')'),
        # nav-period element (exact div content)
        ('<div class="nav-period">' + args.prev_current_short + '</div>',
         '<div class="nav-period">' + args.current_short + '</div>'),
        # Span (6m -> 9m) wherever it appears as a standalone label
        ('· ' + args.prev_span_short + '<', '· ' + args.span_short + '<'),  # stat-label
        ('System Growth · ' + args.prev_span_short, 'System Growth · ' + args.span_short),
        (args.prev_span_short + ' Growth', args.span_short + ' Growth'),
        # Institution count in intro subtitle
        (re.compile(r'<em>\d+ institutions</em>'), f'<em>{institutions_count} institutions</em>'),
    ]

    for old, new in substitutions:
        if isinstance(old, re.Pattern):
            html, n = old.subn(new, html)
        else:
            n = html.count(old)
            if n > 0:
                html = html.replace(old, new)
        print(f'  [{n}x] {old!r:80s} -> {new!r}')

    with open(args.out_html, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'\nWrote: {args.out_html}')


if __name__ == '__main__':
    main()
