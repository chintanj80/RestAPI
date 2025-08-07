import streamlit as st
import pandas as pd


# Sample data
data = {
    'ID': [1, 2, 3, 4],
    'Name': ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Brown'],
    'Age': [25, 30, 35, 28],
    'Department': ['Engineering', 'Marketing', 'Sales', 'Human Resources'],
    'Salary': [75000, 65000, 55000, 60000],
    'Active': [True, True, False, True]
}

df = pd.DataFrame(data)


# Configure the page
st.set_page_config(
    page_title="Streamlit Demo",
    page_icon=":guardsman:",  # You can use an emoji or a custom icon
    layout="wide",  # Options: wide, centered
    initial_sidebar_state="expanded"  # Options: expanded, collapsed
)

def button1_click():
    st.write("Button 1 clicked!")
    st.balloons()  # Optional: Show balloons animation

def main():
    # Remove top padding/margin
    st.markdown("""
    <style>
        .block-container {
        padding-top: 0.9rem;
        padding-bottom: 0rem;
        padding-left: 5rem;
        padding-right: 5rem;
        }
    </style>
    """, unsafe_allow_html=True)
    st.title("Streamlit Demo Application...")
    st.write("This is a simple demo application using Streamlit.")
    
    tab1, tab2 = st.tabs(["💻 Jup", "🔌API"])
    
    with tab1:
        col1, col2 = st.columns([0.05, 0.8])  # Adjust column widths as needed
        
        with col1:
            pass
            
        with col2:
            #st.header("Column 2 -Super long column with a lot of text to demonstrate how to control the size and width of the columns...")
            col2_1, col2_2 = st.columns([0.2, 0.8])  # Split column 2 into two sub-columns
            with col2_1: st.markdown("##### Column 2")
            with col2_2: st.button("Launch Jupyter", on_click=button1_click, key="button1", help="This is a button in column 2")
            
            st.dataframe(
                df,
                column_config={
                    "ID": st.column_config.NumberColumn(
                        "Employee ID",
                        help="Unique employee identifier",
                        width="small"
                    ),
                    "Name": st.column_config.TextColumn(
                        "Full Name",
                        help="Employee full name",
                        width="large"
                    ),
                    "Age": st.column_config.NumberColumn(
                        "Age",
                        help="Employee age",
                        width="small"
                    ),
                    "Department": st.column_config.SelectboxColumn(
                        "Department",
                        help="Employee department",
                        width="medium",
                        options=[
                            "Engineering",
                            "Marketing", 
                            "Sales",
                            "Human Resources"
                        ]
                    ),
                    "Salary": st.column_config.NumberColumn(
                        "Annual Salary",
                        help="Annual salary in USD",
                        format="$%d",
                        width="medium"
                    ),
                    "Active": st.column_config.CheckboxColumn(
                        "Is Active",
                        help="Employee status",
                        width="small"
                    ),
                    "Start": st.column_config.ImageColumn(
                        
                },
                use_container_width=True,
                hide_index=True
            )





if __name__ == "__main__":
    main()