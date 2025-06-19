# Shopify to Xero Monthly Journal Converter

This Python script converts Shopify order CSV data into journal entries formatted for import into Xero accounting software. It processes all orders for a specified month and year, grouping transactions by date, and handles multiple payment methods, taxes, discounts, and shipping.

---

## Features

- Processes Shopify CSV exports with columns such as *Subtotal*, *Shipping*, *Discount Amount*, *Taxes*, *Total*, *Payment Method*, and *Created at*.
- Generates journal entries grouped by date for entire month.
- Handles different payment methods and maps them to correct Xero account codes.
- Supports international orders with zero-rated VAT.
- Outputs a CSV formatted to Xero journal import specifications.
- Interactive file and date selection GUI (Tkinter dialogs).
- Includes monthly summary report and balance verification.

---

## Requirements

- Python 3.x
- Tkinter (usually included with Python)
- CSV file exported from Shopify with correct columns and date format (DD/MM/YYYY).

---

## How to Use

1. Run the script in a Python environment:
2. A file dialog will open to select the Shopify CSV export file.
3. Enter the month and year to process when prompted.
4. The script will generate a CSV file named `monthly_journal_MM_YYYY.csv` in the current directory.
5. Import this CSV file into Xero journal entries.

---

## Notes

- Ensure the Shopify CSV has the expected columns and date formats.
- The script uses Tkinter dialogs for ease of use, no command-line arguments needed.
- Check the console output for monthly summaries and any warnings about imbalances.

---

## Code Overview

- `safe_float(value)`: Safely converts string values to float.
- `get_payment_account(payment_method)`: Maps payment methods to Xero account codes.
- `process_single_date(rows, date)`: Processes transactions for a single date into journal entries.
- `convert_whole_month_to_journal(input_csv, output_csv, month, year)`: Processes the entire month's data.
- Tkinter GUI used to select input file and input month/year.

---

## License

MIT License

---

## Author

Sahil Loy Dsouza

