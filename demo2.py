import streamlit as st
import requests
import json
import pandas as pd
from typing import Dict, List, Any

# Configure the page
st.set_page_config(
    page_title="API Data Grid App",
    page_icon="🔗",
    layout="wide"
)

def show_preference_dialog():
    """
    Display a modal dialog for user preferences
    """
    if 'show_dialog' not in st.session_state:
        st.session_state.show_dialog = False
    
    if st.session_state.show_dialog:
        with st.container():
            # Create a modal-like dialog using columns and styling
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col2:
                # Dialog box styling
                st.markdown("""
                <div style="
                    background-color: white;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                    border: 2px solid #4CAF50;
                    margin: 20px 0;
                ">
                """, unsafe_allow_html=True)
                
                st.markdown("### 🎛️ User Preferences")
                st.markdown("---")
                
                # Create form for the dialog
                with st.form("preference_form"):
                    # Radio button for Yes/No preference
                    user_preference = st.radio(
                        "Do you want to receive notifications?",
                        options=["Yes", "No"],
                        index=0,
                        help="Select your notification preference"
                    )
                    
                    # Dropdown for favorite color
                    favorite_color = st.selectbox(
                        "Select your favorite color:",
                        options=["Red", "Green", "Yellow"],
                        index=0,
                        help="Choose your preferred color"
                    )
                    
                    # Form buttons
                    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
                    
                    with col_btn1:
                        submitted = st.form_submit_button("✅ Submit", use_container_width=True)
                    
                    with col_btn2:
                        cancelled = st.form_submit_button("❌ Cancel", use_container_width=True)
                    
                    with col_btn3:
                        # Placeholder for spacing
                        pass
                    
                    # Handle form submission
                    if submitted:
                        st.session_state.user_preferences = {
                            'notifications': user_preference,
                            'favorite_color': favorite_color,
                            'timestamp': pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        st.session_state.show_dialog = False
                        st.success(f"✅ Preferences saved! Notifications: {user_preference}, Color: {favorite_color}")
                        st.rerun()
                    
                    if cancelled:
                        st.session_state.show_dialog = False
                        st.info("❌ Dialog cancelled")
                        st.rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)

