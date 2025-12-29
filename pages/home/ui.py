import streamlit as st
from pages.home.chatbot_logic import create_chatbot

def distinct_home_page():
    # Initialize chat history in session state
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "chat_processing" not in st.session_state:
        st.session_state.chat_processing = False
    
    # Main Dashboard Content
    # Main Dashboard Content - AI Assistant
    with st.container(border=True):
        st.title("🤖 AI Assistant")
        st.caption("Ask me anything or manage your calendar with natural language!")
        
        # Display chat messages
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.chat_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        # Chat input
        if prompt := st.chat_input("Type your message here...", disabled=st.session_state.chat_processing):
            # Add user message to chat history
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            
            # Display user message
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Set processing state
            st.session_state.chat_processing = True
            
            # Display assistant response with spinner
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
                            chat_history=st.session_state.chat_messages[:-1]  # Exclude the current message
                        )
                        
                        # Display response
                        st.markdown(response)
                        
                        # Add assistant response to chat history
                        st.session_state.chat_messages.append({"role": "assistant", "content": response})
                        
                    except Exception as e:
                        error_message = f"I apologize, but I encountered an error: {str(e)}"
                        st.error(error_message)
                        st.session_state.chat_messages.append({"role": "assistant", "content": error_message})
            
            # Reset processing state
            st.session_state.chat_processing = False
            
            # Rerun to update the UI
            st.rerun()
        
        # Clear chat button
        if st.button("Clear Chat History", type="secondary"):
            st.session_state.chat_messages = []
            st.rerun()
