"""
MERX Opportunities Dashboard
Streamlit app with workflow trigger and on-demand description fetching
"""

import streamlit as st
import json
import pandas as pd
from datetime import datetime, date
import os
import requests
from bs4 import BeautifulSoup

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
    .trigger-section {
        background-color: #e7f3ff;
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px solid #1f77b4;
        margin-bottom: 2rem;
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
    
    formats = [
        '%Y-%m-%d',
        '%Y/%m/%d',
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


def fetch_description(url: str) -> str:
    """Fetch description from MERX opportunity page."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try multiple selectors for description
            selectors = [
                'div.description',
                'div.solicitation-description',
                'div.opportunity-description',
                'div[class*="description"]',
                'div[class*="detail"]',
                'section.description',
                '.notice-description',
                '#description',
                'div.content',
                'div.main-content'
            ]
            
            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(separator='\n', strip=True)
                    if len(text) > 50:
                        return text
            
            # Fallback: get all paragraphs
            paragraphs = soup.find_all('p')
            if paragraphs:
                texts = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20]
                if texts:
                    return '\n\n'.join(texts[:5])
        
        return "Description not available on this page."
        
    except requests.Timeout:
        return "⏱️ Request timed out. The page took too long to load."
    except Exception as e:
        return f"⚠️ Error loading description: {str(e)}"


def trigger_workflow(github_token: str, repo: str, search_term: str, max_pages: int, min_date: str):
    """Trigger GitHub Actions workflow."""
    
    url = f"https://api.github.com/repos/{repo}/actions/workflows/scraper.yml/dispatches"
    
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    data = {
        "ref": "main",
        "inputs": {
            "search_term": search_term,
            "max_pages": str(max_pages),
            "min_published_date": min_date
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 204:
            return True
        else:
            st.error(f"GitHub API Error: Status {response.status_code}")
            st.error(f"Response: {response.text}")
            return False
    except Exception as e:
        st.error(f"Error triggering workflow: {e}")
        return False


def main():
    # Header
    st.markdown('<div class="main-header">📋 MERX Opportunities Dashboard</div>', unsafe_allow_html=True)
    
    # Workflow Trigger Section
    st.markdown('<div class="trigger-section">', unsafe_allow_html=True)
    st.markdown("### 🔄 Run New Scrape")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Get the date from the data if available, otherwise use default
        default_date = date(2025, 12, 10)
        
        # Try to get date from existing data
        data_check = load_data()
        if data_check:
            published_dates = [d.get('published_date', '') for d in data_check if d.get('published_date')]
            if published_dates:
                parsed_dates = [parse_date(d) for d in published_dates]
                valid_dates = [d for d in parsed_dates if d is not None]
                if valid_dates:
                    default_date = min(valid_dates).date()
        
        min_date = st.date_input(
            "📅 Select minimum published date (opportunities published on or after this date will be collected)",
            value=default_date,
            key="date"
        )
    
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        trigger_button = st.button("🚀 Run Scraper", type="primary", use_container_width=True)
    
    if trigger_button:
        # Fixed values
        search_term = "health"
        max_pages = 5
        
        # Get secrets
        try:
            github_token = st.secrets["GITHUB_TOKEN"]
            github_repo = st.secrets["GITHUB_REPO"]
        except Exception as e:
            st.error("⚠️ GitHub credentials not configured. Please add GITHUB_TOKEN and GITHUB_REPO to Streamlit secrets.")
            st.stop()
        
        with st.spinner("Triggering workflow... This will take 2-3 minutes to complete."):
            min_date_str = min_date.strftime('%Y-%m-%d')
            success = trigger_workflow(github_token, github_repo, search_term, max_pages, min_date_str)
            
            if success:
                st.success(f"✅ Workflow triggered successfully! Scraping with date >= {min_date_str}")
                st.info("⏳ The scraper is running now. Refresh this page in 2-3 minutes to see new results.")
            else:
                st.error("❌ Failed to trigger workflow. Check your GitHub token and permissions.")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Load data
    data = load_data()
    
    if not data:
        st.warning("⚠️ No data available. Run the scraper above to collect opportunities.")
        st.stop()
    
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
    
    # Stats at top
    col1, col2, col3 = st.columns(3)
    
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
    
    # Add spacing
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Show date filter info
    if data:
        # Get the earliest published date from the data
        published_dates = [d.get('published_date', '') for d in data if d.get('published_date')]
        if published_dates:
            # Try to find the minimum date
            parsed_dates = [parse_date(d) for d in published_dates]
            valid_dates = [d for d in parsed_dates if d is not None]
            if valid_dates:
                min_date_in_data = min(valid_dates)
                st.info(f"📅 Showing opportunities published from **{min_date_in_data.strftime('%b %d, %Y')}** onwards (based on your selected filter)")
    
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
            
            for idx, opp in enumerate(filtered_data):
                title = opp.get('title', 'No title')
                org = opp.get('organization', 'Unknown organization')
                published = opp.get('published_date', '')
                closing = opp.get('closing_date', '')
                link = opp.get('link', '')
                
                # Check if closing soon
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
                    </div>
                """, unsafe_allow_html=True)
                
                # Add buttons below the card
                col_a, col_b = st.columns(2)
                with col_a:
                    if link:
                        st.link_button("🔗 View on MERX", link, use_container_width=True)
                
                with col_b:
                    if link:
                        if st.button("📄 View Details", key=f"detail_{idx}", use_container_width=True):
                            with st.spinner("Fetching description..."):
                                description = fetch_description(link)
                                st.info("**Description:**")
                                st.write(description)
                
                st.markdown("<br>", unsafe_allow_html=True)
    
    elif view_mode == "📊 Table":
        # Table View
        if not filtered_data:
            st.warning("No opportunities match your filters.")
        else:
            st.subheader(f"Showing {len(filtered_data)} opportunities")
            
            table_df = pd.DataFrame(filtered_data)
            display_columns = ['title', 'organization', 'published_date', 'closing_date', 'link']
            available_columns = [col for col in display_columns if col in table_df.columns]
            
            column_names = {
                'title': 'Title',
                'organization': 'Organization',
                'published_date': 'Published',
                'closing_date': 'Closes',
                'link': 'Link'
            }
            
            display_df = table_df[available_columns].copy()
            display_df.columns = [column_names.get(col, col) for col in available_columns]
            
            if 'Link' in display_df.columns:
                display_df['Link'] = display_df['Link'].apply(
                    lambda x: f'<a href="{x}" target="_blank">View</a>' if x else ''
                )
            
            st.write(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)
            
            csv = table_df[available_columns].to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"merx_opportunities_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    else:  # Analytics View
        st.subheader("📈 Analytics")
        
        st.markdown("#### Opportunities by Organization")
        org_counts = df['organization'].value_counts().head(10)
        st.bar_chart(org_counts)
        
        st.markdown("---")
        
        st.markdown("#### Top Organizations - Detailed View")
        top_orgs = df['organization'].value_counts().head(10).reset_index()
        top_orgs.columns = ['Organization', 'Count']
        st.dataframe(top_orgs, use_container_width=True)
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style="text-align: center; color: #666; font-size: 0.9rem;">
            Data scraped from <a href="https://www.merx.com/public/solicitations/open" target="_blank">MERX</a> | 
            Built with Streamlit
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
