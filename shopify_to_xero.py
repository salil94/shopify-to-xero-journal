import csv   
from datetime import datetime
from collections import defaultdict
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox

def safe_float(value):
    """Convert value to float, handling empty/invalid values."""
    if not value or str(value).strip() in ('', '-', 'nan'):
        return 0.0
    try:
        return float(str(value).strip().replace(',', ''))
    except ValueError:
        return 0.0

def get_payment_account(payment_method):
    """Map payment method to account code."""
    payment_mapping = {
        'Stripe': '102 - Stripe Account',
        'Cash on Delivery (COD)': '110 - Cash on Delivery',
        'Cash on Delivery (COD) + custom': '110 - Cash on Delivery', 
        'Cash on Delivery (COD) + Bank Deposit': '110 - Cash on Delivery',
        'Tamara Split Payments': '111 - Tamara',
        'Tamara': '111 - Tamara',
        'Tabby': '112 - Tabby',
        'Custom (POS)': '113 - POS Account',
        'Card': '102 - Card Account',
        'Cash': '101 - Cash Account'
    }
    
    payment_method = str(payment_method).strip()
    
    # Direct match
    if payment_method in payment_mapping:
        return payment_mapping[payment_method]
    
    # Partial match for complex names
    for key in payment_mapping:
        if key.lower() in payment_method.lower():
            return payment_mapping[key]
    
    # Default fallback
    return '102 - Stripe Account'

def has_international_orders(rows):
    """Check if any orders are international (non-AE)."""
    for row in rows:
        country = row.get('Billing Country', '').strip()
        if country and country != 'AE':
            return True
    return False

def process_single_date(rows, target_date_str):
    """Process orders for a single date and return journal entries."""
    
    if not rows:
        return []
    
    print(f"📅 Processing {target_date_str}: {len(rows)} orders")
    
    # Calculate totals
    totals = {
        'subtotal': 0.0,
        'shipping': 0.0,
        'discount': 0.0,
        'taxes': 0.0,
        'total': 0.0
    }
    
    payment_totals = defaultdict(float)
    zero_tax_revenue = 0.0
    
    for row in rows:
        subtotal = safe_float(row.get(' Subtotal '))
        shipping = safe_float(row.get(' Shipping '))
        discount = safe_float(row.get('Discount Amount'))
        taxes = safe_float(row.get(' Taxes '))
        total = safe_float(row.get(' Total '))
        payment_method = row.get('Payment Method', '').strip()
        
        totals['subtotal'] += subtotal
        totals['shipping'] += shipping
        totals['discount'] += discount
        totals['taxes'] += taxes
        totals['total'] += total
        
        # Track payment methods
        if payment_method:
            payment_totals[payment_method] += total
        
        # Track zero-tax revenue (international orders)
        if taxes == 0 and subtotal > 0:
            zero_tax_revenue += subtotal
    
    # Create journal entries
    target_date = datetime.strptime(target_date_str, "%d/%m/%Y").date()
    dot_date = target_date.strftime("%d.%m.%Y")
    narration = f"Shopify Sales {dot_date}"
    entries = []
    
    # 1. Main Taxable Revenue (Credit - negative)
    taxable_revenue = totals['subtotal'] - zero_tax_revenue + totals['discount']
    if taxable_revenue > 0:
        entries.append({
            '*Narration': narration,
            '*Date': target_date_str,
            'Description': narration,
            '*AccountCode': '208 - Revenue - Shopify',
            '*Tax Rate': 'Output VAT 5% (5%)',
            '*Amount': f"{-taxable_revenue:.2f}"
        })
    
    # 2. Shipping Revenue (Credit - negative)
    if totals['shipping'] > 0:
        entries.append({
            '*Narration': narration,
            '*Date': target_date_str,
            'Description': narration,
            '*AccountCode': '203 - Revenue - Shipping Retail',
            '*Tax Rate': 'Zero Rated Output VAT (0%)',
            '*Amount': f"{-totals['shipping']:.2f}"
        })
    
    # 3. Payment Method Entries (Debits - positive)
    for payment_method, amount in payment_totals.items():
        if amount > 0:
            account = get_payment_account(payment_method)
            entries.append({
                '*Narration': narration,
                '*Date': target_date_str,
                'Description': narration,
                '*AccountCode': account,
                '*Tax Rate': 'Tax Exempt (0%)',
                '*Amount': f"{amount:.2f}"
            })
    
    # 4. Sales Discount (Debit - positive)
    if totals['discount'] > 0:
        entries.append({
            '*Narration': narration,
            '*Date': target_date_str,
            'Description': narration,
            '*AccountCode': '205B - Sales Discount [Shopify]',
            '*Tax Rate': 'Output VAT 5% (5%)',
            '*Amount': f"{totals['discount']:.2f}"
        })
    
    # 5. Zero VAT Revenue (Credit - negative)
    if zero_tax_revenue > 0:
        entries.append({
            '*Narration': narration,
            '*Date': target_date_str,
            'Description': narration,
            '*AccountCode': '208 - Revenue - Shopify',
            '*Tax Rate': 'Zero Rated Output VAT (0%)',
            '*Amount': f"{-zero_tax_revenue:.2f}"
        })
    
    # Quick balance verification
    total_amount_sum = sum(float(entry['*Amount']) for entry in entries)
    balance_ok = abs(total_amount_sum - totals['taxes']) < 0.01
    
    status = "✅" if balance_ok else "⚠️"
    print(f"     {status} {totals['taxes']:.2f} AED tax, Balance: {total_amount_sum:.2f}")
    
    return entries

