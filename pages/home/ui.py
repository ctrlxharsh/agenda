import streamlit as st
import asyncio
from pages.home.chatbot_logic import create_chatbot

def distinct_home_page():
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "chat_processing" not in st.session_state:
        st.session_state.chat_processing = False
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

    with st.container():
        cols = st.columns([9, 2])
        with cols[0]:
            st.subheader("🤖 AI Assistant")
            st.caption("Ask me anything or manage your calendar with natural language!")
        with cols[1]:
            if st.button("Clear chat history 🗑️", use_container_width=True):
                st.session_state.chat_messages = []
                st.rerun()
    
    if not st.session_state.chat_messages:
        st.info("👋 Hi! I can help you manage your calendar, create tasks, and schedule meetings. Try asking me something!")
    else:
        for message in st.session_state.chat_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    if prompt := st.chat_input("Type your message here...", disabled=st.session_state.chat_processing):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        st.session_state.chat_processing = True
        
        api_key = st.session_state.get('openai_api_key')
        
        if not api_key:
            st.warning("Please enter your OpenAI API key in the sidebar settings first.")
            st.session_state.chat_messages.append({"role": "assistant", "content": "Please enter your OpenAI API key in the sidebar settings first."})
            st.session_state.chat_processing = False
            st.rerun()
            return

        # Get assistant response
        with st.chat_message("assistant"):
            # Async function to handle streaming
            async def process_chat(bot):
                response_placeholder = st.empty()
                full_response = ""
                status_placeholder = st.empty()
                
                full_response = ""
                status_placeholder = st.empty()
                
                with status_placeholder.status("Thinking...", expanded=True) as status:
                    async for event in bot.chat_stream(
                        user_message=prompt,
                        chat_history=st.session_state.chat_messages[:-1]
                    ):
                        if event["type"] == "token":
                            full_response += event["content"]
                            response_placeholder.markdown(full_response + "▌")
                        
                        elif event["type"] == "tool_start":
                            tool_name = event['tool']
                            status.update(label=f"🛠️ Executing {tool_name}...", state="running", expanded=True)
                            status.write(f"**{tool_name}**: Executing...")
                            # Safe JSON display
                            input_data = event['input']
                            if isinstance(input_data, (dict, list)):
                                status.json(input_data)
                            else:
                                status.write(input_data)
                        
                        elif event["type"] == "tool_end":
                            tool_name = event['tool']
                            status.update(label="Thinking...", state="running")
                            status.write(f"✅ **{tool_name}**: Done")
                            # Safe JSON display
                            output_data = event['output']
                            if isinstance(output_data, (dict, list)):
                                status.json(output_data)
                            else:
                                status.write(output_data)
                        
                        elif event["type"] == "error":
                            st.error(event["content"])
                            full_response = event["content"]
                    
                    status.update(label="Finished", state="complete", expanded=False)
                
                response_placeholder.markdown(full_response)
                return full_response

            try:
                # Create chatbot instance
                chatbot = create_chatbot(
                    user_id=st.session_state.user['id'],
                    username=st.session_state.user['username'],
                    api_key=api_key.strip()
                )
                
                # Run the async process
                response = asyncio.run(process_chat(chatbot))
                
                # Add assistant response to chat history
                st.session_state.chat_messages.append({"role": "assistant", "content": response})
                
            except Exception as e:
                import openai
                error_message = f"I apologize, but I encountered an error: {str(e)}"
                
                if isinstance(e, openai.AuthenticationError):
                    error_message = "🔴 **Authentication Failed**: The provided OpenAI API Key is invalid. Please check the key in the sidebar."
                elif "RateLimitError" in str(e):
                    error_message = "⏳ **Rate Limit**: You have exceeded your OpenAI API quota."
                
                st.error(error_message)
                st.session_state.chat_messages.append({"role": "assistant", "content": error_message})
        

        
        st.session_state.chat_processing = False
