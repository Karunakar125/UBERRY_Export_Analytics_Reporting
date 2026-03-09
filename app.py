# ============================================================
# 🌾 AGRICULTURAL EXPORT ANALYTICS DASHBOARD
# Built with Streamlit + Claude API
# ============================================================

# IMPORTS: Bring in the libraries we need
import streamlit as st
import pandas as pd
import sqlite3
from anthropic import Anthropic
import json

# ============================================================
# SECTION 1: PAGE CONFIGURATION
# ============================================================
# This tells Streamlit how to set up the page

st.set_page_config(
    page_title="EXPORT ANALYTICS DASHBOARD",  # Browser tab title
    layout="wide",  # Use full width of browser
    initial_sidebar_state="expanded"  # Show sidebar by default
)

# ============================================================
# SECTION 2: CUSTOM STYLING (CSS)
# ============================================================
# Make the dashboard look better with custom colors and styling

st.markdown("""
    <style>
    .main-title { 
        font-size: 3em;          /* Large title */
        color: #2E7D32;          /* Green color for agriculture theme */
        font-weight: bold;       /* Make it bold */
    }
    .metric-box { 
        background-color: #E8F5E9;  /* Light green background */
        padding: 20px;              /* Space inside box */
        border-radius: 10px;        /* Rounded corners */
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================
# SECTION 3: INITIALIZE ANTHROPIC CLIENT
# ============================================================
# Set up the connection to Claude API

client = Anthropic()

# ============================================================
# SECTION 4: DATABASE CONNECTION FUNCTION
# ============================================================
# This function creates a connection to the database
# @st.cache_resource means Streamlit remembers this connection
# so it doesn't recreate it every time
import os
import subprocess
from pathlib import Path

# Auto-generate database if missing
db_path = "agricultural_data.db"
if not os.path.exists(db_path):
    # Run setup_database.py to create it
    subprocess.run(["python", "setup_database.py"], check=True)
#@st.cache_resource
def get_db_connection():
    """
    Connect to SQLite database
    
    Returns:
        sqlite3.Connection: Connection to agricultural_data.db
    """
    return sqlite3.connect('agricultural_data.db')

# ============================================================
# SECTION 5: GET DATABASE SUMMARY FOR CLAUDE
# ============================================================
# This function gets information about what's in the database
# We send this info to Claude so it knows what tables/columns exist

def get_db_summary():
    """
    Get summary of database structure for Claude's context
    
    Returns:
        dict: Contains info about dispatch_fact and stock_fact tables
    """
    conn = get_db_connection()
    
    # Get info about dispatch_fact table
    dispatch_df = pd.read_sql("SELECT * FROM dispatch_fact LIMIT 10", conn)
    dispatch_columns = list(dispatch_df.columns)  # Get column names
    dispatch_count = pd.read_sql(
        "SELECT COUNT(*) as count FROM dispatch_fact", 
        conn
    )['count'][0]  # Count total rows
    
    # Get info about stock_fact table
    stock_df = pd.read_sql("SELECT * FROM stock_fact LIMIT 10", conn)
    stock_columns = list(stock_df.columns)  # Get column names
    stock_count = pd.read_sql(
        "SELECT COUNT(*) as count FROM stock_fact", 
        conn
    )['count'][0]  # Count total rows
    
    conn.close()
    
    # Return dictionary with all this info
    return {
        "dispatch": {
            "columns": dispatch_columns,
            "count": dispatch_count,
        },
        "stock": {
            "columns": stock_columns,
            "count": stock_count,
        }
    }

# ============================================================
# SECTION 6: EXECUTE SQL QUERIES
# ============================================================
# This function runs SQL queries on the database

def execute_sql_query(query: str) -> str:
    """
    Execute a SQL query on the database
    
    Args:
        query (str): SQL query to execute
    
    Returns:
        str: Query results as formatted text
    """
    try:
        conn = get_db_connection()
        result_df = pd.read_sql(query, conn)
        conn.close()
        return result_df.to_string()  # Convert to readable format
    except Exception as e:
        return f"❌ Query Error: {str(e)}"

# ============================================================
# SECTION 7: GET AI ANSWER FROM CLAUDE
# ============================================================
# This is the CORE function that talks to Claude

def get_ai_answer(user_question: str, conversation_history: list) -> str:
    """
    Send user question to Claude API and get intelligent response
    
    Args:
        user_question (str): What the user asks
        conversation_history (list): Previous messages in conversation
    
    Returns:
        str: Claude's response
    """
    
    # Get database context to send to Claude
    db_summary = get_db_summary()
    
    # Create the SYSTEM PROMPT - This tells Claude what it is and what data it has access to
    system_prompt = f"""You are an expert agricultural data analyst specializing in export operations.

You have access to two database tables with real agricultural export data:

1. DISPATCH_FACT table ({db_summary['dispatch']['count']} records)
   Columns: {', '.join(db_summary['dispatch']['columns'])}
   
   This table contains shipment/dispatch information:
   - DO_DISPATCH: Date when goods were dispatched
   - UNIT: Production unit (PAVITHRAN, PONNI, AMUDHA)
   - CUSTOMER: Customer code (QD, AC, IRCA, AF, etc)
   - CROP: Crop type/year
   - EXPORT_INVOICE_NUMBER: Invoice reference
   - QTY_DISPATCHED: Quantity dispatched in drums
   - And other related fields

2. STOCK_FACT table ({db_summary['stock']['count']} records)
   Columns: {', '.join(db_summary['stock']['columns'])}
   
   This table contains inventory/stock information:
   - BATCH_CODE: Batch identifier (UBIAMP, UBITMP, UBINMP)
   - UNIT: Production unit
   - PRODUCT_CODE: Product type (AMP, TMP, NMP)
   - PRODUCT: Product name (Alphonso, Totapuri, Neelam)
   - TOTAL_DRUMS: Total drums in batch
   - PRODUCT_RATIO: Composition ratio (70:30, 80:20, 100%)
   - And other related fields

When answering user questions:
1. Understand what data would answer the question
2. Think about which table(s) to query
3. Provide business insights, not just raw numbers
4. Be conversational and helpful
5. If you need to query data, explain what you're looking for
6. Give actionable recommendations when possible

Important: Be helpful and insightful. Analyze the data from a business perspective."""

    # Add the user's question to the conversation history
    conversation_history.append({
        "role": "user",
        "content": user_question
    })
    
    # Call Claude API with the conversation history
    response = client.messages.create(
        model="claude-opus-4-6",  # Use the latest Claude model
        max_tokens=1500,  # Limit response length
        system=system_prompt,  # Send the system prompt
        messages=conversation_history  # Send all previous messages too
    )
    
    # Extract Claude's response
    assistant_message = response.content[0].text
    
    # Add Claude's response to conversation history (so next question remembers this)
    conversation_history.append({
        "role": "assistant",
        "content": assistant_message
    })
    
    return assistant_message

# ============================================================
# SECTION 8: INITIALIZE SESSION STATE
# ============================================================
# Streamlit uses "session state" to remember things while the app is running
# This is like memory for the app during a user session

if "conversation_history" not in st.session_state:
    # If this is the first time, create an empty conversation history
    st.session_state.conversation_history = []

# ============================================================
# SECTION 9: PAGE TITLE AND SUBTITLE
# ============================================================
# Display the main heading

st.markdown(
    '<div class="main-title">🌾 Agricultural Export Analytics</div>', 
    unsafe_allow_html=True
)
st.markdown("**AI-Powered Natural Language Querying for Stock & Dispatch Data**")
st.divider()  # Add a horizontal line

# ============================================================
# SECTION 10: CREATE TABS
# ============================================================
# Create 3 tabs: Dashboard, AI Assistant, Raw Data
# Users can click between them

tab1, tab2, tab3 = st.tabs([
    "📊 Dashboard", 
    "🤖 AI Assistant", 
    "📋 Raw Data"
])

# ============================================================
# SECTION 11: TAB 1 - DASHBOARD
# ============================================================

with tab1:  # Everything indented here goes in Tab 1
    
    st.header("📊 Dashboard Overview")
    
    # Connect to database
    conn = get_db_connection()
    
    # ========== SECTION 11.1: KPI CARDS (Metrics) ==========
    # These are the big number cards showing key metrics
    
    col1, col2, col3, col4 = st.columns(4)  # 4 columns for 4 metrics
    
    with col1:
        # Calculate total stock across all batches
        total_stock = pd.read_sql(
            "SELECT SUM(TOTAL_DRUMS) as total FROM stock_fact", 
            conn
        )['total'][0]
        st.metric(
            "Total Stock (Drums)", 
            f"{int(total_stock):,}" if total_stock else 0,  # Format with commas
            delta="Current inventory"
        )
    
    with col2:
        # Calculate total dispatch quantity
        total_dispatch = pd.read_sql(
            "SELECT SUM(QTY_DISPATCHED) as total FROM dispatch_fact", 
            conn
        )['total'][0]
        st.metric(
            "Total Dispatched", 
            f"{int(total_dispatch):,}" if total_dispatch else 0,
            delta="YTD"
        )
    
    with col3:
        # Calculate balance (stock - dispatch)
        balance = int(total_stock or 0) - int(total_dispatch or 0)
        st.metric(
            "Balance Stock", 
            f"{balance:,}",
            delta="Remaining"
        )
    
    with col4:
        # Count unique customers
        unique_customers = pd.read_sql(
            "SELECT COUNT(DISTINCT CUSTOMER) as count FROM dispatch_fact", 
            conn
        )['count'][0]
        st.metric(
            "Active Customers", 
            unique_customers,
            delta="Total"
        )
    
    st.divider()  # Horizontal line to separate sections
    
    # ========== SECTION 11.2: STOCK BY UNIT CHART ==========
    # Bar chart showing stock distributed by unit
    
    st.subheader("📦 Stock Analysis by Unit")
    stock_by_unit = pd.read_sql("""
        SELECT UNIT, SUM(TOTAL_DRUMS) as TotalStock
        FROM stock_fact
        GROUP BY UNIT
        ORDER BY TotalStock DESC
    """, conn)
    
    if not stock_by_unit.empty:  # Only show if data exists
        st.bar_chart(
            data=stock_by_unit.set_index('UNIT'),  # UNIT becomes x-axis
            height=400
        )
    
    st.divider()
    
    # ========== SECTION 11.3: DISPATCH BY CUSTOMER CHART ==========
    # Bar chart showing top 10 customers by dispatch quantity
    
    st.subheader("👥 Dispatch by Customer (Top 10)")
    dispatch_by_customer = pd.read_sql("""
        SELECT CUSTOMER, SUM(QTY_DISPATCHED) as TotalDispatched
        FROM dispatch_fact
        GROUP BY CUSTOMER
        ORDER BY TotalDispatched DESC
        LIMIT 10
    """, conn)
    
    if not dispatch_by_customer.empty:  # Only show if data exists
        st.bar_chart(
            data=dispatch_by_customer.set_index('CUSTOMER'),
            height=400
        )
    
    conn.close()  # Close database connection

# ============================================================
# SECTION 12: TAB 2 - AI ASSISTANT
# ============================================================

with tab2:  # Everything indented here goes in Tab 2
    
    st.header("🤖 AI Data Assistant")
    
    # Show helpful tips
    st.info(
        "💡 Ask natural language questions about your stock and dispatch data. Examples:\n"
        "- 'Top 10 customers by dispatch'\n"
        "- 'Which products move fastest?'\n"
        "- 'Show me stock by unit'\n"
        "- 'Customer concentration risk'"
    )
    
    # ========== SECTION 12.1: DISPLAY CONVERSATION HISTORY ==========
    # Show all previous messages in this conversation
    
    for message in st.session_state.conversation_history:
        if message["role"] == "user":
            st.chat_message("user").write(message["content"])  # User messages aligned right
        else:
            st.chat_message("assistant").write(message["content"])  # Assistant messages aligned left
    
    # ========== SECTION 12.2: CHAT INPUT ==========
    # Text box where user types their question
    
    user_input = st.chat_input("Ask Claude about your data...")
    
    # If user typed something and pressed enter:
    if user_input:
        # Show user's message immediately
        st.chat_message("user").write(user_input)
        
        # Show thinking indicator while Claude is working
        with st.spinner("🤔 Claude is analyzing your data..."):
            # Get Claude's response
            response = get_ai_answer(
                user_input, 
                st.session_state.conversation_history
            )
            # Show Claude's response
            st.chat_message("assistant").write(response)

# ============================================================
# SECTION 13: TAB 3 - RAW DATA EXPLORER
# ============================================================

with tab3:  # Everything indented here goes in Tab 3
    
    st.header("📋 Raw Data Explorer")
    
    # ========== SECTION 13.1: TABLE SELECTOR ==========
    # Dropdown to choose which table to view
    
    table_choice = st.selectbox(
        "Select table:", 
        ["dispatch_fact", "stock_fact"]  # 2 options
    )
    
    # ========== SECTION 13.2: DISPLAY DATA ==========
    # Show first 50 rows of selected table
    
    conn = get_db_connection()
    if table_choice == "dispatch_fact":
        df = pd.read_sql("SELECT * FROM dispatch_fact LIMIT 50", conn)
    else:
        df = pd.read_sql("SELECT * FROM stock_fact LIMIT 50", conn)
    
    st.dataframe(df, use_container_width=True)  # Full width table
    conn.close()

# ============================================================
# SECTION 14: FOOTER
# ============================================================

st.divider()
st.caption("🌾 Agricultural Export Analytics • Powered by Claude API + Streamlit")