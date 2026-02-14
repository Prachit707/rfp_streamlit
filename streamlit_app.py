"""
MERX Opportunities Dashboard
Streamlit app to display scraped MERX data
"""

import streamlit as st
import json
import pandas as pd
from datetime import datetime
import os

# Page config
st.set_page_config(
    page_title="MERX Opportunities Dashboard",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .opportunity-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin-bottom: 1rem;
    }
    .opportunity-title {
        font-size: 1.3rem;
        font-weight: bold;
        color: #0e1117;
        margin-bottom: 0.5rem;
    }
    .opportunity-org {
        color: #555;
        font-size: 1rem;
        margin-bottom: 0.5rem;
    }
    .date-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.9rem;
        margin-right: 0.5rem;
    }
    .published-badge {
        background-color: #d4edda;
        color: #155724;
    }
    .closing-badge {
        background-color: #fff3cd;
        color: #856404;
    }
    .urgent-badge {
        background-color: #f8d7da;
        color: #721c24;
    }
    .link-button {
        background-color: #1f77b4;
        color: white;
        padding: 0.5rem 1rem;
        text-decoration: none;
        border-radius: 5px;
        display: inline-block;
        margin-top: 0.5rem;
    }
    .link-button:hover {
        background-color: #145a8c;
        color: white;
        text-decoration: none;
    }
    .stats-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .stats-number {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .stats-label {
        color: #666;
        font-size: 0.9rem;
    }
    </style>
""", unsafe_allow_html=True)


def load_data(file_path: str = "merx_results.json"):
    """Load MERX data from JSON file."""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        else:
            return []
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return []


def parse_date(date_str: str):
    """Try to parse a date string."""
    if not date_str:
        return None
    
    # Common date formats
    formats = [
        '%Y-%m-%d',
        '%b %d, %Y',
        '%B %d, %Y',
        '%d/%m/%Y',
        '%m/%d/%Y',
        '%Y/%m/%d',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
    
    return None


def main():
    # Header
    st.markdown('<div class="main-header">📋 MERX Opportunities Dashboard</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Load data
    data = load_data()
    
    if not data:
        st.warning("⚠️ No data available. Please run the scraper first to collect opportunities.")
        st.info("Upload your `merx_results.json` file using the sidebar, or place it in the app directory.")
        
        # File uploader
        uploaded_file = st.file_uploader("Upload MERX Results JSON", type=['json'])
        if uploaded_file:
            data = json.load(uploaded_file)
            st.success(f"✅ Loaded {len(data)} opportunities!")
    
    if data:
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Sidebar filters
        st.sidebar.header("🔍 Filters")
        
        # Search
        search_query = st.sidebar.text_input("Search opportunities", "")
        
        # Organization filter
        organizations = sorted(df['organization'].unique())
        selected_orgs = st.sidebar.multiselect(
            "Filter by Organization",
            organizations,
            default=[]
        )
        
        # Date range filter
        st.sidebar.subheader("Date Filters")
        filter_by_closing = st.sidebar.checkbox("Filter by closing date", value=False)
        
        # Stats at top
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
                <div class="stats-card">
                    <div class="stats-number">{len(data)}</div>
                    <div class="stats-label">Total Opportunities</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            unique_orgs = len(df['organization'].unique())
            st.markdown(f"""
                <div class="stats-card">
                    <div class="stats-number">{unique_orgs}</div>
                    <div class="stats-label">Organizations</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col3:
            with_links = len([d for d in data if d.get('link')])
            st.markdown(f"""
                <div class="stats-card">
                    <div class="stats-number">{with_links}</div>
                    <div class="stats-label">With Links</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col4:
            # Last updated
            if data:
                last_scraped = data[0].get('scraped_at', 'Unknown')
                try:
                    last_date = datetime.fromisoformat(last_scraped).strftime('%b %d, %Y')
                except:
                    last_date = last_scraped[:10] if last_scraped else 'Unknown'
            else:
                last_date = 'Unknown'
            
            st.markdown(f"""
                <div class="stats-card">
                    <div class="stats-label">Last Updated</div>
                    <div style="font-size: 1.1rem; font-weight: bold; color: #666;">{last_date}</div>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Filter data
        filtered_data = data.copy()
        
        # Apply search filter
        if search_query:
            filtered_data = [
                d for d in filtered_data
                if search_query.lower() in d.get('title', '').lower()
                or search_query.lower() in d.get('organization', '').lower()
            ]
        
        # Apply organization filter
        if selected_orgs:
            filtered_data = [
                d for d in filtered_data
                if d.get('organization') in selected_orgs
            ]
        
        # Display view selector
        view_mode = st.radio(
            "View Mode",
            ["📋 Cards", "📊 Table", "📈 Analytics"],
            horizontal=True
        )
        
        st.markdown("---")
        
        if view_mode == "📋 Cards":
            # Card View
            if not filtered_data:
                st.warning("No opportunities match your filters.")
            else:
                st.subheader(f"Showing {len(filtered_data)} opportunities")
                
                for opp in filtered_data:
                    title = opp.get('title', 'No title')
                    org = opp.get('organization', 'Unknown organization')
                    published = opp.get('published_date', '')
                    closing = opp.get('closing_date', '')
                    link = opp.get('link', '')
                    
                    # Check if closing soon (if we can parse the date)
                    closing_date = parse_date(closing)
                    is_urgent = False
                    if closing_date:
                        days_until_close = (closing_date - datetime.now()).days
                        is_urgent = days_until_close <= 7
                    
                    st.markdown(f"""
                        <div class="opportunity-card">
                            <div class="opportunity-title">{title}</div>
                            <div class="opportunity-org">🏢 {org}</div>
                            <div style="margin: 0.8rem 0;">
                                {f'<span class="date-badge published-badge">📅 Published: {published}</span>' if published else ''}
                                {f'<span class="date-badge {"urgent-badge" if is_urgent else "closing-badge"}">⏰ Closes: {closing}</span>' if closing else ''}
                            </div>
                            {f'<a href="{link}" target="_blank" class="link-button">🔗 View on MERX</a>' if link else ''}
                        </div>
                    """, unsafe_allow_html=True)
        
        elif view_mode == "📊 Table":
            # Table View
            if not filtered_data:
                st.warning("No opportunities match your filters.")
            else:
                st.subheader(f"Showing {len(filtered_data)} opportunities")
                
                # Create DataFrame for table view
                table_df = pd.DataFrame(filtered_data)
                
                # Select and reorder columns
                display_columns = ['title', 'organization', 'published_date', 'closing_date', 'link']
                available_columns = [col for col in display_columns if col in table_df.columns]
                
                # Rename columns for display
                column_names = {
                    'title': 'Title',
                    'organization': 'Organization',
                    'published_date': 'Published',
                    'closing_date': 'Closes',
                    'link': 'Link'
                }
                
                display_df = table_df[available_columns].copy()
                display_df.columns = [column_names.get(col, col) for col in available_columns]
                
                # Make links clickable
                if 'Link' in display_df.columns:
                    display_df['Link'] = display_df['Link'].apply(
                        lambda x: f'<a href="{x}" target="_blank">View</a>' if x else ''
                    )
                
                st.write(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)
                
                # Download button
                csv = table_df[available_columns].to_csv(index=False)
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name=f"merx_opportunities_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        
        else:  # Analytics View
            st.subheader("📈 Analytics")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Opportunities by Organization")
                org_counts = df['organization'].value_counts().head(10)
                st.bar_chart(org_counts)
            
            with col2:
                st.markdown("#### Opportunities by Page")
                if 'page' in df.columns:
                    page_counts = df['page'].value_counts().sort_index()
                    st.bar_chart(page_counts)
            
            # Date distribution
            st.markdown("#### Closing Dates Distribution")
            if 'closing_date' in df.columns:
                closing_dates = df['closing_date'].value_counts().head(15)
                st.bar_chart(closing_dates)
            
            # Top organizations table
            st.markdown("#### Top 10 Organizations")
            top_orgs = df['organization'].value_counts().head(10).reset_index()
            top_orgs.columns = ['Organization', 'Count']
            st.dataframe(top_orgs, use_container_width=True)
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style="text-align: center; color: #666; font-size: 0.9rem;">
            Data scraped from <a href="https://www.merx.com/public/solicitations/open" target="_blank">MERX</a> | 
            Last updated: {last_update} | 
            Built with Streamlit
        </div>
    """.format(
        last_update=datetime.now().strftime('%B %d, %Y')
    ), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
