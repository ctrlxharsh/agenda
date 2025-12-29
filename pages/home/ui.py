import streamlit as st
from pages.home.chatbot_logic import create_chatbot

def distinct_home_page():
    # Initialize chat history in session state
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "chat_processing" not in st.session_state:
        st.session_state.chat_processing = False
    # CSS for fixed clear button at top right
    st.markdown("""
    <style>
    .fixed-clear-btn {
        position: fixed;
        top: 70px;
        right: 20px;
        z-index: 999;
    }
    </style>
    """, unsafe_allow_html=True)

    # AI Assistant Header
    st.subheader("🤖 AI Assistant")
    st.caption("Ask me anything or manage your calendar with natural language!")
    
    # Fixed Clear button at top right
    with st.container():
        cols = st.columns([9, 1])
        with cols[1]:
            if st.button("🗑️", help="Clear chat history", use_container_width=True):
                st.session_state.chat_messages = []
                st.rerun()
    
    # Display chat messages
    if not st.session_state.chat_messages:
        st.info("👋 Hi! I can help you manage your calendar, create tasks, and schedule meetings. Try asking me something!")
    else:
        for message in st.session_state.chat_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Chat input (Streamlit places this at the bottom automatically)
    if prompt := st.chat_input("Type your message here...", disabled=st.session_state.chat_processing):
        # Add user message to chat history
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Set processing state
        st.session_state.chat_processing = True
        
        # Get assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Create chatbot instance
                    chatbot = create_chatbot(
                        user_id=st.session_state.user['id'],
                        username=st.session_state.user['username']
                    )
                    
                    # Get response
                    response = chatbot.chat(
                        user_message=prompt,
                        chat_history=st.session_state.chat_messages[:-1]
                    )
                    
                    st.markdown(response)
                    
                    # Add assistant response to chat history
                    st.session_state.chat_messages.append({"role": "assistant", "content": response})
                    
                except Exception as e:
                    error_message = f"I apologize, but I encountered an error: {str(e)}"
                    st.error(error_message)
                    st.session_state.chat_messages.append({"role": "assistant", "content": error_message})
        
        # Reset processing state
        st.session_state.chat_processing = False
