
import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agenda.mcp_models.calendar import MCPCalendarTools

async def schedule_it():
    print("Scheduling meeting manually as requested...")
    tools = MCPCalendarTools(user_id=1)
    
    # "meet reuired", low, 2026-01-11, 16:00-18:00
    # Collaborator: Harsh (ID 8) found in previous step
    
    result = await tools.schedule_meeting(
        title="meet reuired",
        scheduled_date="2026-01-11",
        start_time="16:00",
        end_time="18:00",
        priority="low",
        description="Meeting with Harsh to cover required items and next steps.",
        collaborator_ids=[8],
        auto_generate_link=True
    )
    
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(schedule_it())
