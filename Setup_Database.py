import pandas as pd
from sqlalchemy import create_engine
import os

# Get the folder where this script is
folder = os.path.dirname(os.path.abspath(__file__))##(r"C:\Viswa\UBERRY\AI_Implementation"))

print("=" * 50)
print("🚀 Creating Agricultural Database...")
print("=" * 50)

# Read your Excel files
print("\n📁 Reading Excel files...")
try:
    dispatch_df = pd.read_excel(os.path.join(folder, 'Dispatch_fact.xlsx'))
    print(f"   ✅ Dispatch_fact.xlsx loaded: {len(dispatch_df)} records")
except FileNotFoundError:
    print("   ❌ ERROR: Dispatch_fact.xlsx not found!")
    print("   Please make sure the file is in the same folder as this script")
    exit(1)

try:
    stock_df = pd.read_excel(os.path.join(folder, 'Stock_fact.xlsx'))
    print(f"   ✅ Stock_Fact.xlsx loaded: {len(stock_df)} records")
except FileNotFoundError:
    print("   ❌ ERROR: Stock_fact.xlsx not found!")
    print("   Please make sure the file is in the same folder as this script")
    exit(1)

# Create SQLite database
print("\n💾 Creating SQLite database...")
db_path = os.path.join(folder, 'agricultural_data.db')
engine = create_engine(f'sqlite:///{db_path}')

# Store data in database
dispatch_df.to_sql('dispatch_fact', engine, if_exists='replace', index=False)
print(f"   ✅ dispatch_fact table created: {len(dispatch_df)} records")

stock_df.to_sql('stock_fact', engine, if_exists='replace', index=False)
print(f"   ✅ stock_fact table created: {len(stock_df)} records")

# Verify
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()

print("\n✅ SUCCESS!")
print("=" * 50)
print(f"Database created: {db_path}")
print(f"Tables: {', '.join(tables)}")
print("=" * 50)
print("\n🎉 Next step: Run the Streamlit app!")
print("   Command: streamlit run app.py")