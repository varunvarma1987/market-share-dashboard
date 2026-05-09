"""
Script to extract Deposits by households data from Excel file
Run this with: python extract_deposits_data.py
"""

try:
    import pandas as pd
    import json

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

    # Get the Deposits column
    deposits_col = 'Deposits by households'

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
            deposits_dec = dec_row[deposits_col] if pd.notna(dec_row[deposits_col]) else 0
        else:
            deposits_dec = 0

        # Get June row
        jun_row = df_jun[df_jun['Institution Name'] == name]
        if len(jun_row) > 0:
            jun_row = jun_row.iloc[0]
            deposits_jun = jun_row[deposits_col] if pd.notna(jun_row[deposits_col]) else 0
        else:
            deposits_jun = 0

        # Calculate growth
        deposits_growth = 0
        if deposits_dec > 0 and deposits_jun > 0:
            deposits_growth = ((deposits_dec - deposits_jun) / deposits_jun) * 100

        # Only add to result if there's any data
        if deposits_dec > 0 or deposits_jun > 0:
            result.append({
                'name': name,
                'deposits_dec': float(deposits_dec),
                'deposits_jun': float(deposits_jun),
                'market_share': 0,  # Will calculate after getting totals
                'growth': float(deposits_growth)
            })

    # Calculate total markets
    total_deposits_dec = sum(r['deposits_dec'] for r in result)
    total_deposits_jun = sum(r['deposits_jun'] for r in result)

    # Calculate system growth
    deposits_system_growth = ((total_deposits_dec - total_deposits_jun) / total_deposits_jun) * 100 if total_deposits_jun > 0 else 0

    # Update market shares
    for r in result:
        if r['deposits_dec'] > 0 and total_deposits_dec > 0:
            r['market_share'] = (r['deposits_dec'] / total_deposits_dec) * 100

    print(f"\nTotal Deposits Market (Dec): ${total_deposits_dec/1000:.2f}B")
    print(f"Total Deposits Market (Jun): ${total_deposits_jun/1000:.2f}B")
    print(f"Deposits System Growth: {deposits_system_growth:.4f}%")

    # Create JSON output
    output = {
        'institutions': [
            {
                'name': r['name'],
                'deposits_total_dec': r['deposits_dec'],
                'deposits_total_jun': r['deposits_jun'],
                'market_share': round(r['market_share'], 4),
                'growth': round(r['growth'], 4)
            }
            for r in result if r['deposits_dec'] > 0
        ],
        'total_market_dec': round(total_deposits_dec, 1),
        'total_market_jun': round(total_deposits_jun, 1),
        'system_growth': round(deposits_system_growth, 4)
    }

    # Write to file
    with open('deposits_data.json', 'w') as f:
        json.dump(output, f, indent=2)

    print("\n" + "="*80)
    print("Data extracted successfully!")
    print("Output saved to: deposits_data.json")
    print("\nTop 10 institutions by market share:")
    sorted_deposits = sorted(result, key=lambda x: x['market_share'], reverse=True)[:10]
    for inst in sorted_deposits:
        print(f"  - {inst['name']}: {inst['market_share']:.2f}%")

except ImportError:
    print("Error: pandas library not found.")
    print("Please install it with: pip install pandas openpyxl")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
