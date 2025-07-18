agent_role_template = """
< Role >
{}
</ Role >
"""

agent_tool_template = """
< Tools >
{}
</ Tools >
"""

agent_instruction_template = """
< Instructions >
{}
</ Instructions >"""

agent_response_preference_template = """
< Response Preferences >
{}
</ Response Preferences >
"""

tool_calling_prompt_template = """
User's request:
{}
Metrics to analyze from the previous agent:
{}
Reason why you choose the previous tool:
{}
Previous tool name: 
{}
Previous tool result:
{}
"""