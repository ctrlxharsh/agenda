
import json
from datetime import date, datetime, time
from typing import List, Dict, Any
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from utils.db import execute_query
from utils.env_config import get_openai_api_key

def fetch_todays_items(user_id: int) -> List[Dict[str, Any]]:
    """
    Fetch all items for the user that are relevant for today's plan.
    Includes:
    1. Items scheduled for TODAY (tasks, meetings,todo etc.)
    """
    query = """
    SELECT 
        task_id, title, description, status, priority, 
        estimated_time, scheduled_date, start_time, end_time, 
        due_date, category
    FROM tasks 
    WHERE user_id = %s 
    AND (
        scheduled_date::date = %s 
        OR scheduled_date IS NULL
    )
    ORDER BY scheduled_date NULLS LAST, priority DESC
    """
    today = date.today()
    results = execute_query(query, (user_id, today), fetch_all=True)
    
    items = []
    if results:
        for row in results:
            items.append({
                "task_id": row[0],
                "title": row[1],
                "description": row[2],
                "status": row[3],
                "priority": row[4],
                "estimated_time": row[5] or 1.0, # Default 1 hour if not set
                "scheduled_date": row[6],
                "start_time": row[7],
                "end_time": row[8],
                "due_date": row[9],
                "category": row[10]
            })
    
    return items

def update_task_times(updates: List[Dict[str, Any]]) -> bool:
    """
    Update start_time, end_time, and scheduled_date for a list of tasks.
    """
    try:
        today = date.today()
        for update in updates:
            query = """
            UPDATE tasks 
            SET start_time = %s, end_time = %s, scheduled_date = %s, status = %s
            WHERE task_id = %s
            """
            # Determine status: if it was 'todo', now it's 'task' (scheduled)
            new_status = 'meeting' if update.get('is_meeting') else 'task'
            
            execute_query(query, (
                update['start_time'], 
                update['end_time'], 
                today,
                new_status,
                update['task_id']
            ))
        return True
    except Exception as e:
        print(f"Error updating task times: {e}")
        return False

def generate_schedule_with_ai(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Use OpenAI to generate a schedule for the given items.
    Respects fixed times for existing scheduled items (like meetings).
    """
    if not items:
        return []

    api_key = get_openai_api_key()
    llm = ChatOpenAI(model="gpt-5-mini", temperature=0.2, api_key=api_key)
    
    # Prepare items for the prompt
    items_json = json.dumps(items, default=str)
    current_date = date.today().strftime("%Y-%m-%d")
    
    system_prompt = f"""
    You are an expert daily planner. Your goal is to create an optimal schedule for the user for TODAY ({current_date}).
    
    RULES:
    1. You will receive a list of items (tasks, meetings, todos).
    2. Items with status 'meeting' (or 'event') are FIXED constraints. YOU CANNOT MOVE THEM.
    3. Items with status 'task' (even if they have a time) or 'todo' are FLEXIBLE. You SHOULD reschedule them to:
       - Avoid overlaps with meetings.
       - Prioritize 'urgent'/'high' tasks.
       - Create a logical flow (e.g. group locations if known).
    4. If a task has a pre-assigned time but creates a conflict or is low priority, MOVE IT.
    5. 'estimated_time' is in hours. If missing, assume 1 hour or if task is like flight or something then assume time according to that 
    6. Ensure ABSOLUTELY NO OVERLAPS in the final schedule.
    
    OUTPUT FORMAT:
    Return a valid JSON array of objects. Each object must have:
    - task_id: int
    - start_time: "HH:MM:SS" (24h format)
    - end_time: "HH:MM:SS" (24h format)
    - reason: str (Explain WHY you moved this or picked this time. E.g. "Moved to 2pm to avoid meeting overlap")
    
    Only return items that are scheduled for today.
    """
    
    user_prompt = f"Here are my items for today: {items_json}. Please generate a schedule."
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    response = llm.invoke(messages)
    content = response.content.strip()
    
    # helper to clean json markdown if present
    if content.startswith("```json"):
        content = content[7:]
    if content.endswith("```"):
        content = content[:-3]
        
    try:
        schedule = json.loads(content)
        return schedule
    except json.JSONDecodeError:
        print("Failed to decode AI response")
        return []
