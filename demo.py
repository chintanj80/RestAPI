# app.py - Main application entry point
import streamlit as st
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import pandas as pd
import plotly.express as px
from abc import ABC, abstractmethod

# Page configuration - must be first Streamlit command
st.set_page_config(
    page_title="Professional Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================
# Data Models
# =====================

@dataclass
class AppConfig:
    """Application configuration"""
    app_title: str = "Professional Dashboard"
    theme_color: str = "#1f77b4"
    cache_ttl: int = 3600

@dataclass
class FilterState:
    """Filter state management"""
    date_range: Optional[tuple] = None
    categories: list = field(default_factory=list)
    min_value: float = 0.0
    max_value: float = 100.0

# =====================
# Data Layer
# =====================

class DataService(ABC):
    """Abstract data service interface"""
    
    @abstractmethod
    def load_data(self, filters: FilterState) -> pd.DataFrame:
        pass

class SampleDataService(DataService):
    """Sample data implementation"""
    
    @st.cache_data(ttl=3600)
    def load_data(_self, filters: FilterState) -> pd.DataFrame:
        """Load sample data with caching"""
        # Generate sample data
        import numpy as np
        np.random.seed(42)
        
        data = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=100),
            'category': np.random.choice(['A', 'B', 'C'], 100),
            'value': np.random.normal(50, 15, 100),
            'volume': np.random.randint(1000, 5000, 100)
        })
        
        return data

# =====================
# UI Components
# =====================

