"""
Unified extractor that builds the 4 JSON data blocks the dashboard needs:
  - housing_total (DATA): Owner-Occupied + Investment combined, plus all_institutions
  - housing_oo (DATA_OO): Owner-Occupied only
  - housing_inv (DATA_INV): Investment only
  - deposits (DATA_DEPOSITS): Deposits by households

Compares a "current" period against a fixed "base" period (Jun 2025).
Outputs a single JSON file with all four blocks for HTML injection.

Usage:
    python extract_all_data.py <xlsx-file> <current-period YYYY-MM-DD> [--base YYYY-MM-DD] [--header N]
Defaults:
    base   = 2025-06-30
    header = 1   (back-series file uses row 1; quarterly summary uses row 0)
"""

import argparse
import json
import sys

import pandas as pd


def round_v(v, n=4):
    return round(float(v), n) if pd.notna(v) else 0.0


def build_pair_block(df_cur, df_base, value_col, key_cur, key_base):
    """Generic helper: build per-institution list with cur, base, market_share, growth."""
    names = sorted(set(df_cur['Institution Name'].tolist() + df_base['Institution Name'].tolist()))

    rows = []
    for name in names:
        cr = df_cur[df_cur['Institution Name'] == name]
        br = df_base[df_base['Institution Name'] == name]
        cv = float(cr.iloc[0][value_col]) if len(cr) > 0 and pd.notna(cr.iloc[0][value_col]) else 0.0
        bv = float(br.iloc[0][value_col]) if len(br) > 0 and pd.notna(br.iloc[0][value_col]) else 0.0
        if cv > 0 or bv > 0:
            rows.append({'name': name, 'cv': cv, 'bv': bv})

    total_cur = sum(r['cv'] for r in rows)
    total_base = sum(r['bv'] for r in rows)
    sys_growth = ((total_cur - total_base) / total_base) * 100 if total_base > 0 else 0.0

    institutions = []
    for r in rows:
        if r['cv'] <= 0:
            continue
        ms = (r['cv'] / total_cur) * 100 if total_cur > 0 else 0.0
        gr = ((r['cv'] - r['bv']) / r['bv']) * 100 if r['bv'] > 0 else 0.0
        institutions.append({
            'name': r['name'],
            key_cur: round(r['cv'], 1),
            key_base: round(r['bv'], 1),
            'market_share': round(ms, 4),
            'growth': round(gr, 4),
        })

    return institutions, round(total_cur, 1), round(total_base, 1), round(sys_growth, 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('xlsx')
    ap.add_argument('current', help='YYYY-MM-DD of latest period (e.g. 2026-03-31)')
    ap.add_argument('--base', default='2025-06-30')
    ap.add_argument('--header', type=int, default=1)
    ap.add_argument('--out', default='all_data.json')
    args = ap.parse_args()

    cur_ts = pd.Timestamp(args.current)
    base_ts = pd.Timestamp(args.base)

    df = pd.read_excel(args.xlsx, sheet_name='Table 1', header=args.header)
    df_cur = df[df['Period'] == cur_ts].copy()
    df_base = df[df['Period'] == base_ts].copy()

    if len(df_cur) == 0:
        print(f'ERROR: no rows for {cur_ts.date()}', file=sys.stderr)
        sys.exit(1)
    if len(df_base) == 0:
        print(f'ERROR: no rows for {base_ts.date()}', file=sys.stderr)
        sys.exit(1)

    print(f'Current ({cur_ts.date()}): {len(df_cur)} rows')
    print(f'Base    ({base_ts.date()}): {len(df_base)} rows')

    oo_col = 'Loans to households: Housing: Owner-occupied'
    inv_col = 'Loans to households: Housing: Investment'
    dep_col = 'Deposits by households'
    assets_col = 'Total residents assets'

    # Build a synthetic "Housing total = OO + INV" column on copies
    df_cur['__housing_total'] = df_cur[oo_col].fillna(0) + df_cur[inv_col].fillna(0)
    df_base['__housing_total'] = df_base[oo_col].fillna(0) + df_base[inv_col].fillna(0)

    # 1. Total housing
    hsg_inst, hsg_cur, hsg_base, hsg_sg = build_pair_block(
        df_cur, df_base, '__housing_total', 'housing_total_dec', 'housing_total_jun'
    )

    # all_institutions: every name with assets/housing total (current period only)
    all_inst = []
    for _, row in df_cur.iterrows():
        name = row['Institution Name']
        ta = float(row[assets_col]) if pd.notna(row[assets_col]) else 0.0
        ht = float(row['__housing_total']) if pd.notna(row['__housing_total']) else 0.0
        all_inst.append({
            'name': name,
            'total_assets': round(ta, 1),
            'housing_total': round(ht, 1),
        })
    all_inst.sort(key=lambda x: x['name'])

    data_housing = {
        'institutions': hsg_inst,
        'all_institutions': all_inst,
        'total_market_dec': hsg_cur,
        'total_market_jun': hsg_base,
        'system_growth': hsg_sg,
    }

    # 2. OO
    oo_inst, oo_cur, oo_base, oo_sg = build_pair_block(
        df_cur, df_base, oo_col, 'housing_total_dec', 'housing_total_jun'
    )
    data_oo = {
        'institutions': oo_inst,
        'total_market_dec': oo_cur,
        'total_market_jun': oo_base,
        'system_growth': oo_sg,
    }

    # 3. INV
    inv_inst, inv_cur, inv_base, inv_sg = build_pair_block(
        df_cur, df_base, inv_col, 'housing_total_dec', 'housing_total_jun'
    )
    data_inv = {
        'institutions': inv_inst,
        'total_market_dec': inv_cur,
        'total_market_jun': inv_base,
        'system_growth': inv_sg,
    }

    # 4. Deposits
    dep_inst, dep_cur, dep_base, dep_sg = build_pair_block(
        df_cur, df_base, dep_col, 'deposits_total_dec', 'deposits_total_jun'
    )
    data_deposits = {
        'institutions': dep_inst,
        'total_market_dec': dep_cur,
        'total_market_jun': dep_base,
        'system_growth': dep_sg,
    }

    output = {
        'meta': {
            'current_period': str(cur_ts.date()),
            'base_period': str(base_ts.date()),
            'source_file': args.xlsx,
        },
        'DATA': data_housing,
        'DATA_OO': data_oo,
        'DATA_INV': data_inv,
        'DATA_DEPOSITS': data_deposits,
    }

    with open(args.out, 'w') as f:
        json.dump(output, f, indent=2)

    print()
    print(f'Total Housing  cur=${hsg_cur/1000:.2f}B base=${hsg_base/1000:.2f}B growth={hsg_sg:.4f}%')
    print(f'OO Housing     cur=${oo_cur/1000:.2f}B  base=${oo_base/1000:.2f}B  growth={oo_sg:.4f}%')
    print(f'INV Housing    cur=${inv_cur/1000:.2f}B  base=${inv_base/1000:.2f}B  growth={inv_sg:.4f}%')
    print(f'Deposits       cur=${dep_cur/1000:.2f}B  base=${dep_base/1000:.2f}B  growth={dep_sg:.4f}%')
    print(f'\nOutput: {args.out}')
    print(f'Institutions: housing={len(hsg_inst)} oo={len(oo_inst)} inv={len(inv_inst)} dep={len(dep_inst)} all={len(all_inst)}')


if __name__ == '__main__':
    main()