@st.dialog("User Preferences")
def show_streamlit_dialog():
    """
    Alternative implementation using Streamlit's native dialog (if available in your version)
    """
    st.write("### 🎛️ Set Your Preferences")
    
    # Radio button for Yes/No preference
    user_preference = st.radio(
        "Do you want to receive notifications?",
        options=["Yes", "No"],
        index=0,
        help="Select your notification preference"
    )
    
    # Dropdown for favorite color
    favorite_color = st.selectbox(
        "Select your favorite color:",
        options=["Red", "Green", "Yellow"],
        index=0,
        help="Choose your preferred color"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ Submit", use_container_width=True):
            st.session_state.user_preferences = {
                'notifications': user_preference,
                'favorite_color': favorite_color,
                'timestamp': pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            st.success(f"✅ Preferences saved! Notifications: {user_preference}, Color: {favorite_color}")
            st.rerun()
    
    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.rerun()

def display_user_preferences():
    """
    Display saved user preferences
    """
    if 'user_preferences' in st.session_state:
        prefs = st.session_state.user_preferences
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 👤 User Preferences")
        st.sidebar.markdown(f"**Notifications**: {prefs['notifications']}")
        
        # Show color with actual color styling
        color_map = {"Red": "#FF0000", "Green": "#00FF00", "Yellow": "#FFFF00"}
        color_hex = color_map.get(prefs['favorite_color'], "#000000")
        st.sidebar.markdown(
            f"**Favorite Color**: <span style='color: {color_hex}; font-weight: bold;'>{prefs['favorite_color']}</span>", 
            unsafe_allow_html=True
        )
        st.sidebar.markdown(f"**Saved**: {prefs['timestamp']}")
        
        if st.sidebar.button("🗑️ Clear Preferences"):
            del st.session_state.user_preferences
            st.rerun()

def make_api_call(endpoint: str, params: Dict = None) -> Dict[str, Any]:
    """
    Make API call to the specified endpoint
    
    Args:
        endpoint: API endpoint URL
        params: Optional parameters for the API call
    
    Returns:
        JSON response from the API
    """
    try:
        response = requests.get(endpoint, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API call failed: {str(e)}")
        return {}
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse JSON response: {str(e)}")
        return {}

def handle_action_api_call(action: str, item_id: int, data_type: str):
    """
    Handle API calls triggered by action buttons
    
    Args:
        action: The action type (posts, albums, todos, comments, etc.)
        item_id: The ID of the item
        data_type: The type of data being acted upon
    """
    base_url = "https://jsonplaceholder.typicode.com"
    
    action_endpoints = {
        "user_posts": f"{base_url}/posts?userId={item_id}",
        "user_albums": f"{base_url}/albums?userId={item_id}",
        "user_todos": f"{base_url}/todos?userId={item_id}",
        "post_comments": f"{base_url}/comments?postId={item_id}",
        "post_details": f"{base_url}/posts/{item_id}",
        "item_details": f"{base_url}/{data_type.lower()}/{item_id}"
    }
    
    if action in action_endpoints:
        with st.spinner(f"Fetching {action.replace('_', ' ')}..."):
            result = make_api_call(action_endpoints[action])
            if result:
                st.session_state['action_data'] = result
                st.session_state['action_type'] = action
                st.session_state['action_item_id'] = item_id
                st.success(f"✅ Successfully fetched {action.replace('_', ' ')} for ID {item_id}")

def display_data_grid_with_actions(data: List[Dict], title: str = "Data Grid"):
    """
    Display data in grid format with interactive action buttons
    
    Args:
        data: List of dictionaries containing the data
        title: Title for the grid
    """
    if not data:
        st.warning("No data to display")
        return
    
    st.subheader(title)
    
    current_data_type = st.session_state.get('data_type', '')
    
    # Create action buttons for each row
    if 'id' in data[0]:
        for i, row in enumerate(data):
            with st.container():
                # Create columns for data display and actions
                cols = st.columns([4, 1])  # 4:1 ratio for data:actions
                
                with cols[0]:
                    # Display row data in a more compact format
                    row_info = []
                    for key, value in row.items():
                        if key != 'id':  # Don't repeat ID
                            if isinstance(value, str) and len(value) > 50:
                                value = value[:50] + "..."
                            row_info.append(f"**{key}**: {value}")
                    
                    st.markdown(f"**ID {row['id']}**: " + " | ".join(row_info[:3]))  # Show first 3 fields
                
                with cols[1]:
                    # Action buttons based on data type
                    if current_data_type == "Users":
                        action_col1, action_col2, action_col3 = st.columns(3)
                        with action_col1:
                            if st.button("📝", key=f"posts_{i}", help="Fetch User Posts"):
                                handle_action_api_call("user_posts", row['id'], current_data_type)
                        with action_col2:
                            if st.button("📁", key=f"albums_{i}", help="Fetch User Albums"):
                                handle_action_api_call("user_albums", row['id'], current_data_type)
                        with action_col3:
                            if st.button("✅", key=f"todos_{i}", help="Fetch User Todos"):
                                handle_action_api_call("user_todos", row['id'], current_data_type)
                    
                    elif current_data_type == "Posts":
                        action_col1, action_col2 = st.columns(2)
                        with action_col1:
                            if st.button("💬", key=f"comments_{i}", help="Fetch Comments"):
                                handle_action_api_call("post_comments", row['id'], current_data_type)
                        with action_col2:
                            if st.button("👁️", key=f"details_{i}", help="View Details"):
                                handle_action_api_call("post_details", row['id'], current_data_type)
                    
                    else:
                        if st.button("🔍", key=f"details_{i}", help="Fetch Details"):
                            handle_action_api_call("item_details", row['id'], current_data_type)
                
                st.divider()
    
    # Also show traditional table view
    with st.expander("📊 View as Table"):
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)

def display_data_grid(data: List[Dict], title: str = "Data Grid"):
    """
    Display data in HTML grid format with action icons
    
    Args:
        data: List of dictionaries containing the data
        title: Title for the grid
    """
    if not data:
        st.warning("No data to display")
        return
    
    # Use the new interactive display
    display_data_grid_with_actions(data, title)

def main():
    st.title("🔗 API Data Grid Application")
    st.markdown("---")
    
    # Display user preferences in sidebar if they exist
    display_user_preferences()
    
    # Show dialog if triggered
    show_preference_dialog()
    
    # Sidebar for API configuration
    with st.sidebar:
        st.header("API Configuration")
        
        # Button to open preferences dialog
        if st.button("⚙️ Open Preferences Dialog", use_container_width=True):
            st.session_state.show_dialog = True
            st.rerun()
        
        # Alternative: Native dialog button (if supported in your Streamlit version)
        if st.button("🎛️ Native Dialog (Alternative)", use_container_width=True):
            show_streamlit_dialog()
        
        st.markdown("---")
        
        # Default API endpoints (using JSONPlaceholder for demo)
        api_endpoints = {
            "Users": "https://jsonplaceholder.typicode.com/users",
            "Posts": "https://jsonplaceholder.typicode.com/posts",
            "Albums": "https://jsonplaceholder.typicode.com/albums",
            "Todos": "https://jsonplaceholder.typicode.com/todos"
        }
        
        # Custom API endpoint input
        custom_endpoint = st.text_input(
            "Custom API Endpoint",
            placeholder="https://api.example.com/data"
        )
        
        if custom_endpoint:
            api_endpoints["Custom"] = custom_endpoint
    
    # Main content area
    col1, col2, col3 = st.columns([2, 2, 2])
    
    # Create buttons for different API calls
    with col1:
        if st.button("📊 Fetch Users", use_container_width=True):
            st.session_state['current_data'] = make_api_call(api_endpoints["Users"])
            st.session_state['data_type'] = "Users"
    
    with col2:
        if st.button("📝 Fetch Posts", use_container_width=True):
            st.session_state['current_data'] = make_api_call(api_endpoints["Posts"])
            st.session_state['data_type'] = "Posts"
    
    with col3:
        if st.button("📁 Fetch Albums", use_container_width=True):
            st.session_state['current_data'] = make_api_call(api_endpoints["Albums"])
            st.session_state['data_type'] = "Albums"
    
    # Second row of buttons
    col4, col5, col6 = st.columns([2, 2, 2])
    
    with col4:
        if st.button("✅ Fetch Todos", use_container_width=True):
            st.session_state['current_data'] = make_api_call(api_endpoints["Todos"])
            st.session_state['data_type'] = "Todos"
    
    with col5:
        if st.button("🔄 Refresh Data", use_container_width=True):
            if 'data_type' in st.session_state:
                endpoint_key = st.session_state['data_type']
                st.session_state['current_data'] = make_api_call(api_endpoints[endpoint_key])
    
    with col6:
        if st.button("🧹 Clear Data", use_container_width=True):
            st.session_state.clear()
    
    # Custom API call section
    if custom_endpoint:
        st.markdown("---")
        col7, col8 = st.columns([1, 1])
        with col7:
            if st.button("🚀 Call Custom API", use_container_width=True):
                st.session_state['current_data'] = make_api_call(custom_endpoint)
                st.session_state['data_type'] = "Custom"
    
    # Display the data grid
    st.markdown("---")
    
    if 'current_data' in st.session_state and st.session_state['current_data']:
        data = st.session_state['current_data']
        data_type = st.session_state.get('data_type', 'API Data')
        
        # Handle both single objects and arrays
        if isinstance(data, dict):
            if 'results' in data:
                # Handle paginated responses
                display_data_grid(data['results'], f"{data_type} (Page Data)")
            else:
                # Single object response
                display_data_grid([data], f"{data_type} (Single Record)")
        elif isinstance(data, list):
            # Limit display for large datasets
            display_limit = st.slider(
                "Number of records to display", 
                min_value=1, 
                max_value=min(len(data), 100), 
                value=min(len(data), 10)
            )
            display_data_grid(data[:display_limit], f"{data_type} ({len(data)} total records)")
        
        # Show raw JSON in expandable section
        with st.expander("View Raw JSON Response"):
            st.json(data)
    
    else:
        st.info("👆 Click a button above to fetch data from an API and display it in the grid!")
    
    # Display action results if any
    if 'action_data' in st.session_state and st.session_state['action_data']:
        st.markdown("---")
        st.subheader("🎯 Action Results")
        
        action_type = st.session_state.get('action_type', 'action')
        action_item_id = st.session_state.get('action_item_id', '')
        action_data = st.session_state['action_data']
        
        # Display action results
        col_action1, col_action2 = st.columns([3, 1])
        
        with col_action1:
            st.markdown(f"**{action_type.replace('_', ' ').title()}** for ID **{action_item_id}**:")
            
            if isinstance(action_data, list):
                if len(action_data) > 0:
                    # Show summary
                    st.info(f"Found {len(action_data)} items")
                    
                    # Display first few items
                    display_limit_action = min(len(action_data), 5)
                    for i, item in enumerate(action_data[:display_limit_action]):
                        with st.container():
                            if isinstance(item, dict):
                                item_info = []
                                for key, value in item.items():
                                    if isinstance(value, str) and len(value) > 60:
                                        value = value[:60] + "..."
                                    item_info.append(f"**{key}**: {value}")
                                st.markdown(" | ".join(item_info))
                            else:
                                st.write(item)
                            if i < display_limit_action - 1:
                                st.divider()
                    
                    if len(action_data) > display_limit_action:
                        st.markdown(f"... and {len(action_data) - display_limit_action} more items")
                else:
                    st.warning("No items found")
            
            elif isinstance(action_data, dict):
                # Single item result
                for key, value in action_data.items():
                    st.markdown(f"**{key}**: {value}")
            
            else:
                st.write(action_data)
        
        with col_action2:
            if st.button("🗑️ Clear Action Results", use_container_width=True):
                del st.session_state['action_data']
                del st.session_state['action_type']
                del st.session_state['action_item_id']
                st.rerun()
        
        # Raw JSON for action results
        with st.expander("View Action Raw JSON"):
            st.json(action_data)
    
    # Instructions
    with st.expander("ℹ️ Instructions"):
        st.markdown("""
        ### How to use this app:
        
        1. **Default APIs**: Click any of the preset buttons to fetch data from JSONPlaceholder demo APIs
        2. **Custom API**: Enter your own API endpoint in the sidebar and click "Call Custom API"
        3. **View Data**: The data will be displayed in a formatted HTML grid below
        4. **Refresh**: Use the "Refresh Data" button to reload the current dataset
        5. **Clear**: Use "Clear Data" to reset the application
        
        ### Supported API Response Formats:
        - JSON arrays: `[{...}, {...}, ...]`
        - Single JSON objects: `{...}`
        - Paginated responses with 'results' key: `{"results": [...], ...}`
        
        ### Features:
        - Responsive HTML grid with hover effects
        - Expandable raw JSON view
        - Error handling for failed API calls
        - Configurable display limits for large datasets
        - **Interactive action buttons** for related API calls
        - **Preference dialog** with user settings
        
        ### Dialog Features:
        - **Two dialog implementations**: Custom modal and native Streamlit dialog
        - **Radio buttons**: Yes/No for notifications
        - **Dropdown menu**: Color selection (Red, Green, Yellow)
        - **Persistent preferences**: Saved in sidebar with color styling
        - **Form validation**: Submit/Cancel functionality
        """)

if __name__ == "__main__":
    main()