class UIComponents:
    """Reusable UI components"""
    
    @staticmethod
    def render_header(title: str, subtitle: str = ""):
        """Render application header"""
        st.title(title)
        if subtitle:
            st.markdown(f"*{subtitle}*")
        st.divider()
    
    @staticmethod
    def render_sidebar_filters() -> FilterState:
        """Render sidebar filters"""
        with st.sidebar:
            st.header("🔧 Filters")
            
            # Date range filter
            date_range = st.date_input(
                "Date Range",
                value=[],
                help="Select date range for filtering"
            )
            
            # Category multiselect
            categories = st.multiselect(
                "Categories",
                
                options=['A', 'B', 'C'],
                default=['A', 'B', 'C'],
                help="Select categories to include"
            )
            
            # Value range slider
            value_range = st.slider(
                "Value Range",
                min_value=0.0,
                max_value=100.0,
                value=(0.0, 100.0),
                help="Filter by value range"
            )
            
            return FilterState(
                date_range=date_range if date_range else None,
                categories=categories,
                min_value=value_range[0],
                max_value=value_range[1]
            )
    
    @staticmethod
    def render_metrics_grid(data: pd.DataFrame):
        """Render metrics in a grid layout"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Records",
                f"{len(data):,}",
                delta=f"+{len(data)//10}",
                help="Total number of records"
            )
        
        with col2:
            avg_value = data['value'].mean()
            st.metric(
                "Average Value",
                f"{avg_value:.2f}",
                delta=f"{avg_value-50:.2f}",
                help="Mean value across all records"
            )
        
        with col3:
            total_volume = data['volume'].sum()
            st.metric(
                "Total Volume",
                f"{total_volume:,}",
                help="Sum of all volume values"
            )
        
        with col4:
            unique_categories = data['category'].nunique()
            st.metric(
                "Categories",
                unique_categories,
                help="Number of unique categories"
            )
    
    @staticmethod
    def render_charts(data: pd.DataFrame):
        """Render chart visualizations"""
        tab1, tab2, tab3 = st.tabs(["📈 Trends", "📊 Distribution", "📋 Data Table"])
        
        with tab1:
            # Time series chart
            fig_line = px.line(
                data, 
                x='date', 
                y='value', 
                color='category',
                title="Value Trends Over Time",
                height=400
            )
            fig_line.update_layout(showlegend=True)
            st.plotly_chart(fig_line, use_container_width=True)
        
        with tab2:
            col1, col2 = st.columns(2)
            
            with col1:
                # Histogram
                fig_hist = px.histogram(
                    data, 
                    x='value', 
                    color='category',
                    title="Value Distribution",
                    nbins=20
                )
                st.plotly_chart(fig_hist, use_container_width=True)
            
            with col2:
                # Box plot
                fig_box = px.box(
                    data, 
                    x='category', 
                    y='value',
                    title="Value by Category"
                )
                st.plotly_chart(fig_box, use_container_width=True)
        
        with tab3:
            # Data table with search and pagination
            st.subheader("📋 Raw Data")
            
            # Search functionality
            search_term = st.text_input("🔍 Search data", placeholder="Enter search term...")
            
            display_data = data.copy()
            if search_term:
                mask = display_data.astype(str).apply(
                    lambda x: x.str.contains(search_term, case=False, na=False)
                ).any(axis=1)
                display_data = display_data[mask]
            
            # Display dataframe
            st.dataframe(
                display_data,
                use_container_width=True,
                height=400,
                column_config={
                    "date": st.column_config.DateColumn("Date"),
                    "value": st.column_config.NumberColumn("Value", format="%.2f"),
                    "volume": st.column_config.NumberColumn("Volume", format="%d")
                }
            )

# =====================
# Page Management
# =====================

class PageManager:
    """Manage different pages/views"""
    
    def __init__(self, data_service: DataService):
        self.data_service = data_service
        self.ui = UIComponents()
    
    def render_dashboard_page(self):
        """Main dashboard page"""
        self.ui.render_header(
            "📊 Professional Dashboard",
            "Advanced analytics with modern UI components"
        )
        
        # Get filters from sidebar
        filters = self.ui.render_sidebar_filters()
        
        # Load and filter data
        try:
            with st.spinner("Loading data..."):
                data = self.data_service.load_data(filters)
                
                # Apply filters
                if filters.categories:
                    data = data[data['category'].isin(filters.categories)]
                
                data = data[
                    (data['value'] >= filters.min_value) & 
                    (data['value'] <= filters.max_value)
                ]
                
                if filters.date_range and len(filters.date_range) == 2:
                    start_date, end_date = filters.date_range
                    data = data[
                        (data['date'] >= pd.to_datetime(start_date)) &
                        (data['date'] <= pd.to_datetime(end_date))
                    ]
            
            if data.empty:
                st.warning("⚠️ No data available with current filters")
                return
            
            # Render metrics
            st.subheader("📊 Key Metrics")
            self.ui.render_metrics_grid(data)
            
            st.divider()
            
            # Render charts
            st.subheader("📈 Analytics")
            self.ui.render_charts(data)
            
        except Exception as e:
            st.error(f"❌ Error loading data: {str(e)}")
    
    def render_settings_page(self):
        """Settings page"""
        self.ui.render_header("⚙️ Settings", "Configure application preferences")
        
        with st.form("settings_form"):
            st.subheader("Display Settings")
            
            theme = st.selectbox("Theme", ["Light", "Dark", "Auto"])
            refresh_rate = st.slider("Auto-refresh (minutes)", 1, 60, 5)
            show_tooltips = st.checkbox("Show tooltips", value=True)
            
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.form_submit_button("💾 Save Settings", type="primary"):
                    st.success("✅ Settings saved successfully!")
            
            with col2:
                if st.form_submit_button("🔄 Reset to Defaults"):
                    st.info("ℹ️ Settings reset to defaults")

# =====================
# Session Management
# =====================

class SessionManager:
    """Manage Streamlit session state"""
    
    @staticmethod
    def initialize_session():
        """Initialize session state variables"""
        defaults = {
            'current_page': 'Dashboard',
            'user_preferences': {},
            'last_refresh': None
        }
        
        for key, default_value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value

# =====================
# Main Application
# =====================

class StreamlitApp:
    """Main application class"""
    
    def __init__(self):
        self.config = AppConfig()
        self.data_service = SampleDataService()
        self.page_manager = PageManager(self.data_service)
        self.session_manager = SessionManager()
    
    def run(self):
        """Run the application"""
        # Initialize session
        self.session_manager.initialize_session()
        
        # Navigation
        with st.sidebar:
            st.title("🏠 Navigation")
            page = st.radio(
                "Go to:",
                ["Dashboard", "Settings"],
                key="navigation"
            )
        
        # Route to appropriate page
        if page == "Dashboard":
            self.page_manager.render_dashboard_page()
        elif page == "Settings":
            self.page_manager.render_settings_page()
        
        # Footer
        st.divider()
        st.markdown(
            """
            <div style='text-align: center; color: gray; font-size: 0.8em;'>
                Built with ❤️ using Streamlit | Professional Dashboard v1.0
            </div>
            """,
            unsafe_allow_html=True
        )

# =====================
# Application Entry Point
# =====================

if __name__ == "__main__":
    app = StreamlitApp()
    app.run()