def convert_whole_month_to_journal(input_csv, output_csv, month, year):
    """Convert entire month of Shopify data to journal entries - day by day."""
    
    print(f"🗓️ Processing ALL DAYS for {month:02d}/{year}")
    print("=" * 60)
    
    # Read all rows and group by date
    date_groups = defaultdict(list)
    
    try:
        with open(input_csv, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            total_rows = 0
            
            for row in reader:
                created_at = row.get(" Created at ", "").strip()
                if created_at:
                    try:
                        # Parse date to check if it's in the target month/year
                        row_date = datetime.strptime(created_at, "%d/%m/%Y")
                        if row_date.month == month and row_date.year == year:
                            date_groups[created_at].append(row)
                            total_rows += 1
                    except ValueError:
                        continue
        
        print(f"📊 Found {total_rows} orders across {len(date_groups)} days in {month:02d}/{year}")
        
    except FileNotFoundError:
        print(f"❌ Error: Could not find {input_csv}")
        return
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return
    
    if not date_groups:
        print(f"❌ No orders found for {month:02d}/{year}")
        return
    
    # Process each date in chronological order
    all_entries = []
    processed_dates = []
    
    # Sort dates chronologically
    sorted_dates = sorted(date_groups.keys(), key=lambda x: datetime.strptime(x, "%d/%m/%Y"))
    
    print(f"\n📅 Processing dates chronologically:")
    print("-" * 50)
    
    for date_str in sorted_dates:
        rows = date_groups[date_str]
        try:
            entries = process_single_date(rows, date_str)
            if entries:
                all_entries.extend(entries)
                processed_dates.append(date_str)
        except Exception as e:
            print(f"❌ Error processing {date_str}: {e}")
            continue
    
    if not all_entries:
        print("❌ No journal entries generated")
        return
    
    # Write to CSV
    fieldnames = ['*Narration', '*Date', 'Description', '*AccountCode', '*Tax Rate', '*Amount']
    
    try:
        with open(output_csv, 'w', newline='', encoding='utf-8') as outf:
            writer = csv.DictWriter(outf, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_entries)
        
        print(f"\n✅ MONTHLY CONVERSION COMPLETE!")
        print("=" * 50)
        print(f"📁 Output saved to: {output_csv}")
        print(f"📊 Generated {len(all_entries)} total journal entries")
        print(f"📅 Processed {len(processed_dates)} days")
        print(f"🗓️ Date range: {min(processed_dates)} to {max(processed_dates)}")
        
        # Monthly summary by account
        print(f"\n💰 MONTHLY SUMMARY BY ACCOUNT:")
        print("-" * 60)
        account_totals = defaultdict(float)
        for entry in all_entries:
            account_totals[entry['*AccountCode']] += float(entry['*Amount'])
        
        for account, total in sorted(account_totals.items()):
            print(f"{account:<45} {total:>12.2f} AED")
        
        # Overall balance check
        total_sum = sum(account_totals.values())
        print(f"\n⚖️ OVERALL MONTHLY BALANCE:")
        print(f"Net sum of all entries: {total_sum:.2f} AED")
        if abs(total_sum) < 1.0:
            print("✅ Monthly journal is perfectly balanced!")
        else:
            print(f"⚠️ Monthly imbalance: {total_sum:.2f} AED")
        
        # Show structure preview
        print(f"\n📋 OUTPUT STRUCTURE PREVIEW:")
        print("Your file contains entries in this order:")
        current_date = ""
        entry_count = 0
        for entry in all_entries[:20]:  # Show first 20 entries
            if entry['*Date'] != current_date:
                if current_date:
                    print(f"     ... ({entry_count} entries for {current_date})")
                current_date = entry['*Date']
                entry_count = 0
                print(f"📅 {current_date}:")
            entry_count += 1
        
        if len(all_entries) > 20:
            print(f"     ... and {len(all_entries) - 20} more entries")
        
        print(f"\n🎯 Ready to import into Xero!")
        print(f"📝 Each day's entries are grouped together chronologically")
        
    except Exception as e:
        print(f"❌ Error writing output file: {e}")

if __name__ == "__main__":
    print("Shopify to Xero - WHOLE MONTH Converter")
    print("=" * 45)
    print("📅 Creates journal entries for entire month, day by day")
    print()

    # Initialize Tkinter root once
    root = tk.Tk()
    root.withdraw()  # Hide main window

    # Get input CSV file
    input_csv = filedialog.askopenfilename(
        title="Select Shopify CSV file",
        filetypes=[("CSV files", "*.csv")]
    )
    if not input_csv:
        messagebox.showerror("Error", "No file selected. Exiting.")
        exit()

    # Get month and year via simpledialog
    month = simpledialog.askinteger("Input", "Enter month (1-12):", minvalue=1, maxvalue=12)
    if month is None:
        messagebox.showerror("Error", "No month entered. Exiting.")
        exit()

    year = simpledialog.askinteger("Input", "Enter year (e.g., 2025):", minvalue=2020, maxvalue=2030)
    if year is None:
        messagebox.showerror("Error", "No year entered. Exiting.")
        exit()

    output_filename = f"monthly_journal_{month:02d}_{year}.csv"
    convert_whole_month_to_journal(input_csv, output_filename, month, year)
