"""
Script to extract Owner-Occupied and Investment housing loan data from Excel file
Run this with: python extract_oo_inv_data.py
"""

try:
    import pandas as pd

    # Read the Excel file from 'Table 1' sheet
    df = pd.read_excel('market_share_dec25.xlsx', sheet_name='Table 1')

    # Display column names to verify
    print("Columns in the file:")
    for i, col in enumerate(df.columns):
        print(f"{i}: {col}")

    print("\n" + "="*80 + "\n")

    # Filter for December and June data
    df_dec = df[df['Period'] == pd.Timestamp('2025-12-31')].copy()
    df_jun = df[df['Period'] == pd.Timestamp('2025-06-30')].copy()

    print(f"December rows: {len(df_dec)}")
    print(f"June rows: {len(df_jun)}")

    # Get the OO and Investment columns (column M and N are index 12 and 13 in 0-based)
    oo_col = 'Loans to households: Housing: Owner-occupied'
    inv_col = 'Loans to households: Housing: Investment'

    # Get all unique institution names from both periods
    all_institutions = set(df_dec['Institution Name'].tolist() + df_jun['Institution Name'].tolist())

    print(f"Total unique institutions: {len(all_institutions)}")

    # Merge Dec and Jun data
    result = []

    for name in all_institutions:
        # Get December row
        dec_row = df_dec[df_dec['Institution Name'] == name]
        if len(dec_row) > 0:
            dec_row = dec_row.iloc[0]
            oo_dec = dec_row[oo_col] if pd.notna(dec_row[oo_col]) else 0
            inv_dec = dec_row[inv_col] if pd.notna(dec_row[inv_col]) else 0
        else:
            oo_dec = 0
            inv_dec = 0

        # Get June row
        jun_row = df_jun[df_jun['Institution Name'] == name]
        if len(jun_row) > 0:
            jun_row = jun_row.iloc[0]
            oo_jun = jun_row[oo_col] if pd.notna(jun_row[oo_col]) else 0
            inv_jun = jun_row[inv_col] if pd.notna(jun_row[inv_col]) else 0
        else:
            oo_jun = 0
            inv_jun = 0

        # Calculate growth
        oo_growth = 0
        if oo_dec > 0 and oo_jun > 0:
            oo_growth = ((oo_dec - oo_jun) / oo_jun) * 100

        inv_growth = 0
        if inv_dec > 0 and inv_jun > 0:
            inv_growth = ((inv_dec - inv_jun) / inv_jun) * 100

        # Only add to result if there's any data
        if oo_dec > 0 or oo_jun > 0 or inv_dec > 0 or inv_jun > 0:
            result.append({
                'name': name,
                'oo_dec': float(oo_dec),
                'oo_jun': float(oo_jun),
                'oo_market_share': 0,  # Will calculate after getting totals
                'oo_growth': float(oo_growth),
                'inv_dec': float(inv_dec),
                'inv_jun': float(inv_jun),
                'inv_market_share': 0,  # Will calculate after getting totals
                'inv_growth': float(inv_growth)
            })

    # Calculate total markets
    total_oo_dec = sum(r['oo_dec'] for r in result)
    total_oo_jun = sum(r['oo_jun'] for r in result)
    total_inv_dec = sum(r['inv_dec'] for r in result)
    total_inv_jun = sum(r['inv_jun'] for r in result)

    # Calculate system growth
    oo_system_growth = ((total_oo_dec - total_oo_jun) / total_oo_jun) * 100 if total_oo_jun > 0 else 0
    inv_system_growth = ((total_inv_dec - total_inv_jun) / total_inv_jun) * 100 if total_inv_jun > 0 else 0

    # Update market shares
    for r in result:
        if r['oo_dec'] > 0 and total_oo_dec > 0:
            r['oo_market_share'] = (r['oo_dec'] / total_oo_dec) * 100
        if r['inv_dec'] > 0 and total_inv_dec > 0:
            r['inv_market_share'] = (r['inv_dec'] / total_inv_dec) * 100

    print(f"\nTotal OO Market (Dec): ${total_oo_dec/1000:.2f}B")
    print(f"Total OO Market (Jun): ${total_oo_jun/1000:.2f}B")
    print(f"OO System Growth: {oo_system_growth:.4f}%")

    print(f"\nTotal INV Market (Dec): ${total_inv_dec/1000:.2f}B")
    print(f"Total INV Market (Jun): ${total_inv_jun/1000:.2f}B")
    print(f"INV System Growth: {inv_system_growth:.4f}%")

    # Create JSON output
    import json

    output = {
        'oo_institutions': [
            {
                'name': r['name'],
                'housing_total_dec': r['oo_dec'],
                'housing_total_jun': r['oo_jun'],
                'market_share': round(r['oo_market_share'], 4),
                'growth': round(r['oo_growth'], 4)
            }
            for r in result if r['oo_dec'] > 0
        ],
        'inv_institutions': [
            {
                'name': r['name'],
                'housing_total_dec': r['inv_dec'],
                'housing_total_jun': r['inv_jun'],
                'market_share': round(r['inv_market_share'], 4),
                'growth': round(r['inv_growth'], 4)
            }
            for r in result if r['inv_dec'] > 0
        ],
        'oo_total_market_dec': round(total_oo_dec, 1),
        'oo_total_market_jun': round(total_oo_jun, 1),
        'oo_system_growth': round(oo_system_growth, 4),
        'inv_total_market_dec': round(total_inv_dec, 1),
        'inv_total_market_jun': round(total_inv_jun, 1),
        'inv_system_growth': round(inv_system_growth, 4)
    }

    # Write to file
    with open('oo_inv_data.json', 'w') as f:
        json.dump(output, f, indent=2)

    print("\n" + "="*80)
    print("Data extracted successfully!")
    print("Output saved to: oo_inv_data.json")
    print("\nTop 5 OO institutions by market share:")
    sorted_oo = sorted(result, key=lambda x: x['oo_market_share'], reverse=True)[:5]
    for inst in sorted_oo:
        print(f"  - {inst['name']}: {inst['oo_market_share']:.2f}%")

    print("\nTop 5 INV institutions by market share:")
    sorted_inv = sorted(result, key=lambda x: x['inv_market_share'], reverse=True)[:5]
    for inst in sorted_inv:
        print(f"  - {inst['name']}: {inst['inv_market_share']:.2f}%")

except ImportError:
    print("Error: pandas library not found.")
    print("Please install it with: pip install pandas openpyxl")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
