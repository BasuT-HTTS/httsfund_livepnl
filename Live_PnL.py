import streamlit as st
import mysql.connector
import pandas as pd

class BasketExplorer:
    def __init__(self, host, username, password, database):
        self.conn = self.connect_to_database(host, username, password, database)

    def connect_to_database(self, host, username, password, database):
        try:
            conn = mysql.connector.connect(
                host=host,
                user=username,
                password=password,
                database=database
            )
            return conn
        except mysql.connector.Error as e:
            st.error(f"Database Connection Error: {e}")
            return None

    def fetch_data(self, query):
        try:
            if self.conn:
                return pd.read_sql(query, self.conn)
        except mysql.connector.Error as e:
            st.error(f"Error executing query: {e}")
            return pd.DataFrame()

    def fetch_last_row(self, table_name):
        try:
            query = f"SELECT * FROM {table_name} ORDER BY VDATE DESC, VTIME DESC LIMIT 1"
            return pd.read_sql(query, self.conn)
        except mysql.connector.Error as e:
            st.error(f"Error fetching last row: {e}")
            return pd.DataFrame()

    def process_data(self):
        # Fetch basket data
        basket_query = "SELECT * FROM httsbaskets"
        baskets_df = self.fetch_data(basket_query)

        if baskets_df.empty:
            st.warning("No basket data found.")
            return

        # Fetch the last row from PnL HTTS table
        pnl_df = self.fetch_last_row("pnlhtts")
        if pnl_df.empty:
            st.warning("No PnL data found.")
            return

        # Extract VDATE and VTIME for reference
        last_update_date = pnl_df['VDATE'].iloc[0]
        last_update_time = pnl_df['VTIME'].iloc[0]

        # Filter active baskets
        active_baskets = baskets_df[(baskets_df['STATUS'] == '1')]

        def calculate_pnl(basket_name):
            pnl_columns = [col for col in pnl_df.columns if col == basket_name]
            if not pnl_columns:
                return 0
            # Ensure values are converted to float and summed
            return pnl_df[pnl_columns].iloc[0].astype(float).sum()

        # Segregate by OWNED and CATEGORY
        live_intra = active_baskets[(active_baskets['CATEGORY'] == 'INTRA')]
        live_daily = active_baskets[(active_baskets['CATEGORY'] == 'DAILY')]
        paper_baskets = active_baskets[active_baskets['OWNED'] == 'PAPER']

        # Calculate PnL for each basket and store in a list
        intra_pnls = []
        for _, basket in live_intra.iterrows():
            pnl = calculate_pnl(basket['BASKETNAME'])
            intra_pnls.append({
                "Basket Name": basket['BASKETNAME'],
                "Category": basket['CATEGORY'],
                "PnL": pnl
            })

        daily_pnls = []
        for _, basket in live_daily.iterrows():
            pnl = calculate_pnl(basket['BASKETNAME'])
            daily_pnls.append({
                "Basket Name": basket['BASKETNAME'],
                "Category": basket['CATEGORY'],
                "PnL": pnl
            })

        paper_pnls = []
        for _, basket in paper_baskets.iterrows():
            pnl = calculate_pnl(basket['BASKETNAME'])
            paper_pnls.append({
                "Basket Name": basket['BASKETNAME'],
                "Category": basket['CATEGORY'],
                "PnL": pnl
            })

        # Convert lists to DataFrames
        intra_df = pd.DataFrame(intra_pnls)
        daily_df = pd.DataFrame(daily_pnls)
        paper_df = pd.DataFrame(paper_pnls)

        # Returning PnL summary
        return {
            "Live Intra": intra_df["PnL"].sum() if not intra_df.empty else 0,
            "Live Daily": daily_df["PnL"].sum() if not daily_df.empty else 0,
            "Total Live PnL": (intra_df["PnL"].sum() + daily_df["PnL"].sum()) if not intra_df.empty or not daily_df.empty else 0,
            "Paper": paper_df["PnL"].sum() if not paper_df.empty else 0,
            "Last Update": f"{last_update_date} {last_update_time}",
            "INTRA Baskets": intra_df,
            "DAILY Baskets": daily_df,
            "PAPER Baskets": paper_df
        }

def main():
    st.set_page_config(
        page_title="HTTS Live PnL", 
        page_icon=":book:", 
        layout="wide"
    )

    # Database connection details
    host = "162.251.85.8"
    username = "httsfive_pnluser"
    password = "@shana99P"
    database = "httsfive_pnl"

    # Initialize BasketExplorer
    explorer = BasketExplorer(host, username, password, database)

    # Process data and display
    results = explorer.process_data()
    if results:
        # Format last update
        last_update = pd.to_datetime(results["Last Update"])
        last_update_str = last_update.strftime("%d-%m-%Y, %H:%M")

        # Display metrics on cards
        col1, col2, col3 = st.columns(3)

        # Function to format PnL values with color
        def format_pnl(value):
            color = "green" if value > 0 else "red" if value < 0 else "black"
            return f'<span style="color:{color}; font-size:24px; font-weight:bold;">{value:.2f}</span>'

        with col1:
            st.metric("📊 Total HTTS PnL", f"{int(results['Total Live PnL'])}")

        with col2:
            st.metric("📊 HTTS INTRA PnL", f"{int(results['Live Intra'])}")

        with col3:
            st.metric("📊 HTTS DAILY PnL", f"{int(results['Live Daily'])}")

        # with col1:
            st.metric("📊 HTTS PAPER PnL", f"{int(results['Paper'])}")

        st.divider()
        st.markdown(f"**Last Updated:** {last_update_str}")
        # Add refresh button
        if st.button("🔄 Refresh"):
            st.query_params["refresh"] = "true"
        st.divider()

        # Display the details for each category (INTRA, DAILY, PAPER)
        # Create 3 columns for displaying the baskets side by side
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("INTRA Baskets")
            intra_df = results['INTRA Baskets']
            if not intra_df.empty:
                intra_df_sorted = intra_df.sort_values(by='PnL', ascending=False).drop(columns=['Category']).reset_index(drop=True)
                intra_df_sorted['PnL'] = intra_df_sorted['PnL'].astype(int)
                st.dataframe(intra_df_sorted, hide_index=True)
            else:
                st.write("No INTRA baskets available.")

        with col2:
            st.subheader("DAILY Baskets")
            daily_df =  results['DAILY Baskets']
            if not daily_df.empty:
                daily_df_sorted = daily_df.sort_values(by='PnL', ascending=False).drop(columns=['Category']).reset_index(drop=True)
                daily_df_sorted['PnL'] = daily_df_sorted['PnL'].astype(int)
                st.dataframe(daily_df_sorted, hide_index=True)
            else:
                st.write("No DAILY baskets available.")
        with col3:
            st.subheader("PAPER Baskets")
            paper_df = results['PAPER Baskets']
            if not paper_df.empty:
                paper_df_sorted = paper_df.sort_values(by='PnL', ascending=False).drop(columns=['Category']).reset_index(drop=True)
                paper_df_sorted['PnL'] = paper_df_sorted['PnL'].astype(int)
                st.dataframe(paper_df_sorted, hide_index=True)
            else:
                st.write("No PAPER baskets available.")

if __name__ == "__main__":
    main()
