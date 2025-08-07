import streamlit as st
import pandas as pd
import time

# More advanced callback functions
def execute_action(row_id, action_type):
    """Execute different actions based on type"""
    current_time = time.strftime("%H:%M:%S")
    
    if 'action_log' not in st.session_state:
        st.session_state.action_log = []
    
    if action_type == "start":
        st.session_state.process_states[row_id] = "Running"
        st.session_state.action_log.append(f"[{current_time}] Started process {row_id}")
    
    elif action_type == "stop":
        st.session_state.process_states[row_id] = "Stopped"
        st.session_state.action_log.append(f"[{current_time}] Stopped process {row_id}")
    
    elif action_type == "reset":
        st.session_state.process_states[row_id] = "Ready"
        st.session_state.action_log.append(f"[{current_time}] Reset process {row_id}")
    
    elif action_type == "delete":
        if 'deleted_rows' not in st.session_state:
            st.session_state.deleted_rows = set()
        st.session_state.deleted_rows.add(row_id)
        st.session_state.action_log.append(f"[{current_time}] Deleted process {row_id}")

# Sample dataset
processes_data = {
    'ID': [101, 102, 103, 104, 105, 106],
    'Task Name': [
        'Customer Data Analysis',
        'Inventory Processing', 
        'Report Generation',
        'Email Campaign',
        'Database Backup',
        'System Maintenance'
    ],
    'Department': ['Analytics', 'Operations', 'Finance', 'Marketing', 'IT', 'IT'],
    'Priority': ['High', 'Medium', 'Low', 'High', 'Critical', 'Medium'],
    'Estimated Time': ['2h', '45m', '1h', '30m', '3h', '1.5h'],
    'Assigned To': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank']
}

df_processes = pd.DataFrame(processes_data)

# Initialize session states
if 'process_states' not in st.session_state:
    st.session_state.process_states = {row_id: 'Ready' for row_id in df_processes['ID']}
if 'deleted_rows' not in st.session_state:
    st.session_state.deleted_rows = set()
if 'action_log' not in st.session_state:
    st.session_state.action_log = []

st.title("Advanced Process Management Dashboard")

# Filter out deleted rows
active_df = df_processes[~df_processes['ID'].isin(st.session_state.deleted_rows)].copy()

# Add current status to dataframe
active_df['Current Status'] = [st.session_state.process_states[row_id] for row_id in active_df['ID']]

# Display the dataframe
st.subheader("📊 Process Overview")
st.dataframe(
    active_df,
    column_config={
        "ID": st.column_config.NumberColumn("Process ID", width="small"),
        "Task Name": st.column_config.TextColumn("Task Description", width="large"),
        "Department": st.column_config.TextColumn("Department", width="medium"),
        "Priority": st.column_config.SelectboxColumn(
            "Priority Level",
            width="small",
            options=["Critical", "High", "Medium", "Low"]
        ),
        "Estimated Time": st.column_config.TextColumn("Est. Duration", width="small"),
        "Assigned To": st.column_config.TextColumn("Assignee", width="medium"),
        "Current Status": st.column_config.TextColumn("Status", width="medium")
    },
    use_container_width=True,
    hide_index=True
)

# Interactive controls for each process
st.subheader("🎮 Process Controls")

for idx, row in active_df.iterrows():
    row_id = row['ID']
    task_name = row['Task Name']
    current_status = st.session_state.process_states[row_id]
    priority = row['Priority']
    
    # Create expandable section for each process
    with st.expander(f"🔧 Controls for: {task_name} (ID: {row_id})", expanded=False):
        
        # Process info
        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.metric("Status", current_status)
        with col_info2:
            st.metric("Priority", priority)
        with col_info3:
            st.metric("Assignee", row['Assigned To'])
        
        # Action buttons
        col_btn1, col_btn2, col_btn3, col_btn4, col_btn5 = st.columns(5)
        
        with col_btn1:
            if st.button(
                "🚀 Start",
                key=f"start_proc_{row_id}",
                disabled=(current_status == "Running"),
                type="primary",
                use_container_width=True
            ):
                execute_action(row_id, "start")
                st.rerun()
        
        with col_btn2:
            if st.button(
                "⏹️ Stop",
                key=f"stop_proc_{row_id}",
                disabled=(current_status != "Running"),
                use_container_width=True
            ):
                execute_action(row_id, "stop")
                st.rerun()
        
        with col_btn3:
            if st.button(
                "🔄 Reset",
                key=f"reset_proc_{row_id}",
                disabled=(current_status == "Running"),
                use_container_width=True
            ):
                execute_action(row_id, "reset")
                st.rerun()
        
        with col_btn4:
            if st.button(
                "ℹ️ Info",
                key=f"info_proc_{row_id}",
                use_container_width=True
            ):
                st.info(f"Task: {task_name}\nDepartment: {row['Department']}\nEstimated: {row['Estimated Time']}")
        
        with col_btn5:
            if st.button(
                "🗑️ Delete",
                key=f"delete_proc_{row_id}",
                use_container_width=True,
                type="secondary"
            ):
                execute_action(row_id, "delete")
                st.rerun()

# Summary dashboard
st.divider()
st.subheader("📈 Summary Dashboard")

summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)

with summary_col1:
    total_processes = len(active_df)
    st.metric("Total Processes", total_processes)

with summary_col2:
    running_count = sum(1 for status in st.session_state.process_states.values() if status == "Running")
    st.metric("Running", running_count)

with summary_col3:
    stopped_count = sum(1 for status in st.session_state.process_states.values() if status == "Stopped")
    st.metric("Stopped", stopped_count)

with summary_col4:
    deleted_count = len(st.session_state.deleted_rows)
    st.metric("Deleted", deleted_count)

# Action log
if st.session_state.action_log:
    st.subheader("📝 Activity Log")
    
    # Show recent actions (last 10)
    recent_actions = st.session_state.action_log[-10:]
    
    for action in reversed(recent_actions):
        st.text(action)
    
    # Clear log button
    if st.button("🗑️ Clear Activity Log", type="secondary"):
        st.session_state.action_log = []
        st.rerun()